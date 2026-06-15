# Telephony Toolbox

Telephony Toolbox is a web application for managing Cisco UCM Call Forward All (CFA) diversions with strict destination validation, role-based access control, comprehensive audit logging, and flexible authentication support.

## Overview

Telephony Toolbox provides a safe, audited interface for authorized users to update diversion destinations for pre-defined Cisco UCM Directory Numbers, using the UCM AXL API as the source of truth for live state.

It is designed to be extensible so that if core telephony platforms are later moved from CUCM to a different application (eg Asterisk, Freeswitch, or hosted provider) then the user experience for diversion management remains consistent, with the backend API calls modified appropriately.

### Key Features

- **Diversion Management**: View and update Call Forward All destinations for assigned diversions
- **Strict Validation**: Destination numbers are validated and normalized to Australian +E.164 format
- **Role-Based Access**: Two application roles (Standard User, App Admin) with group-based diversion access
- **Flexible Authentication**: Support for Entra (OIDC), LDAP, or local user authentication with CSRF protection
- **Audit Logging**: Complete audit trail with 90-day retention for compliance
- **CUCM Integration**: Uses Cisco AXL API with support for CUCM versions 8.0–14
- **Responsive UI**: Quasar Vue 3 frontend with admin dashboards for user and group management
- **Graceful Degradation**: Allows cached state viewing when CUCM is unavailable; blocks edits

## Stack

- **Frontend**: Quasar SPA on Vue 3 with responsive Quasar components
- **Backend**: Django 5.2 + Django REST Framework with session authentication
- **Database**: PostgreSQL in production; SQLite for local development
- **Authentication**: Django sessions with CSRF; Entra OIDC, LDAP, and local users
- **CUCM Integration**: Zeep SOAP client with versioned local WSDL schemas
- **Deployment**: nginx (static files & proxy), Gunicorn, systemd on RHEL 9

## Documentation

- [ARCHITECTURE.md](docs/ARCHITECTURE.md) — System design, data flow, and component interactions
- [API_SPECIFICATION.md](docs/API_SPECIFICATION.md) — REST API endpoints, authentication, and request/response formats
- [CONFIGURATION.md](docs/CONFIGURATION.md) — Environment variables and deployment settings
- [AUTHENTICATION.md](docs/AUTHENTICATION.md) — Authentication flows and identity provider setup
- [DEVELOPMENT.md](docs/DEVELOPMENT.md) — Local development setup and testing
- [DEPLOYMENT.md](docs/DEPLOYMENT.md) — Production deployment on RHEL 9 with nginx and Gunicorn

## Quick Start: Local Development

### Prerequisites

- Python 3.10+
- Node.js 18+ with pnpm
- PostgreSQL (optional; SQLite used by default)

### Setup

1. Clone the repository and navigate to the root directory.

2. Create an environment file:

	```bash
	cp scripts/env.example .env
	```

3. Create and activate a Python virtual environment:

	```bash
	python3 -m venv .venv
	source .venv/bin/activate
	pip install -r backend/requirements.txt
	```

4. Install frontend dependencies:

	```bash
	pnpm --prefix frontend install
	```

5. Run database migrations:

	```bash
	python backend/manage.py migrate
	```

6. (Optional) Create a bootstrap app admin:

	```bash
	python backend/manage.py bootstrap_local_app_admin \
	  --email admin@example.com \
	  --display-name "App Admin" \
	  --password 'ChangeMeNow!'
	```

7. Start the development servers:

	```bash
	# Terminal 1: Backend on http://localhost:8000
	python backend/manage.py runserver 0.0.0.0:8000

	# Terminal 2: Frontend on http://localhost:9000 (proxies /api to backend)
	pnpm --prefix frontend run dev
	```

### Testing

Run tests from the repository root:

```bash
# Backend tests
.venv/bin/pytest

# Frontend tests (if configured)
pnpm --prefix frontend run test
```

## User Roles and Permissions

| Role | Capabilities |
|------|--------------|
| **Standard User** | View assigned diversions, update CFA destinations (when CUCM available), audit access |
| **App Admin** | Full user and group management, create/edit/delete diversions, access all groups' diversions, export audit logs, health monitoring |

## Destination Validation

Accepted destination formats:

- **Australian FNN**: `(02, 03, 07, 08) + 8 digits` → normalized to `+612...` or `+613...` etc.
- **Australian Mobile**: `04 + 8 digits` → normalized to `+614...`
- **E.164 Format**: `+61...` (Australian country code only)

Rejected:

- Internal extensions (< 10 digits)
- International numbers (including `0011` prefix)
- SIP URIs and email-like formats
- Blank destinations
- Leading + characters outside +61 format

## Common Deployment Scenarios

### Development with SQLite

Simplest setup; no database configuration needed. Suitable for testing and feature development.

### Staging/Production with PostgreSQL

See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for full production setup with nginx, Gunicorn, systemd, and SELinux configuration.

## Project Structure

```
backend/               # Django REST Framework backend
  accounts/           # User management, authentication, roles
  access_groups/      # Group definitions and memberships
  diversions/         # Diversion CRUD and update operations
  audit/              # Audit event logging and export
  cucm/               # CISCO AXL client and schemas
  dialplan/           # Phone number validation and normalization
  health/             # System health endpoints
  telephony_toolbox/  # Django configuration and URL routing

frontend/             # Quasar Vue 3 SPA
  src/
    pages/           # Page components (login, diversions, admin)
    components/      # Reusable UI components
    stores/          # Pinia state management
    services/        # API client and business logic
    router/          # Route definitions

docs/                 # Documentation (this directory)
  ARCHITECTURE.md
  API_SPECIFICATION.md
  CONFIGURATION.md
  AUTHENTICATION.md
  DEVELOPMENT.md
  DEPLOYMENT.md

scripts/              # Deployment and utility scripts
  install-rhel-baremetal.sh
  upgrade-rhel-baremetal.sh

wsdl/                 # Versioned CISCO AXL WSDL schemas
```

## Troubleshooting

**CUCM is unavailable**: Check backend logs and CUCM AXL connectivity. The UI shows "unavailable" status; cached diversions remain viewable but edits are blocked.

**Authentication fails**: Verify ENTRA or LDAP settings in `.env`. Check authentication provider connectivity and user existence.

**Database migration errors**: Ensure Django settings reference the correct database backend (PostgreSQL or SQLite).

For more details, see [DEVELOPMENT.md](docs/DEVELOPMENT.md) and [DEPLOYMENT.md](docs/DEPLOYMENT.md).

- Backend checks: `.venv/bin/python backend/manage.py check`
- Backend tests: `.venv/bin/pytest -q`
- Frontend build: `npm --prefix frontend run build`

## Install and Upgrade Scripts

- Fresh RHEL 9 install: [scripts/install-rhel-baremetal.sh](scripts/install-rhel-baremetal.sh)
- Upgrade existing RHEL 9 deployment: [scripts/upgrade-rhel-baremetal.sh](scripts/upgrade-rhel-baremetal.sh)
- Environment template: [scripts/env.example](scripts/env.example)
- Systemd template: [scripts/templates/telephonytoolbox-gunicorn.service.template](scripts/templates/telephonytoolbox-gunicorn.service.template)
- nginx template: [scripts/templates/telephonytoolbox.nginx.conf.template](scripts/templates/telephonytoolbox.nginx.conf.template)

The RHEL install flow defaults to `/opt/telephonytoolbox`, binds Gunicorn to `127.0.0.1:8010`, creates a dedicated nginx site under `sites-enabled`, and prompts for `APP_HOSTNAME` when it is not already supplied in the environment.

# License

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, version 3.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program.  If not, see <https://www.gnu.org/licenses/>.