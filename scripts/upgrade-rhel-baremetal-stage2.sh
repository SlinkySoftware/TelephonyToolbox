#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Slinky Software

set -euo pipefail

LOG_PREFIX="upgrade-rhel"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./rhel-deploy-common.sh
source "$SCRIPT_DIR/rhel-deploy-common.sh"

main() {
  require_root
  validate_paths

  log "Starting stage 2 upgrade execution"
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
  run_migrations
  run_django_check
  write_systemd_service
  write_nginx_site
  write_logrotate_config
  ensure_selinux_contexts
  reload_systemd
  reload_nginx
  restart_gunicorn_service

  cat <<EOF

Upgrade completed successfully.

Executed steps:
1. Stage 1 refreshed the git checkout.
2. Revalidated Python and Node.js build/runtime dependencies.
3. Ensured ownership, nginx group access, and SELinux contexts.
4. Reinstalled backend and frontend dependencies.
5. Rebuilt the Quasar SPA and refreshed nginx/systemd configuration.
6. Ran Django migrations and system checks.
7. Restarted $SYSTEMD_SERVICE_NAME on $BACKEND_BIND.

EOF
}

main "$@"