#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
APP_ROOT="${APP_ROOT:-$REPO_ROOT}"
BACKEND_DIR="$APP_ROOT/backend"
FRONTEND_DIR="$APP_ROOT/frontend"
VENV_PATH="${VENV_PATH:-$APP_ROOT/.venv}"
ENV_FILE="${ENV_FILE:-$APP_ROOT/.env}"
SYSTEMD_SERVICE_NAME="${SYSTEMD_SERVICE_NAME:-telephony-toolbox-gunicorn.service}"
RESTART_SERVICE="${RESTART_SERVICE:-false}"

load_environment() {
  if [[ -f "$ENV_FILE" ]]; then
    set -a
    # shellcheck source=/dev/null
    source "$ENV_FILE"
    set +a
  fi
}

main() {
  load_environment

  "$VENV_PATH/bin/pip" install --upgrade pip
  "$VENV_PATH/bin/pip" install -r "$BACKEND_DIR/requirements.txt"

  npm --prefix "$FRONTEND_DIR" ci
  npm --prefix "$FRONTEND_DIR" run build

  "$VENV_PATH/bin/python" "$BACKEND_DIR/manage.py" migrate --noinput
  "$VENV_PATH/bin/pytest" -q "$APP_ROOT"

  if [[ "$RESTART_SERVICE" == "true" ]]; then
    systemctl daemon-reload
    systemctl restart "$SYSTEMD_SERVICE_NAME"
  fi

  echo 'Upgrade completed.'
}

main "$@"