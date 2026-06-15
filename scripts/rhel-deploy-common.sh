#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Slinky Software

set -euo pipefail

APP_NAME="${APP_NAME:-telephonytoolbox}"
APP_USER="${APP_USER:-telephonytoolbox}"
APP_GROUP="${APP_GROUP:-$APP_USER}"
APP_DIR="${APP_DIR:-/opt/telephonytoolbox}"
BACKEND_DIR="${BACKEND_DIR:-$APP_DIR/backend}"
FRONTEND_DIR="${FRONTEND_DIR:-$APP_DIR/frontend}"
VENV_DIR="${VENV_DIR:-$APP_DIR/.venv}"
ENV_DIR="${ENV_DIR:-/etc/telephonytoolbox}"
ENV_FILE="${ENV_FILE:-$ENV_DIR/backend.env}"
LOG_DIR_WAS_PROVIDED=0
if [[ -n "${LOG_DIR+x}" ]]; then
  LOG_DIR_WAS_PROVIDED=1
fi
LOG_DIR="${LOG_DIR:-/var/log/telephonytoolbox}"
APP_HOSTNAME="${APP_HOSTNAME:-}"
BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8010}"
BACKEND_BIND="${BACKEND_HOST}:${BACKEND_PORT}"
NGINX_USER="${NGINX_USER:-nginx}"
SYSTEMD_SERVICE_NAME="${SYSTEMD_SERVICE_NAME:-telephonytoolbox-gunicorn.service}"
SYSTEMD_SERVICE_PATH="${SYSTEMD_SERVICE_PATH:-/etc/systemd/system/${SYSTEMD_SERVICE_NAME}}"
NGINX_CONF_DIR="${NGINX_CONF_DIR:-/etc/nginx}"
NGINX_SITES_AVAILABLE_DIR="${NGINX_SITES_AVAILABLE_DIR:-$NGINX_CONF_DIR/sites-available}"
NGINX_SITES_ENABLED_DIR="${NGINX_SITES_ENABLED_DIR:-$NGINX_CONF_DIR/sites-enabled}"
NGINX_SITES_INCLUDE="${NGINX_SITES_INCLUDE:-$NGINX_CONF_DIR/conf.d/sites-enabled.conf}"
NGINX_SITE_NAME="${NGINX_SITE_NAME:-telephonytoolbox.conf}"
NGINX_SITE_AVAILABLE_PATH="${NGINX_SITE_AVAILABLE_PATH:-$NGINX_SITES_AVAILABLE_DIR/$NGINX_SITE_NAME}"
NGINX_SITE_ENABLED_PATH="${NGINX_SITE_ENABLED_PATH:-$NGINX_SITES_ENABLED_DIR/$NGINX_SITE_NAME}"
LOGROTATE_CONF="${LOGROTATE_CONF:-/etc/logrotate.d/telephonytoolbox}"
FRONTEND_DIST_DIR="${FRONTEND_DIST_DIR:-$FRONTEND_DIR/dist}"
FRONTEND_SPA_DIR="${FRONTEND_SPA_DIR:-$FRONTEND_DIST_DIR/spa}"
REPO_ENV_LINK="${REPO_ENV_LINK:-$APP_DIR/.env}"
PYTHON_BIN="${PYTHON_BIN:-}"
NODE_MAJOR="${NODE_MAJOR:-22}"

log() {
  echo "[${LOG_PREFIX:-rhel-deploy}] $*"
}

die() {
  echo "$*" >&2
  exit 1
}

run_as_app_user() {
  sudo -u "$APP_USER" -H bash -lc "cd '$APP_DIR' && $*"
}

require_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    die "This script must run as root (use sudo)."
  fi
}

trim_value() {
  printf '%s' "$1" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'
}

strip_outer_quotes() {
  local value="$1"
  value="${value#\"}"
  value="${value%\"}"
  value="${value#\'}"
  value="${value%\'}"
  printf '%s' "$value"
}

validate_paths() {
  if [[ ! -d "$BACKEND_DIR" || ! -f "$BACKEND_DIR/manage.py" ]]; then
    die "Backend directory not found: $BACKEND_DIR"
  fi

  if [[ ! -d "$FRONTEND_DIR" || ! -f "$FRONTEND_DIR/package.json" ]]; then
    die "Frontend directory not found: $FRONTEND_DIR"
  fi
}

validate_log_dir() {
  if [[ "$LOG_DIR" != /* ]]; then
    die "LOG_DIR must be an absolute path: $LOG_DIR"
  fi
}

detect_app_hostname_from_nginx_site() {
  local candidate

  if [[ ! -f "$NGINX_SITE_AVAILABLE_PATH" ]]; then
    return 1
  fi

  candidate="$(sed -n 's/^[[:space:]]*server_name[[:space:]]\+\([^;]*\);/\1/p' "$NGINX_SITE_AVAILABLE_PATH" | head -n 1 | awk '{print $1}')"
  candidate="$(trim_value "$candidate")"
  case "$candidate" in
    ''|'_')
      return 1
      ;;
  esac

  printf '%s' "$candidate"
}

detect_app_hostname_from_env_file() {
  local raw candidate
  local -a hosts

  if [[ ! -f "$ENV_FILE" ]]; then
    return 1
  fi

  raw="$(sed -n 's/^DJANGO_ALLOWED_HOSTS=//p' "$ENV_FILE" | tail -n 1)"
  raw="$(strip_outer_quotes "$raw")"
  if [[ -z "$raw" ]]; then
    return 1
  fi

  IFS=',' read -r -a hosts <<< "$raw"
  for candidate in "${hosts[@]}"; do
    candidate="$(trim_value "$candidate")"
    case "$candidate" in
      ''|'localhost'|'127.0.0.1'|'[::1]')
        continue
        ;;
    esac
    printf '%s' "$candidate"
    return 0
  done

  return 1
}

resolve_app_hostname() {
  if [[ -z "$APP_HOSTNAME" ]]; then
    APP_HOSTNAME="$(detect_app_hostname_from_nginx_site || true)"
  fi

  if [[ -z "$APP_HOSTNAME" ]]; then
    APP_HOSTNAME="$(detect_app_hostname_from_env_file || true)"
  fi

  if [[ -z "$APP_HOSTNAME" ]]; then
    if [[ -t 0 ]]; then
      read -r -p 'Telephony Toolbox hostname for nginx server_name: ' APP_HOSTNAME
    else
      die "APP_HOSTNAME is required for non-interactive installs when no existing configuration can be reused."
    fi
  fi

  APP_HOSTNAME="$(trim_value "$APP_HOSTNAME")"
  if [[ -z "$APP_HOSTNAME" ]]; then
    die "APP_HOSTNAME cannot be blank."
  fi

  if [[ "$APP_HOSTNAME" == *[[:space:]]* || "$APP_HOSTNAME" == *://* || "$APP_HOSTNAME" == */* ]]; then
    die "APP_HOSTNAME must be a single hostname without a scheme or path."
  fi
}

ensure_python_312() {
  log "Installing Python runtime and deployment dependencies"
  dnf -y install \
    python3.12 \
    python3.12-devel \
    python3.12-pip \
    gcc \
    gcc-c++ \
    make \
    libffi-devel \
    openssl-devel \
    postgresql-devel \
    libxml2-devel \
    libxslt-devel \
    xmlsec1 \
    xmlsec1-openssl \
    git \
    curl \
    nginx \
    policycoreutils-python-utils

  if command -v python3.12 >/dev/null 2>&1; then
    PYTHON_BIN="python3.12"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  else
    die "Python not found after package installation."
  fi

  local detected_version
  detected_version="$($PYTHON_BIN -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
  if [[ "${detected_version%%.*}" -lt 3 ]] || [[ "${detected_version%%.*}" -eq 3 && "${detected_version##*.}" -lt 12 ]]; then
    die "Python >= 3.12 is required, found $detected_version via $PYTHON_BIN"
  fi

  log "Using Python interpreter: $PYTHON_BIN ($detected_version)"
}

node_version_supported() {
  command -v node >/dev/null 2>&1 || return 1

  node <<'EOF' >/dev/null
const [major, minor] = process.versions.node.split('.').map(Number)
const supported = major >= 26 || major === 24 || (major === 22 && minor >= 12)
process.exit(supported ? 0 : 1)
EOF
}

ensure_nodejs_runtime() {
  if node_version_supported; then
    log "Using existing Node.js runtime: $(node --version)"
    return
  fi

  log "Installing Node.js ${NODE_MAJOR}.x for Quasar builds"
  dnf -y module disable nodejs || true
  curl -fsSL "https://rpm.nodesource.com/setup_${NODE_MAJOR}.x" | bash -
  dnf -y install nodejs

  if ! node_version_supported; then
    die "Node.js 22.12+, 24.x, or 26+ is required for frontend builds; found $(node --version 2>/dev/null || echo unavailable)."
  fi

  log "Using Node.js runtime: $(node --version)"
}

ensure_app_user_and_group() {
  if ! getent group "$APP_GROUP" >/dev/null 2>&1; then
    log "Creating system group: $APP_GROUP"
    groupadd --system "$APP_GROUP"
  fi

  if ! id "$APP_USER" >/dev/null 2>&1; then
    log "Creating system user: $APP_USER"
    useradd --system --home-dir "$APP_DIR" --shell /bin/bash --gid "$APP_GROUP" --no-create-home "$APP_USER"
  fi

  usermod -a -G "$APP_GROUP" "$APP_USER" || true

  if id "$NGINX_USER" >/dev/null 2>&1; then
    usermod -a -G "$APP_GROUP" "$NGINX_USER" || true
  else
    die "Expected nginx user '$NGINX_USER' was not created by the nginx package installation."
  fi
}

ensure_app_ownership() {
  log "Ensuring application ownership for $APP_DIR"
  chown -R "$APP_USER:$APP_GROUP" "$APP_DIR"
}

migrate_existing_repo_env() {
  local backup_path

  if [[ ! -f "$REPO_ENV_LINK" || -L "$REPO_ENV_LINK" ]]; then
    return
  fi

  mkdir -p "$ENV_DIR"

  if [[ ! -f "$ENV_FILE" ]]; then
    log "Migrating existing repo .env to $ENV_FILE"
    mv "$REPO_ENV_LINK" "$ENV_FILE"
    return
  fi

  backup_path="${REPO_ENV_LINK}.backup.$(date +%Y%m%d%H%M%S)"
  log "Backing up existing repo .env to $backup_path before switching to $ENV_FILE"
  mv "$REPO_ENV_LINK" "$backup_path"
  chown "$APP_USER:$APP_GROUP" "$backup_path" || true
}

load_log_dir_from_env_file() {
  local log_file

  if [[ "$LOG_DIR_WAS_PROVIDED" -eq 1 || ! -f "$ENV_FILE" ]]; then
    return
  fi

  log_file="$(sed -n 's/^DJANGO_LOG_FILE=//p' "$ENV_FILE" | tail -n 1)"
  log_file="$(strip_outer_quotes "$log_file")"
  if [[ -n "$log_file" ]]; then
    LOG_DIR="$(dirname "$log_file")"
  fi
}

generate_secret() {
  openssl rand -base64 48 | tr -d '\n'
}

ensure_env_dir() {
  mkdir -p "$ENV_DIR"
  chmod 750 "$ENV_DIR"
  chown root:"$APP_GROUP" "$ENV_DIR"
}

ensure_env_key() {
  local key="$1"
  local value="$2"

  if grep -q "^${key}=" "$ENV_FILE"; then
    return
  fi

  printf '%s=%s\n' "$key" "$value" >> "$ENV_FILE"
}

upsert_env_key() {
  local key="$1"
  local value="$2"
  local escaped

  escaped="$(printf '%s' "$value" | sed 's/[&|]/\\&/g')"
  if grep -q "^${key}=" "$ENV_FILE"; then
    sed -i "s|^${key}=.*$|${key}=${escaped}|" "$ENV_FILE"
  else
    printf '%s=%s\n' "$key" "$value" >> "$ENV_FILE"
  fi
}

write_backend_env() {
  local secret_key

  ensure_env_dir

  if [[ ! -f "$ENV_FILE" ]]; then
    secret_key="$(generate_secret)"
    log "Writing backend environment file: $ENV_FILE"
    cat > "$ENV_FILE" <<EOF
DJANGO_SECRET_KEY=$secret_key
DJANGO_ALLOWED_HOSTS=$APP_HOSTNAME,localhost,127.0.0.1
DJANGO_DEBUG=false
DJANGO_LOG_FILE=$LOG_DIR/application.log
DJANGO_LOG_LEVEL=INFO
CSRF_TRUSTED_ORIGINS=http://$APP_HOSTNAME,https://$APP_HOSTNAME

DATABASE_HOST=127.0.0.1
DATABASE_PORT=5432
DATABASE_NAME=telephonytoolbox
DATABASE_USER=telephonytoolbox
DATABASE_PASSWORD=change-me

AUTH_MODE=entra
LOCAL_AUTH_ENABLED=true

CUCM_AXL_HOST=
CUCM_AXL_USERNAME=
CUCM_AXL_PASSWORD=
CUCM_AXL_VERSION=14
CUCM_AXL_VERIFY_TLS=true
CUCM_ROUTE_PARTITION=INTERNAL

AUDIT_RETENTION_DAYS=90

ENTRA_CLIENT_ID=
ENTRA_CLIENT_SECRET=
ENTRA_TENANT_ID=
ENTRA_REDIRECT_URI=https://$APP_HOSTNAME/api/auth/login/entra/callback/

LDAP_SERVER_URI=
LDAP_BIND_DN=
LDAP_BIND_PASSWORD=
LDAP_USER_SEARCH_BASE=
LDAP_USER_EMAIL_ATTRIBUTE=mail
LDAP_USER_DISPLAY_NAME_ATTRIBUTE=displayName
LDAP_USER_ENABLED_ATTRIBUTE=
LDAP_GROUP_SEARCH_FILTER=
EOF
  else
    log "Existing backend environment file detected, preserving: $ENV_FILE"
  fi

  if [[ "$LOG_DIR_WAS_PROVIDED" -eq 1 ]]; then
    upsert_env_key "DJANGO_LOG_FILE" "$LOG_DIR/application.log"
  else
    ensure_env_key "DJANGO_LOG_FILE" "$LOG_DIR/application.log"
  fi

  ensure_env_key "DJANGO_LOG_LEVEL" "INFO"
  ensure_env_key "DJANGO_DEBUG" "false"
  ensure_env_key "DATABASE_HOST" "127.0.0.1"
  ensure_env_key "DATABASE_PORT" "5432"
  ensure_env_key "DATABASE_NAME" "telephonytoolbox"
  ensure_env_key "DATABASE_USER" "telephonytoolbox"
  ensure_env_key "DATABASE_PASSWORD" "change-me"
  ensure_env_key "AUTH_MODE" "entra"
  ensure_env_key "LOCAL_AUTH_ENABLED" "true"
  ensure_env_key "CUCM_AXL_VERSION" "14"
  ensure_env_key "CUCM_AXL_VERIFY_TLS" "true"
  ensure_env_key "CUCM_ROUTE_PARTITION" "INTERNAL"
  ensure_env_key "AUDIT_RETENTION_DAYS" "90"
  ensure_env_key "LDAP_USER_EMAIL_ATTRIBUTE" "mail"
  ensure_env_key "LDAP_USER_DISPLAY_NAME_ATTRIBUTE" "displayName"
  ensure_env_key "LDAP_USER_ENABLED_ATTRIBUTE" ""
  ensure_env_key "LDAP_GROUP_SEARCH_FILTER" ""
  if [[ -n "$APP_HOSTNAME" ]]; then
    ensure_env_key "DJANGO_ALLOWED_HOSTS" "$APP_HOSTNAME,localhost,127.0.0.1"
    ensure_env_key "CSRF_TRUSTED_ORIGINS" "http://$APP_HOSTNAME,https://$APP_HOSTNAME"
    ensure_env_key "ENTRA_REDIRECT_URI" "https://$APP_HOSTNAME/api/auth/login/entra/callback/"
  fi

  chmod 640 "$ENV_FILE"
  chown root:"$APP_GROUP" "$ENV_FILE"
}

link_repo_env_file() {
  if [[ -L "$REPO_ENV_LINK" || -e "$REPO_ENV_LINK" ]]; then
    rm -f "$REPO_ENV_LINK"
  fi

  ln -s "$ENV_FILE" "$REPO_ENV_LINK"
  chown -h "$APP_USER:$APP_GROUP" "$REPO_ENV_LINK"
}

ensure_log_dir() {
  log "Ensuring application log directory exists: $LOG_DIR"
  mkdir -p "$LOG_DIR"
  chown root:"$APP_GROUP" "$LOG_DIR"
  chmod 2775 "$LOG_DIR"

  touch \
    "$LOG_DIR/application.log" \
    "$LOG_DIR/gunicorn-access.log" \
    "$LOG_DIR/nginx-access.log" \
    "$LOG_DIR/nginx-error.log"

  chown root:"$APP_GROUP" \
    "$LOG_DIR/application.log" \
    "$LOG_DIR/gunicorn-access.log" \
    "$LOG_DIR/nginx-access.log" \
    "$LOG_DIR/nginx-error.log"

  chmod 664 \
    "$LOG_DIR/application.log" \
    "$LOG_DIR/gunicorn-access.log" \
    "$LOG_DIR/nginx-access.log" \
    "$LOG_DIR/nginx-error.log"
}

setup_backend_venv() {
  log "Creating backend virtual environment"
  run_as_app_user "$PYTHON_BIN -m venv '$VENV_DIR'"

  log "Installing backend Python dependencies"
  run_as_app_user "'$VENV_DIR/bin/pip' install --upgrade pip wheel setuptools"
  run_as_app_user "'$VENV_DIR/bin/pip' install -r '$BACKEND_DIR/requirements.txt'"
}

install_frontend_dependencies() {
  log "Installing frontend dependencies"
  if [[ -f "$FRONTEND_DIR/package-lock.json" ]]; then
    run_as_app_user "cd '$FRONTEND_DIR' && npm ci"
  else
    run_as_app_user "cd '$FRONTEND_DIR' && npm install"
  fi
}

build_frontend() {
  if [[ ! -f "$FRONTEND_DIR/.env.production" ]]; then
    log "Creating frontend production environment file"
    cat > "$FRONTEND_DIR/.env.production" <<'EOF'
VITE_API_BASE=/api
EOF
    chown "$APP_USER:$APP_GROUP" "$FRONTEND_DIR/.env.production"
    chmod 640 "$FRONTEND_DIR/.env.production"
  fi

  log "Building Quasar frontend"
  run_as_app_user "cd '$FRONTEND_DIR' && npm run build"

  if [[ ! -d "$FRONTEND_SPA_DIR" ]]; then
    die "Quasar build output not found at $FRONTEND_SPA_DIR"
  fi
}

apply_frontend_permissions() {
  log "Setting frontend permissions for nginx group access"
  chown -R "$APP_USER:$APP_GROUP" "$FRONTEND_DIST_DIR"
  chmod 750 "$APP_DIR" "$FRONTEND_DIR" "$FRONTEND_DIST_DIR" "$FRONTEND_SPA_DIR"
  find "$FRONTEND_SPA_DIR" -type d -exec chmod 750 {} +
  find "$FRONTEND_SPA_DIR" -type f -exec chmod 640 {} +
}

write_systemd_service() {
  log "Writing systemd service: $SYSTEMD_SERVICE_PATH"
  cat > "$SYSTEMD_SERVICE_PATH" <<EOF
[Unit]
Description=Telephony Toolbox Gunicorn service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$APP_USER
Group=$APP_GROUP
WorkingDirectory=$BACKEND_DIR
EnvironmentFile=$ENV_FILE
Environment=PYTHONUNBUFFERED=1
ExecStart=$VENV_DIR/bin/gunicorn telephony_toolbox.wsgi:application --workers 4 --worker-class sync --max-requests 1000 --max-requests-jitter 100 --timeout 60 --bind $BACKEND_BIND --access-logfile $LOG_DIR/gunicorn-access.log --error-logfile $LOG_DIR/application.log --capture-output --log-level info
Restart=always
RestartSec=5
UMask=0007

[Install]
WantedBy=multi-user.target
EOF

  chmod 644 "$SYSTEMD_SERVICE_PATH"
}

write_nginx_site() {
  log "Writing nginx site configuration: $NGINX_SITE_AVAILABLE_PATH"
  install -d -m 755 "$NGINX_SITES_AVAILABLE_DIR" "$NGINX_SITES_ENABLED_DIR"

  cat > "$NGINX_SITES_INCLUDE" <<EOF
include $NGINX_SITES_ENABLED_DIR/*.conf;
EOF

  cat > "$NGINX_SITE_AVAILABLE_PATH" <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name $APP_HOSTNAME;

    root $FRONTEND_SPA_DIR;
    index index.html;
    client_max_body_size 20m;

    location /assets/ {
        access_log off;
        expires 1y;
        add_header Cache-Control "public, immutable";
        try_files \$uri =404;
    }

    location /api/ {
        proxy_pass http://$BACKEND_BIND;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-Host \$host;
        proxy_set_header X-Forwarded-Port \$server_port;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Real-IP \$remote_addr;
    }

    location / {
        try_files \$uri \$uri/ /index.html;
    }

    location ~ /\. {
        deny all;
    }

    access_log $LOG_DIR/nginx-access.log;
    error_log $LOG_DIR/nginx-error.log;
}
EOF

  chmod 644 "$NGINX_SITE_AVAILABLE_PATH" "$NGINX_SITES_INCLUDE"
  ln -sfn "$NGINX_SITE_AVAILABLE_PATH" "$NGINX_SITE_ENABLED_PATH"
}

write_logrotate_config() {
  log "Writing logrotate configuration: $LOGROTATE_CONF"
  cat > "$LOGROTATE_CONF" <<EOF
$LOG_DIR/application.log $LOG_DIR/gunicorn-access.log $LOG_DIR/nginx-access.log $LOG_DIR/nginx-error.log {
    daily
    rotate 14
    dateext
    missingok
    notifempty
    compress
    delaycompress
    copytruncate
    su root $APP_GROUP
    create 0640 root $APP_GROUP
}
EOF

  chmod 644 "$LOGROTATE_CONF"
}

ensure_selinux_contexts() {
  if ! command -v selinuxenabled >/dev/null 2>&1 || ! selinuxenabled; then
    log "SELinux not enabled; skipping context updates"
    return
  fi

  if ! command -v semanage >/dev/null 2>&1; then
    die "semanage is required to manage SELinux file contexts. Install policycoreutils-python-utils."
  fi

  log "Applying SELinux file contexts"
  semanage fcontext -a -t usr_t "${APP_DIR}(/.*)?" 2>/dev/null || semanage fcontext -m -t usr_t "${APP_DIR}(/.*)?"
  semanage fcontext -a -t httpd_sys_content_t "${FRONTEND_SPA_DIR}(/.*)?" 2>/dev/null || semanage fcontext -m -t httpd_sys_content_t "${FRONTEND_SPA_DIR}(/.*)?"
  semanage fcontext -a -t httpd_log_t "${LOG_DIR}(/.*)?" 2>/dev/null || semanage fcontext -m -t httpd_log_t "${LOG_DIR}(/.*)?"
  restorecon -RF "$APP_DIR" "$LOG_DIR"

  log "Allowing nginx to proxy to the local Gunicorn port"
  setsebool -P httpd_can_network_connect 1
}

run_migrations() {
  log "Running Django migrations"
  run_as_app_user "set -a && source '$ENV_FILE' && set +a && cd '$BACKEND_DIR' && '$VENV_DIR/bin/python' manage.py migrate --noinput"
}

run_django_check() {
  log "Running Django system checks"
  run_as_app_user "set -a && source '$ENV_FILE' && set +a && cd '$BACKEND_DIR' && '$VENV_DIR/bin/python' manage.py check"
}

reload_systemd() {
  log "Reloading systemd configuration"
  systemctl daemon-reload
}

reload_nginx() {
  log "Validating nginx configuration"
  nginx -t
  systemctl enable nginx >/dev/null
  systemctl restart nginx
}

start_gunicorn_service() {
  log "Starting Gunicorn service: $SYSTEMD_SERVICE_NAME"
  systemctl enable "$SYSTEMD_SERVICE_NAME" >/dev/null
  if ! systemctl start "$SYSTEMD_SERVICE_NAME"; then
    systemctl status --no-pager "$SYSTEMD_SERVICE_NAME" || true
    return 1
  fi

  if ! systemctl is-active --quiet "$SYSTEMD_SERVICE_NAME"; then
    systemctl status --no-pager "$SYSTEMD_SERVICE_NAME" || true
    return 1
  fi
}

restart_gunicorn_service() {
  log "Restarting Gunicorn service: $SYSTEMD_SERVICE_NAME"
  systemctl enable "$SYSTEMD_SERVICE_NAME" >/dev/null
  if ! systemctl restart "$SYSTEMD_SERVICE_NAME"; then
    systemctl status --no-pager "$SYSTEMD_SERVICE_NAME" || true
    return 1
  fi

  if ! systemctl is-active --quiet "$SYSTEMD_SERVICE_NAME"; then
    systemctl status --no-pager "$SYSTEMD_SERVICE_NAME" || true
    return 1
  fi
}