#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
APP_ROOT="${APP_ROOT:-$REPO_ROOT}"
BACKEND_DIR="$APP_ROOT/backend"
FRONTEND_DIR="$APP_ROOT/frontend"
VENV_PATH="${VENV_PATH:-$APP_ROOT/.venv}"
ENV_FILE="${ENV_FILE:-$APP_ROOT/.env}"
RUN_TESTS="${RUN_TESTS:-true}"
BOOTSTRAP_ADMIN_ENABLED="${BOOTSTRAP_ADMIN_ENABLED:-true}"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

load_environment() {
  if [[ -f "$ENV_FILE" ]]; then
    set -a
    # shellcheck source=/dev/null
    source "$ENV_FILE"
    set +a
  fi
}

bootstrap_admin() {
  local email="${BOOTSTRAP_ADMIN_EMAIL:-}"
  local display_name="${BOOTSTRAP_ADMIN_DISPLAY_NAME:-}"
  local password="${BOOTSTRAP_ADMIN_PASSWORD:-}"

  if [[ "$BOOTSTRAP_ADMIN_ENABLED" != "true" ]]; then
    return 0
  fi

  if [[ -z "$email" ]]; then
    read -r -p 'Bootstrap App Admin email: ' email
  fi

  if [[ -z "$display_name" ]]; then
    read -r -p 'Bootstrap App Admin display name: ' display_name
  fi

  if [[ -z "$password" ]]; then
    read -r -s -p 'Bootstrap App Admin password: ' password
    printf '\n'
  fi

  "$VENV_PATH/bin/python" "$BACKEND_DIR/manage.py" bootstrap_local_app_admin \
    --email "$email" \
    --display-name "$display_name" \
    --password "$password"
}

main() {
  require_command python3
  require_command npm

  load_environment

  python3 -m venv "$VENV_PATH"
  "$VENV_PATH/bin/pip" install --upgrade pip
  "$VENV_PATH/bin/pip" install -r "$BACKEND_DIR/requirements.txt"

  npm --prefix "$FRONTEND_DIR" ci
  npm --prefix "$FRONTEND_DIR" run build

  "$VENV_PATH/bin/python" "$BACKEND_DIR/manage.py" migrate --noinput

  if [[ "$RUN_TESTS" == "true" ]]; then
    "$VENV_PATH/bin/pytest" -q "$APP_ROOT"
  fi

  bootstrap_admin

  cat <<EOF

Install completed.

Next steps:
1. Copy $SCRIPT_DIR/templates/telephony-toolbox-gunicorn.service.template into /etc/systemd/system/ and replace placeholders.
2. Copy $SCRIPT_DIR/templates/telephony-toolbox.nginx.conf.template into your nginx vhost directory and replace placeholders.
3. Ensure nginx serves $FRONTEND_DIR/dist/spa and proxies /api/ to gunicorn.
EOF
}

main "$@"