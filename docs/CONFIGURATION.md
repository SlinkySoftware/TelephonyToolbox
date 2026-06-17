# Telephony Toolbox Configuration Guide

Complete reference for all configuration options via environment variables.

## Overview

Telephony Toolbox is configured entirely through environment variables, which are loaded from a `.env` file in the repository root during startup. This approach supports both local development and production deployment without code changes.

See [scripts/env.example](../scripts/env.example) for a template file.

## Environment File Location

- **Development**: `.env` in repository root (created from `scripts/env.example`)
- **Production**: `/etc/telephonytoolbox/backend.env` (symlinked to repository `.env`)

## Configuration Categories

### Core Django Settings

#### `DJANGO_SECRET_KEY`

**Type**: String (alphanumeric, special characters allowed)  
**Required**: Yes  
**Default**: `telephony-toolbox-dev-secret-key` (development only)  
**Example**: `your-secret-key-12345`

Secret key for Django session signing and CSRF token generation. Must be cryptographically random and unique per deployment.

**Security**: 
- Never commit actual keys to repository; use unique value per environment
- Minimum 50 characters recommended
- Change periodically in production
- All sessions invalidated after key change

**Generate**:
```bash
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

#### `DJANGO_ALLOWED_HOSTS`

**Type**: Comma-separated list  
**Required**: Yes  
**Default**: `localhost,127.0.0.1`  
**Example**: `telephonytoolbox.example.internal,localhost,127.0.0.1`

Host headers the application accepts. Used to prevent HTTP Host header attacks.

**Development**: Automatically includes `localhost`, `127.0.0.1`, `0.0.0.0`, `[::1]` when `DJANGO_DEBUG=true` or runserver is active.

**Production**: Explicitly list all hostnames/IPs where the application is accessible.

---

#### `DJANGO_DEBUG`

**Type**: Boolean (`true`, `false`, `1`, `0`)  
**Required**: No  
**Default**: `true` (development), `false` (production)  
**Example**: `false`

Enable/disable Django debug mode.

**⚠️ WARNING**: Never set `true` in production. Debug mode exposes:
- Full exception tracebacks with source code
- SQL queries and database credentials
- Environment variables
- Internal paths and IP addresses

**Development**: Can be `true`; debug toolbar and detailed error pages helpful.

**Production**: MUST be `false`; critical security requirement.

---

#### `DJANGO_LOG_FILE`

**Type**: File path (absolute)  
**Required**: No  
**Default**: `./backend/logs/telephony_toolbox.log` (relative to repository root)  
**Example**: `/var/log/telephonytoolbox/application.log`

Path to application log file. Backend creates directory if it doesn't exist.

**Development**: `./backend/logs/telephony_toolbox.log` (logged to `backend/logs/` in repo)

**Production**: `/var/log/telephonytoolbox/application.log` (application user must have write permissions)

**If Invalid**: Application logs to console instead (fallback).

---

#### `DJANGO_LOG_LEVEL`

**Type**: Enum (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`)  
**Required**: No  
**Default**: `INFO`  
**Example**: `DEBUG`

Minimum log level to capture.

| Level | When to Use |
|-------|------------|
| `DEBUG` | Development; captures detailed execution flow |
| `INFO` | Production; captures events and status changes |
| `WARNING` | Only warnings and above (errors, critical) |
| `ERROR` | Only errors and critical issues |

**Production**: Recommend `INFO` for balance between visibility and log volume.

---

#### `CSRF_TRUSTED_ORIGINS`

**Type**: Comma-separated list (HTTPS URLs)  
**Required**: No (defaults to `DJANGO_ALLOWED_HOSTS`)  
**Default**: Derived from `DJANGO_ALLOWED_HOSTS`  
**Example**: `https://telephonytoolbox.example.internal,https://localhost:9000`

Trusted origins for CSRF validation. Required when frontend and backend are on different domains/ports.

**Development**: If frontend dev server runs on `http://localhost:9000` and backend on `http://localhost:8000`, add `http://localhost:9000`.

**Production**: Must include HTTPS URL where frontend is served.

**Format**: Full URLs with protocol, no trailing slash.

---

### Database Configuration

#### `DATABASE_NAME`

**Type**: String (database name)  
**Required**: No  
**Default**: None (uses SQLite fallback)  
**Example**: `telephonytoolbox`

PostgreSQL database name. If empty, SQLite is used instead.

---

#### `DATABASE_HOST`

**Type**: String (hostname or IP)  
**Required**: No  
**Default**: `localhost`  
**Example**: `db.example.internal` or `10.0.1.50`

PostgreSQL server hostname or IP address.

**Ignored** if `DATABASE_NAME` is empty (SQLite mode).

---

#### `DATABASE_PORT`

**Type**: Integer  
**Required**: No  
**Default**: `5432`  
**Example**: `5432`

PostgreSQL server port.

**Ignored** if `DATABASE_NAME` is empty.

---

#### `DATABASE_USER`

**Type**: String  
**Required**: No  
**Default**: None  
**Example**: `telephonytoolbox`

PostgreSQL username. Required if `DATABASE_NAME` is set.

**Ignored** if `DATABASE_NAME` is empty.

---

#### `DATABASE_PASSWORD`

**Type**: String  
**Required**: No  
**Default**: None (no password)  
**Example**: `SecurePassword123!`

PostgreSQL password. Can be empty if database allows password-less access.

**Security**: Never commit to repository; use environment-specific values.

**Ignored** if `DATABASE_NAME` is empty.

---

### Authentication Configuration

#### `AUTH_MODE`

**Type**: Enum (`entra`, `ldap`, `oidc`)  
**Required**: No  
**Default**: `entra`  
**Example**: `ldap`

Primary authentication provider. Determines which login form frontend displays and which backend service validates credentials.

**Supported Values**:
- `entra` — Microsoft Entra ID (OIDC)
- `ldap` — LDAP directory server
- `oidc` — Generic OpenID Connect / OAuth 2.0 provider with discovery metadata

**Local Fallback**: Enabled regardless of `AUTH_MODE` (controlled by `LOCAL_AUTH_ENABLED`).

---

#### `EXTERNAL_AUTH_NAME`

**Type**: String  
**Required**: No  
**Default**: Provider-specific (`Entra`, `LDAP`, or `OpenID Connect`)  
**Example**: `Enterprise Sign In`

Friendly label shown on frontend sign-in screens for the configured external provider.

**Usage**:
- Customize the login button text users see
- Use provider branding such as `Authentik Login`, `OKTA Login`, or `Enterprise Sign In`
- Display only; not used for backend routing or provider selection

---

#### `LOCAL_AUTH_ENABLED`

**Type**: Boolean (`true`, `false`)  
**Required**: No  
**Default**: `true`  
**Example**: `false`

Enable/disable local user authentication (email + password credentials).

**Development**: Typically `true` for testing without external providers.

**Production**: Can be `false` if all users provisioned via Entra/LDAP; local accounts used for emergency access.

**Important**: Local fallback is always available for App Admin accounts created via `bootstrap_local_app_admin` command.

---

### Entra Configuration

Required if `AUTH_MODE=entra`.

#### `ENTRA_CLIENT_ID`

**Type**: UUID  
**Required**: If `AUTH_MODE=entra`  
**Default**: None  
**Example**: `12345678-1234-1234-1234-123456789012`

Microsoft Entra application ID (from Azure Portal → Entra ID → App registrations).

---

#### `ENTRA_CLIENT_SECRET`

**Type**: String (cryptographic secret)  
**Required**: If `AUTH_MODE=entra`  
**Default**: None  
**Example**: `abc123_DEF456-ghi789~`

Client secret for OAuth token exchange. Generated in Azure Portal.

**Security**: 
- Never commit to repository
- Rotate periodically in production
- Treat as sensitive as database password

---

#### `ENTRA_TENANT_ID`

**Type**: UUID or domain  
**Required**: If `AUTH_MODE=entra`  
**Default**: None  
**Example**: `12345678-1234-1234-1234-123456789012` or `contoso.onmicrosoft.com`

Entra Directory ID (tenant ID). Found in Azure Portal → Entra ID → Overview.

---

#### `ENTRA_REDIRECT_URI`

**Type**: HTTPS URL  
**Required**: If `AUTH_MODE=entra`  
**Default**: None  
**Example**: `https://telephonytoolbox.example.internal/api/auth/login/entra/callback/`

OAuth2 callback URL registered in Entra app. Must match exactly (including trailing slash).

**Must be HTTPS** in production (unless localhost for dev).

**Registration**: Add in Azure Portal → Entra ID → App registrations → [App] → Authentication → Redirect URIs.

---

### Generic OIDC/OAuth Configuration

Required if `AUTH_MODE=oidc`.

#### `OIDC_CLIENT_ID`

**Type**: String  
**Required**: If `AUTH_MODE=oidc`  
**Default**: None  
**Example**: `telephony-toolbox`

OAuth client ID registered with your OpenID Connect provider.

---

#### `OIDC_CLIENT_SECRET`

**Type**: String  
**Required**: If `AUTH_MODE=oidc`  
**Default**: None  
**Example**: `change-me`

OAuth client secret used for token exchange.

---

#### `OIDC_METADATA_URL`

**Type**: HTTPS URL  
**Required**: If `AUTH_MODE=oidc`  
**Default**: None  
**Example**: `https://auth.example.internal/application/o/telephony-toolbox/.well-known/openid-configuration`

OpenID Connect discovery document URL. The application reads authorization, token, JWKS, and userinfo endpoints from this metadata.

---

#### `OIDC_REDIRECT_URI`

**Type**: HTTPS URL  
**Required**: If `AUTH_MODE=oidc`  
**Default**: None  
**Example**: `https://telephonytoolbox.example.internal/api/auth/login/oidc/callback/`

Callback URL registered with the provider. Must match exactly.

---

#### `OIDC_SCOPES`

**Type**: Space-delimited string  
**Required**: No  
**Default**: `openid profile email`  
**Example**: `openid profile email`

Scopes requested during the login flow.

---

#### `OIDC_EMAIL_CLAIM`

**Type**: String  
**Required**: No  
**Default**: `email`  
**Example**: `email`

Primary claim name used to extract the canonical user email address from the ID token or userinfo payload.

---

#### `OIDC_USERNAME_CLAIM`

**Type**: String  
**Required**: No  
**Default**: `preferred_username`  
**Example**: `preferred_username`

Primary claim name used to extract the provider username.

---

#### `OIDC_DISPLAY_NAME_CLAIM`

**Type**: String  
**Required**: No  
**Default**: `name`  
**Example**: `name`

Primary claim name used to extract the display name.

**Authentik Example**:

```bash
AUTH_MODE=oidc
EXTERNAL_AUTH_NAME=Authentik Login
OIDC_CLIENT_ID=telephony-toolbox
OIDC_CLIENT_SECRET=change-me
OIDC_METADATA_URL=https://auth.example.internal/application/o/telephony-toolbox/.well-known/openid-configuration
OIDC_REDIRECT_URI=https://telephonytoolbox.example.internal/api/auth/login/oidc/callback/
OIDC_SCOPES=openid profile email
OIDC_EMAIL_CLAIM=email
OIDC_USERNAME_CLAIM=preferred_username
OIDC_DISPLAY_NAME_CLAIM=name
```

---

### LDAP Configuration

Required if `AUTH_MODE=ldap`.

#### `LDAP_SERVER_URI`

**Type**: URL  
**Required**: If `AUTH_MODE=ldap`  
**Default**: None  
**Example**: `ldap://ldap.example.internal:389` or `ldaps://ldap.example.internal:636`

LDAP server URL. Use `ldap://` for unencrypted or `ldaps://` for TLS.

---

#### `LDAP_BIND_DN`

**Type**: Distinguished Name  
**Required**: If `AUTH_MODE=ldap`  
**Default**: None  
**Example**: `cn=ldap-service,cn=users,dc=example,dc=internal`

LDAP service account DN for directory searches. This account must have read permissions.

---

#### `LDAP_BIND_PASSWORD`

**Type**: String  
**Required**: If `AUTH_MODE=ldap`  
**Default**: None  
**Example**: `ServiceAccountPassword123!`

Password for service account.

**Security**: Never commit to repository.

---

#### `LDAP_USER_SEARCH_BASE`

**Type**: Distinguished Name  
**Required**: If `AUTH_MODE=ldap`  
**Default**: None  
**Example**: `cn=users,dc=example,dc=internal`

Base DN for user searches. Application searches this subtree for users.

---

#### `LDAP_USER_EMAIL_ATTRIBUTE`

**Type**: LDAP attribute name  
**Required**: No  
**Default**: `mail`  
**Example**: `userPrincipalName` or `mail`

LDAP attribute containing user email address. Used as canonical user identifier.

---

#### `LDAP_USER_DISPLAY_NAME_ATTRIBUTE`

**Type**: LDAP attribute name  
**Required**: No  
**Default**: `displayName`  
**Example**: `cn` or `displayName`

LDAP attribute containing user display name (human-readable name).

---

#### `LDAP_USER_ENABLED_ATTRIBUTE`

**Type**: LDAP attribute name  
**Required**: No  
**Default**: None (no checking)  
**Example**: `userAccountControl` or `accountStatus`

Optional LDAP attribute indicating whether user is enabled/active. If set, application checks this attribute.

**If empty**: All LDAP users are considered enabled; no account status checking.

**Common Values**:
- Active Directory: `userAccountControl` (check if value & 0x0002 == 0, i.e., account not disabled)
- OpenLDAP: `accountStatus` (check if value is `active`)

---

#### `LDAP_GROUP_SEARCH_FILTER`

**Type**: LDAP filter string with `%email` placeholder  
**Required**: No  
**Default**: None (no group filtering)  
**Example**: `(&(mail=%email)(memberOf=cn=TelephonyToolbox,ou=Groups,dc=example,dc=internal))`

Optional LDAP search filter for group membership validation. If set, only users matching this filter are allowed to log in.

**Placeholder**: `%email` is replaced with the user's escaped email address (e.g., `user@example.com`).

**Common Patterns**:

```ldap
# Simple email match (no group checking)
(mail=%email)

# Email AND membership in group
(&(mail=%email)(memberOf=cn=TelephonyToolboxUsers,ou=Groups,dc=example,dc=com))

# Email OR membership in multiple groups
(|(mail=%email)(uid=%email))

# Complex: Email AND (group1 OR group2)
(&(mail=%email)(|(memberOf=cn=Group1,ou=Groups,dc=example,dc=com)(memberOf=cn=Group2,ou=Groups,dc=example,dc=com)))
```

**Security**: The `%email` placeholder is automatically escaped to prevent LDAP injection attacks.

**If empty**: All valid LDAP users are allowed.

---

### CUCM Integration

#### `CUCM_AXL_HOST`

**Type**: Hostname or IP  
**Required**: If managing diversions  
**Default**: None  
**Example**: `cucm.example.internal` or `10.0.1.100`

Cisco UCM AXL API server hostname or IP. Application connects via SOAP/HTTPS.

**If empty**: CUCM features disabled; reads/updates return error.

---

#### `CUCM_AXL_USERNAME`

**Type**: String  
**Required**: If `CUCM_AXL_HOST` is set  
**Default**: None  
**Example**: `axl-api-user`

Username for AXL API authentication. Must be a valid CUCM user account with AXL privileges.

---

#### `CUCM_AXL_PASSWORD`

**Type**: String  
**Required**: If `CUCM_AXL_HOST` is set  
**Default**: None  
**Example**: `AxlApiPassword123!`

Password for AXL API user.

**Security**: Never commit to repository.

---

#### `CUCM_AXL_VERSION`

**Type**: String (CUCM version)  
**Required**: No  
**Default**: `14`  
**Example**: `14` or `10.5`

CUCM version for AXL API compatibility. Determines which WSDL schema to load from `wsdl/` directory.

**Supported Values**:
- `8.0` — CUCM 8.0 (legacy)
- `8.5` — CUCM 8.5
- `9.0` — CUCM 9.0
- `9.1` — CUCM 9.1
- `10.5` — CUCM 10.5 (dev/UAT)
- `14` — CUCM 14 (production)

**Important**: Must match or be compatible with actual CUCM version. Mismatch can cause AXL API failures.

---

#### `CUCM_ROUTE_PARTITION`

**Type**: String (CUCM partition name)  
**Required**: No  
**Default**: `INTERNAL`  
**Example**: `INTERNAL` or `CallCenter`

Default CUCM route partition for directory number searches and updates.

**Usage**: Applied to all diversions unless overridden per-diversion.

**Note**: Partition name must exist in CUCM; invalid partition results in AXL errors.

---

#### `CUCM_AXL_VERIFY_TLS`

**Type**: Boolean (`true`, `false`)  
**Required**: No  
**Default**: `true`  
**Example**: `false`

Enable/disable TLS certificate verification for AXL connections.

**Production**: MUST be `true`. Set to `false` only for development/testing with self-signed certificates.

**⚠️ Security**: Disabling TLS verification exposes man-in-the-middle attacks.

---

### Audit Configuration

#### `AUDIT_RETENTION_DAYS`

**Type**: Integer  
**Required**: No  
**Default**: `90`  
**Example**: `180`

Number of days to retain audit event records. Older events are hard-deleted via background job.

**Compliance**: Set based on internal/regulatory requirements. Common values:
- `90` — Standard business retention (3 months)
- `365` — Full year retention
- `1825` — 5-year retention

**Background Job**: Application does not auto-schedule cleanup; run manually via:
```bash
python backend/manage.py delete_expired_audit_events
```

---

## Environment File Example

```bash
# Core Django
DJANGO_SECRET_KEY=your-super-secret-key-12345
DJANGO_ALLOWED_HOSTS=telephonytoolbox.example.internal,localhost
DJANGO_DEBUG=false
DJANGO_LOG_FILE=/var/log/telephonytoolbox/application.log
DJANGO_LOG_LEVEL=INFO
CSRF_TRUSTED_ORIGINS=https://telephonytoolbox.example.internal

# Database
DATABASE_HOST=db.example.internal
DATABASE_PORT=5432
DATABASE_NAME=telephonytoolbox
DATABASE_USER=telephonytoolbox
DATABASE_PASSWORD=SecurePassword123!

# Authentication
AUTH_MODE=entra
LOCAL_AUTH_ENABLED=true

# Entra
ENTRA_CLIENT_ID=12345678-1234-1234-1234-123456789012
ENTRA_CLIENT_SECRET=abc123_DEF456-ghi789~XYZ
ENTRA_TENANT_ID=12345678-1234-1234-1234-123456789012
ENTRA_REDIRECT_URI=https://telephonytoolbox.example.internal/api/auth/login/entra/callback/

# CUCM
CUCM_AXL_HOST=cucm.example.internal
CUCM_AXL_USERNAME=axl-api-user
CUCM_AXL_PASSWORD=AxlApiPassword123!
CUCM_AXL_VERSION=14
CUCM_ROUTE_PARTITION=INTERNAL
CUCM_AXL_VERIFY_TLS=true

# Audit
AUDIT_RETENTION_DAYS=90
```

---

## Configuration Validation

### Startup Checks

Backend performs configuration validation on startup:

1. **Django settings**: SECRET_KEY, ALLOWED_HOSTS, DEBUG
2. **Database**: Connection test (if PostgreSQL configured)
3. **Authentication**: Entra/LDAP configuration check
4. **CUCM**: Optional (warns if not configured, doesn't block startup)

### Common Issues

#### Database connection error
```
Error: could not connect to server: Connection refused
```

**Cause**: PostgreSQL not running or wrong host/port.  
**Fix**: Verify PostgreSQL is running; check `DATABASE_HOST`, `DATABASE_PORT`.

#### Invalid DJANGO_SECRET_KEY
```
Error: SECRET_KEY is too short
```

**Cause**: Secret key < 50 characters or missing.  
**Fix**: Generate new key via `get_random_secret_key()`.

#### CSRF token mismatch
```
Error: Forbidden (403)
CSRF verification failed. Request aborted.
```

**Cause**: Frontend and backend on different domains/ports; `CSRF_TRUSTED_ORIGINS` not configured.  
**Fix**: Add frontend URL to `CSRF_TRUSTED_ORIGINS`.

#### CUCM AXL connection fails
```
Error: Could not connect to CUCM AXL server
```

**Cause**: Wrong host/port, credentials invalid, TLS certificate issue.  
**Fix**: Verify `CUCM_AXL_HOST`, credentials; try setting `CUCM_AXL_VERIFY_TLS=false` for testing.

---

## Configuration for Different Environments

### Local Development

```bash
DJANGO_SECRET_KEY=dev-secret
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_DEBUG=true
DJANGO_LOG_LEVEL=DEBUG

DATABASE_NAME=  # Use SQLite
AUTH_MODE=entra
LOCAL_AUTH_ENABLED=true

# Leave ENTRA_* and LDAP_* empty; use local login
ENTRA_CLIENT_ID=
ENTRA_CLIENT_SECRET=
ENTRA_TENANT_ID=
ENTRA_REDIRECT_URI=

# Leave CUCM empty or configure for test CUCM if available
CUCM_AXL_HOST=
```

### Staging (with PostgreSQL + Entra)

```bash
DJANGO_SECRET_KEY=$(python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
DJANGO_ALLOWED_HOSTS=staging-telephonytoolbox.example.internal
DJANGO_DEBUG=false
DJANGO_LOG_FILE=/var/log/telephonytoolbox/application.log
DJANGO_LOG_LEVEL=INFO

DATABASE_HOST=postgres.staging.internal
DATABASE_PORT=5432
DATABASE_NAME=telephonytoolbox
DATABASE_USER=telephonytoolbox
DATABASE_PASSWORD=StagingPassword123!

AUTH_MODE=entra
LOCAL_AUTH_ENABLED=true

ENTRA_CLIENT_ID=staging-client-id-uuid
ENTRA_CLIENT_SECRET=staging-client-secret
ENTRA_TENANT_ID=tenant-uuid
ENTRA_REDIRECT_URI=https://staging-telephonytoolbox.example.internal/api/auth/login/entra/callback/

CUCM_AXL_HOST=cucm-staging.example.internal
CUCM_AXL_USERNAME=axl-user
CUCM_AXL_PASSWORD=StagingAxlPassword123!
CUCM_AXL_VERSION=14
```

### Production (with PostgreSQL + LDAP)

```bash
DJANGO_SECRET_KEY=$(python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
DJANGO_ALLOWED_HOSTS=telephonytoolbox.example.internal
DJANGO_DEBUG=false
DJANGO_LOG_FILE=/var/log/telephonytoolbox/application.log
DJANGO_LOG_LEVEL=INFO
CSRF_TRUSTED_ORIGINS=https://telephonytoolbox.example.internal

DATABASE_HOST=postgres.prod.internal
DATABASE_PORT=5432
DATABASE_NAME=telephonytoolbox
DATABASE_USER=telephonytoolbox
DATABASE_PASSWORD=ProductionPassword123!

AUTH_MODE=ldap
LOCAL_AUTH_ENABLED=true

LDAP_SERVER_URI=ldaps://ldap.example.internal:636
LDAP_BIND_DN=cn=ldap-service,cn=users,dc=example,dc=internal
LDAP_BIND_PASSWORD=LdapServicePassword123!
LDAP_USER_SEARCH_BASE=cn=users,dc=example,dc=internal
LDAP_USER_EMAIL_ATTRIBUTE=mail
LDAP_USER_DISPLAY_NAME_ATTRIBUTE=displayName
LDAP_USER_ENABLED_ATTRIBUTE=
LDAP_GROUP_SEARCH_FILTER=(&(mail=%email)(memberOf=cn=TelephonyToolboxUsers,ou=Groups,dc=example,dc=internal))

CUCM_AXL_HOST=cucm.example.internal
CUCM_AXL_USERNAME=axl-user
CUCM_AXL_PASSWORD=ProductionAxlPassword123!
CUCM_AXL_VERSION=14
CUCM_ROUTE_PARTITION=INTERNAL
CUCM_AXL_VERIFY_TLS=true

AUDIT_RETENTION_DAYS=90
```

---

## Secrets Management

**Never commit sensitive variables** (passwords, API secrets, tokens) to version control.

### Development

Use `.env` file in repository root (excluded from git via `.gitignore`).

### Production

Recommended approaches:

1. **Environment-specific `.env` file**:
   ```bash
   # /etc/telephonytoolbox/backend.env
   DJANGO_SECRET_KEY=production-secret-key-here
   DATABASE_PASSWORD=production-db-password
   # ... etc
   ```
   Symlink to repo: `ln -s /etc/telephonytoolbox/backend.env /opt/telephonytoolbox/.env`

2. **Secrets management system** (HashiCorp Vault, AWS Secrets Manager, etc.):
   Write a wrapper script to load secrets before starting Gunicorn.

3. **Container environment** (if containerized):
   Pass secrets as environment variables to container at runtime.

**Principle**: Secrets never hardcoded in application; loaded at runtime from external source.

---

## Reloading Configuration

After changing `.env`:

1. **Development**: Restart Django dev server (`Ctrl+C` → re-run)
2. **Production**: Restart Gunicorn service:
   ```bash
   sudo systemctl restart telephonytoolbox
   ```

**Note**: Not all settings can be changed without restart. Database connection details require restart; some logging settings take effect immediately.
