#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Slinky Software

set -euo pipefail

LOG_PREFIX="install-rhel"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./rhel-deploy-common.sh
source "$SCRIPT_DIR/rhel-deploy-common.sh"

main() {
  local gunicorn_started=1

  require_root
  validate_paths

  log "Starting stage 2 installation execution"
  migrate_existing_repo_env
  resolve_app_hostname
  ensure_python_312
  ensure_nodejs_runtime
  ensure_app_user_and_group
  ensure_app_ownership
  write_backend_env
  load_log_dir_from_env_file
  validate_log_dir
  link_repo_env_file
  ensure_log_dir
  setup_backend_venv
  install_frontend_dependencies
  build_frontend
  apply_frontend_permissions
  write_systemd_service
  write_nginx_site
  write_logrotate_config
  ensure_selinux_contexts

  if ! run_migrations; then
    log "Migrations failed. Update $ENV_FILE with the correct database settings and rerun them manually."
  fi

  if ! run_django_check; then
    log "Django system checks failed. Review $ENV_FILE before putting the service into production."
  fi

  reload_systemd
  reload_nginx
  if ! start_gunicorn_service; then
    gunicorn_started=0
    log "Gunicorn did not start cleanly. Check 'systemctl status $SYSTEMD_SERVICE_NAME' after updating the environment file."
  fi

  cat <<EOF

Installation completed.

Deployment defaults:
1. Application directory: $APP_DIR
2. Backend bind: $BACKEND_BIND
3. Nginx site: $NGINX_SITE_ENABLED_PATH
4. Environment file: $ENV_FILE

Next steps:
1. Edit $ENV_FILE with production database, auth, and CUCM values.
2. Bootstrap the first local App Admin:
   sudo -u $APP_USER -H bash -lc "set -a && source '$ENV_FILE' && set +a && cd '$BACKEND_DIR' && '$VENV_DIR/bin/python' manage.py bootstrap_local_app_admin --email admin@example.com --display-name 'App Admin' --password 'ChangeMeNow!'"
3. If you changed database settings, rerun migrations:
   sudo -u $APP_USER -H bash -lc "set -a && source '$ENV_FILE' && set +a && cd '$BACKEND_DIR' && '$VENV_DIR/bin/python' manage.py migrate --noinput"
4. Restart the backend after environment changes:
   sudo systemctl restart $SYSTEMD_SERVICE_NAME

Gunicorn service status after install: $( [[ "$gunicorn_started" -eq 1 ]] && echo started || echo review-required )
EOF
}

main "$@"