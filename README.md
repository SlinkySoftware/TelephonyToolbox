# Telephony Toolbox

Telephony Toolbox is a Quasar frontend and Django REST Framework backend for managing Cisco UCM Call Forward All diversions with strict destination validation, local RBAC, audit logging, and external authentication support.

## Stack

- Frontend: Quasar SPA on Vue 3
- Backend: Django 5.2 + DRF
- Auth: Django sessions with CSRF, Entra OIDC, LDAP, local fallback users
- Database: PostgreSQL in production, SQLite fallback for local development
- CUCM: Cisco AXL via versioned local WSDLs and Zeep

## Local Development

1. Create and populate an environment file from [scripts/env.example](scripts/env.example).
2. Create the Python virtual environment and install dependencies:

	```bash
	python3 -m venv .venv
	.venv/bin/pip install -r backend/requirements.txt
	```

3. Install frontend dependencies:

	```bash
	npm --prefix frontend install
	```

4. Run backend migrations:

	```bash
	.venv/bin/python backend/manage.py migrate
	```

5. Optionally bootstrap the first local App Admin:

	```bash
	.venv/bin/python backend/manage.py bootstrap_local_app_admin --email admin@example.com --display-name "App Admin" --password 'ChangeMeNow!'
	```

6. Start the backend and frontend:

	```bash
	.venv/bin/python backend/manage.py runserver 0.0.0.0:8000
	npm --prefix frontend run dev
	```

The Quasar dev server proxies `/api` to Django on port `8000`.

## Validation

- Backend checks: `.venv/bin/python backend/manage.py check`
- Backend tests: `.venv/bin/pytest -q`
- Frontend build: `npm --prefix frontend run build`

## Install and Upgrade Scripts

- Fresh install: [scripts/install.sh](scripts/install.sh)
- Upgrade existing deployment: [scripts/upgrade.sh](scripts/upgrade.sh)
- Environment template: [scripts/env.example](scripts/env.example)
- Systemd template: [scripts/templates/telephony-toolbox-gunicorn.service.template](scripts/templates/telephony-toolbox-gunicorn.service.template)
- nginx template: [scripts/templates/telephony-toolbox.nginx.conf.template](scripts/templates/telephony-toolbox.nginx.conf.template)

# License

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, version 3.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program.  If not, see <https://www.gnu.org/licenses/>.