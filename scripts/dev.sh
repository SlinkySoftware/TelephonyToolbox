#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

ENV_FILE="$REPO_ROOT/.env"
BACKEND_DIR="$REPO_ROOT/backend"
FRONTEND_DIR="$REPO_ROOT/frontend"
RUN_DIR="$REPO_ROOT/var/run"
LOG_DIR="$REPO_ROOT/var/log/dev"

BACKEND_PID_FILE="$RUN_DIR/dev-backend.pid"
FRONTEND_PID_FILE="$RUN_DIR/dev-frontend.pid"
BACKEND_LOG_FILE="$LOG_DIR/backend.log"
FRONTEND_LOG_FILE="$LOG_DIR/frontend.log"

usage() {
  cat << EOF
Usage: $0 [--env FILE] <start|stop|restart|status> [backend|frontend|all]

Controls the local Django and Quasar development servers.

Options:
  --env FILE   Environment file to load before starting services.
               Defaults to .env in the repository root.

Examples:
  $0 start
  $0 status
  $0 restart backend
  $0 stop frontend

Environment overrides:
  DEV_BACKEND_BIND   Django bind address, default 0.0.0.0:8000
  DEV_FRONTEND_URL   Displayed frontend URL, default http://localhost:9000
EOF
}

die() {
  echo "$*" >&2
  exit 1
}

log() {
  echo "[dev] $*"
}

resolve_path() {
  local path="$1"
  if [[ "$path" == /* ]]; then
    printf '%s\n' "$path"
  else
    printf '%s\n' "$REPO_ROOT/$path"
  fi
}

trim() {
  local value="$1"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  printf '%s' "$value"
}

strip_outer_quotes() {
  local value="$1"
  if [[ ${#value} -ge 2 ]]; then
    if [[ "${value:0:1}" == '"' && "${value: -1}" == '"' ]]; then
      value="${value:1:${#value}-2}"
    elif [[ "${value:0:1}" == "'" && "${value: -1}" == "'" ]]; then
      value="${value:1:${#value}-2}"
    fi
  fi
  printf '%s' "$value"
}

load_env_file() {
  if [[ ! -f "$ENV_FILE" ]]; then
    echo "Environment file not found: $ENV_FILE" >&2
    die "Create one with: cp scripts/env.example .env"
  fi

  local raw_line line key value
  while IFS= read -r raw_line || [[ -n "$raw_line" ]]; do
    line="${raw_line%$'\r'}"
    line="$(trim "$line")"
    if [[ -z "$line" || "${line:0:1}" == '#' || "$line" != *=* ]]; then
      continue
    fi

    key="$(trim "${line%%=*}")"
    value="$(trim "${line#*=}")"
    value="$(strip_outer_quotes "$value")"

    if [[ ! "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
      die "Invalid environment variable name in $ENV_FILE: $key"
    fi

    export "$key=$value"
  done < "$ENV_FILE"
}

ensure_directories() {
  mkdir -p "$RUN_DIR" "$LOG_DIR"
}

python_bin() {
  if [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
    printf '%s\n' "$REPO_ROOT/.venv/bin/python"
  elif command -v python3 >/dev/null 2>&1; then
    command -v python3
  else
    die "python3 was not found. Create .venv or install Python first."
  fi
}

npm_bin() {
  if command -v npm >/dev/null 2>&1; then
    command -v npm
  else
    die "npm was not found. Install Node.js/npm first."
  fi
}

is_running() {
  local pid_file="$1"
  local pid

  [[ -f "$pid_file" ]] || return 1
  pid="$(cat "$pid_file")"
  [[ "$pid" =~ ^[0-9]+$ ]] || return 1
  kill -0 "$pid" >/dev/null 2>&1
}

remove_stale_pid() {
  local pid_file="$1"
  if [[ -f "$pid_file" ]] && ! is_running "$pid_file"; then
    rm -f "$pid_file"
  fi
}

start_process() {
  local name="$1"
  local pid_file="$2"
  local log_file="$3"
  shift 3

  remove_stale_pid "$pid_file"
  if is_running "$pid_file"; then
    log "$name is already running (pid $(cat "$pid_file"))"
    return
  fi

  ensure_directories
  : > "$log_file"

  (
    cd "$REPO_ROOT"
    if command -v setsid >/dev/null 2>&1; then
      exec setsid "$@"
    fi
    exec "$@"
  ) >> "$log_file" 2>&1 &

  echo "$!" > "$pid_file"
  log "started $name (pid $(cat "$pid_file"), log $log_file)"
}

stop_process() {
  local name="$1"
  local pid_file="$2"
  local pid

  remove_stale_pid "$pid_file"
  if ! is_running "$pid_file"; then
    log "$name is not running"
    return
  fi

  pid="$(cat "$pid_file")"
  log "stopping $name (pid $pid)"
  if ! kill -TERM -- "-$pid" >/dev/null 2>&1; then
    kill -TERM "$pid" >/dev/null 2>&1 || true
  fi

  for _ in {1..20}; do
    if ! kill -0 "$pid" >/dev/null 2>&1; then
      rm -f "$pid_file"
      log "stopped $name"
      return
    fi
    sleep 0.25
  done

  log "$name did not stop after TERM; sending KILL"
  if ! kill -KILL -- "-$pid" >/dev/null 2>&1; then
    kill -KILL "$pid" >/dev/null 2>&1 || true
  fi
  rm -f "$pid_file"
  log "stopped $name"
}

status_process() {
  local name="$1"
  local pid_file="$2"
  local log_file="$3"

  remove_stale_pid "$pid_file"
  if is_running "$pid_file"; then
    log "$name: running (pid $(cat "$pid_file"), log $log_file)"
  else
    log "$name: stopped"
  fi
}

start_backend() {
  load_env_file
  local backend_bind="${DEV_BACKEND_BIND:-0.0.0.0:8000}"
  [[ -f "$BACKEND_DIR/manage.py" ]] || die "Django manage.py not found: $BACKEND_DIR/manage.py"
  start_process "backend" "$BACKEND_PID_FILE" "$BACKEND_LOG_FILE" "$(python_bin)" "$BACKEND_DIR/manage.py" runserver "$backend_bind"
  log "backend URL: http://localhost:${backend_bind##*:}/api/"
}

start_frontend() {
  load_env_file
  local frontend_url="${DEV_FRONTEND_URL:-http://localhost:9000}"
  [[ -f "$FRONTEND_DIR/package.json" ]] || die "Frontend package.json not found: $FRONTEND_DIR/package.json"
  start_process "frontend" "$FRONTEND_PID_FILE" "$FRONTEND_LOG_FILE" "$(npm_bin)" --prefix "$FRONTEND_DIR" run dev
  log "frontend URL: $frontend_url"
}

stop_backend() {
  stop_process "backend" "$BACKEND_PID_FILE"
}

stop_frontend() {
  stop_process "frontend" "$FRONTEND_PID_FILE"
}

status_backend() {
  status_process "backend" "$BACKEND_PID_FILE" "$BACKEND_LOG_FILE"
}

status_frontend() {
  status_process "frontend" "$FRONTEND_PID_FILE" "$FRONTEND_LOG_FILE"
}

run_for_service() {
  local action="$1"
  local service="$2"

  case "$service" in
    backend)
      "${action}_backend"
      ;;
    frontend)
      "${action}_frontend"
      ;;
    all)
      if [[ "$action" == stop ]]; then
        "${action}_frontend"
        "${action}_backend"
      else
        "${action}_backend"
        "${action}_frontend"
      fi
      ;;
    *)
      die "Unknown service: $service"
      ;;
  esac
}

main() {
  local command=""
  local service="all"

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --env)
        [[ $# -ge 2 ]] || die "--env requires a file path"
        ENV_FILE="$(resolve_path "$2")"
        shift 2
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      start|stop|restart|status)
        command="$1"
        shift
        ;;
      backend|frontend|all)
        service="$1"
        shift
        ;;
      *)
        die "Unknown argument: $1"
        ;;
    esac
  done

  command="${command:-status}"

  case "$command" in
    start|stop|status)
      run_for_service "$command" "$service"
      ;;
    restart)
      run_for_service stop "$service"
      run_for_service start "$service"
      ;;
    *)
      die "Unknown command: $command"
      ;;
  esac
}

main "$@"