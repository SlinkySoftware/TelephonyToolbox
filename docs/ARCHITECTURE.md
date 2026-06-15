# Telephony Toolbox Architecture

This document describes the system design, data flow, and interactions between components in Telephony Toolbox.

## High-Level Overview

Telephony Toolbox is a two-tier web application:

- **Frontend** (Quasar/Vue 3): Single-Page Application serving user interface
- **Backend** (Django REST Framework): HTTP API server managing business logic, data persistence, and CUCM integration

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Browser                             │
├─────────────────────────────────────────────────────────────────┤
│                   Quasar Vue 3 SPA                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ Auth Pages   │  │ Diversions   │  │ Admin Views  │           │
│  │ (Login)      │  │ (My Updates)  │  │ (User/Group │           │
│  │              │  │              │  │  Management) │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
│         ↓                ↓                   ↓                    │
│  ┌────────────────────────────────────────────────────┐         │
│  │        Pinia State Management + Services           │         │
│  │   (Session, API client, caching, validation)       │         │
│  └────────────────────────────────────────────────────┘         │
└─────────────────────┬──────────────────────────────────────────┘
                      │
                      │ HTTPS + CSRF Token
                      │ Session Cookie
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Django Backend (port 8000)                   │
├─────────────────────────────────────────────────────────────────┤
│
│  REST Framework Layer
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ accounts/   diversions/   access_groups/   audit/        │  │
│  │ URLs, Views, Serializers, Permissions                    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          ↓                                       │
│  Service Layer                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Authentication Services │ Diversion Services │ Audit     │  │
│  │ (Entra, LDAP, Local)    │ (Update, Refresh)   │ Services │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          ↓                                       │
│  Business Logic & Validation                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Destination Validation (E.164, Australian formats)       │  │
│  │ Permission Checks (Group membership, roles)              │  │
│  │ Audit Event Recording (before/after state)               │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          ↓                                       │
│  Data Access Layer                                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Models (User, Diversion, AuditEvent, AccessGroup, etc)  │  │
│  │ ORM Queries, Database Transactions                        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          ↓                                       │
│  External Integrations                                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ CUCM Client (Zeep SOAP)  │  LDAP 3  │  Entra OAuth 2.0  │  │
│  │ (Read/Update Directory   │ (Auth)   │ (OIDC)            │  │
│  │  Numbers, Check Health)  │          │                    │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
        │                          │                    │
        │                          │                    │
        ↓                          ↓                    ↓
    ┌────────────┐         ┌─────────────┐       ┌──────────┐
    │ PostgreSQL │         │ CUCM 8–14   │       │ LDAP/    │
    │ (or SQLite)│         │ (AXL API)   │       │ Entra    │
    │            │         │             │       │          │
    │ Users      │         │ Directory   │       │ Identities
    │ Diversions │         │ Numbers     │       │          │
    │ Audit Logs │         │ CFA Config  │       └──────────┘
    │ Groups     │         └─────────────┘
    └────────────┘
```

## Core Components

### 1. Frontend (Quasar Vue 3 SPA)

**Purpose**: Provide responsive user interface for viewing and managing diversions, authentication, and administration.

**Key Pages**:

- `AuthLoginPage.vue`: Authentication entry point (Entra, LDAP, or local)
- `MyDiversionsPage.vue`: Standard user dashboard showing assigned diversions
- `EditDiversionPage.vue`: Diversion destination editor with real-time validation
- `AdminDashboardPage.vue`: App Admin overview
- `AdminUsersPage.vue`: User management (create, delete, change roles)
- `AdminGroupsPage.vue`: Group creation and membership management
- `AdminDiversionsPage.vue`: Diversion CRUD (create, link to groups)
- `AdminAuditPage.vue`: Audit log viewing and CSV export
- `AdminHealthPage.vue`: System health and connectivity status

**State Management** (Pinia):

- `sessionStore`: Current user, authentication status, role-based visibility
- `diversionsStore`: Cached diversion list, selected diversion detail, destination validation state
- `auditStore`: Audit log queries and filters

**API Communication**:

- Session-based authentication via CSRF-protected REST calls
- Automatic redirect to login if session expires
- Real-time destination validation feedback
- Progress indicators and error messages

### 2. Backend: Authentication & Authorization

#### Django User Model (`accounts.models.User`)

Custom user model with email as canonical identifier:

```python
class User(UUIDTimestampedModel, AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)  # Canonical identifier
    display_name = models.CharField(max_length=255)
    auth_source = models.CharField(choices=AuthSource.choices)  # entra, ldap, or local
    role = models.CharField(choices=UserRole.choices)  # standard_user or app_admin
    is_active = models.BooleanField()  # Soft disable
    is_local = models.BooleanField()  # Created via local auth or admin
```

#### Authentication Flow

1. **Login Request** → `AuthOptionsView` returns `auth_mode` and `local_auth_enabled`
2. **Local Auth**: Credentials verified against User model; Django session created
3. **LDAP Auth**: Credentials validated against LDAP; user synced or created; Django session created
4. **Entra Auth**: Redirect to Entra OAuth authorize endpoint → callback → ID token validated → user synced/created
5. **Session Persistence**: Django session cookie (HttpOnly, Secure, SameSite=Strict in production)

#### Authorization Tiers

| Level | Decision | Implementation |
|-------|----------|-----------------|
| **Authentication** | Is user logged in? | Django session middleware |
| **Role-Based** | Is user App Admin? | `IsAppAdmin` permission class on admin views |
| **Group-Based** | Can user see this diversion? | `visible_diversions_queryset()` filtering by user group memberships |
| **Operation** | Can user update destinations? | CUCM availability check + `IsAppAdmin` for admin operations |

#### Permission Hierarchy

- **Guest** → `/login` page only
- **Standard User** → View diversions in assigned groups; update CFA destinations (if CUCM available)
- **App Admin** → All of Standard User + User management + Group management + Diversion admin + Audit export

### 3. Backend: Data Models

#### `diversions.models.Diversion`

Represents a Call Forward All diversion:

```python
class Diversion(UUIDTimestampedModel):
    name = models.CharField()                          # Human-readable name
    description = models.TextField()                   # Context
    source_number = models.CharField(unique=True)      # Globally unique
    source_partition = models.CharField()              # CUCM partition (default: INTERNAL)
    cached_current_destination = models.CharField()    # Last known CFA destination
    group = models.ForeignKey(AccessGroup)             # Which group manages this diversion
    last_refreshed_at = models.DateTimeField()         # When last synced from CUCM
    last_updated_at = models.DateTimeField()           # When CFA was last modified
    last_updated_by_text = models.CharField()          # User email (text, not FK)
    created_by_text = models.CharField()               # Creator email (audit trail)
```

**Key Properties**:

- `source_number` is immutable after creation (validated in `clean()`)
- Cached state is read-only from user perspective; reflects live CUCM state
- Audit trail via text fields enables hard delete of users without losing history

#### `access_groups.models.AccessGroup` & `UserGroupMembership`

Group-based access control:

```python
class AccessGroup(UUIDTimestampedModel):
    name = models.CharField(unique=True)
    description = models.TextField()

class UserGroupMembership(UUIDModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    group = models.ForeignKey(AccessGroup, on_delete=models.CASCADE)
    # Unique constraint on (user, group) pair
```

**Access Rules**:

- Standard users see only diversions belonging to their group memberships
- App Admins see all diversions
- Groups are local only; users can belong to multiple groups

#### `audit.models.AuditEvent`

Immutable event log for compliance:

```python
class AuditEvent(UUIDModel):
    timestamp = models.DateTimeField(auto_now_add=True)
    event_type = models.CharField()                    # e.g., 'diversion.update.success'
    result = models.CharField(choices=AuditResult.choices)  # success, failure, warning
    actor_user_id_text = models.CharField()            # Text snapshot of user UUID
    actor_email = models.CharField()                   # Text snapshot of email
    actor_display_name = models.CharField()            # Text snapshot of display name
    actor_auth_source = models.CharField()             # Text snapshot of auth source
    object_type = models.CharField()                   # 'diversion', 'user', etc.
    object_id_text = models.CharField()                # Text snapshot of object UUID
    object_name = models.CharField()                   # Human-readable object name
    source_number = models.CharField()                 # Diversion source (if applicable)
    destination_number = models.CharField()            # CFA destination (if applicable)
    message = models.TextField()                       # Event summary
    metadata_json = models.JSONField()                 # Extended context (CUCM response, etc.)
```

**Retention**: 90 days (configurable via `AUDIT_RETENTION_DAYS`). Older records are hard-deleted via scheduled cleanup.

### 4. Backend: Validation & Diversion Update Flow

#### Destination Validation (`dialplan.validators`)

Validates and normalizes destination numbers to Australian +E.164 format:

```
Input Examples:
  "02 9999 8888"          → +61299998888 (FNN)
  "0412 345 678"          → +61412345678 (Mobile)
  "(02) 9999-8888"        → +61299998888 (FNN with formatting)
  "+61299998888"          → +61299998888 (Already E.164)

Rejected:
  "1234"                  → Error: Internal extension not allowed
  "0011 1 202 555 5555"   → Error: International numbers not permitted
  "sip:user@example.com"  → Error: SIP URIs not permitted
  ""                      → Error: Destination required
  "blah"                  → Error: Unsupported dial string
```

**Implementation**: `validate_and_normalise_destination(raw_input: str) → NormalisedDestination`

Returns:
- `is_valid: bool`
- `normalised_e164: str | None` — Validated +61XXX format
- `destination_type: str` — "fnn" or "mobile"
- `error_code: str | None` — Machine-readable error identifier
- `error_message: str` — User-facing error text

#### Diversion Update Flow

```
User submits: { destination: "02 9999 8888" }
                            ↓
                  Validate input (E.164)
                            ↓
          Normalise to: +61299998888
                            ↓
              AXL updateLine() call via CUCM
                            ↓
           Read back current state from CUCM
                            ↓
              Verify returned state matches
          what we just wrote (revalidation)
                            ↓
          Success: Update local cache + audit
          OR Failure: Rollback + audit + error message
```

**Key Design Decisions**:

1. **Write-then-read**: After updating CUCM, immediately read back and verify. Protects against silent failures.
2. **Graceful degradation**: If CUCM unavailable, edits blocked but cached state still visible.
3. **Audit on write**: Every diversion update logged with actor, before/after state, CUCM response.
4. **No approval workflow**: Write directly to CUCM (per MVP scope); audit trail provides accountability.

### 5. Backend: CUCM Integration

#### CUCM Client Architecture

Abstract factory pattern with version-specific implementations:

```python
class CucmClient(ABC):
    def get_directory_number(pattern: str, partition: str) → CucmDirectoryNumber
    def update_call_forward_all(pattern: str, partition: str, destination: str) → CucmUpdateResult
    def health_check() → CucmHealthResult
```

**Implementations**:

- `client_zeep.py` — Main implementation using Zeep SOAP client (recommended)
- `client_14.py` — CUCM 14-specific optimizations
- `client_105.py` — Legacy CUCM 10.5 compatibility
- `client.py` — Router determining which to instantiate based on `CUCM_AXL_VERSION`

**Schema Management**:

Versioned WSDL files in `wsdl/` directory:
- `wsdl/8.0/AXLAPI.wsdl` (and associated XSD)
- `wsdl/9.0/AXLAPI.wsdl`
- `wsdl/9.1/AXLAPI.wsdl`
- etc. through `14/`

Each version's types are loaded dynamically; allows same code to work across CUCM versions.

#### CUCM Directory Number Handling

**Challenge**: CUCM directory number patterns with leading `+` (for E.164 pattern matching) must be:

- Escaped as `\+...` when passed to AXL as pattern
- Stored internally in app as `+...` (unescaped)
- Returned to frontend as `+...` (for display)

**Implementation**:

- `cucm/directory_numbers.py` provides:
  - `normalise_directory_number_pattern()` — Standardize input (strip whitespace, handle escaping)
  - `directory_number_pattern_variants()` — Generate escaped and unescaped variants for lookup
- AXL client automatically escapes patterns internally

#### CUCM Health Check

Periodic health checks determine if updates are allowed:

```
GET /api/health/           → { status: "ok" }  (always accessible)
GET /api/admin/health/     → { cucm_status: "available|unavailable", ... }
```

When CUCM unavailable:
- Frontend shows "Unavailable" badge
- Read operations still work (serve cached data)
- Update/refresh operations return 503 Service Unavailable
- Audit event logged as warning

### 6. Backend: API Endpoints

See [API_SPECIFICATION.md](API_SPECIFICATION.md) for complete endpoint documentation. Summary:

#### Authentication

- `GET /api/auth/options/` — Return `auth_mode` and `local_auth_enabled`
- `POST /api/auth/login/local/` — Local credential login
- `POST /api/auth/login/ldap/` — LDAP credential login
- `GET /api/auth/login/entra/` — Entra OAuth redirect
- `GET /api/auth/login/entra/callback/` — Entra callback handler
- `GET /api/auth/me/` — Current user info
- `POST /api/auth/logout/` — Destroy session

#### Diversions (Standard User)

- `GET /api/diversions/` — List visible diversions
- `GET /api/diversions/<id>/` — Detail view
- `POST /api/diversions/<id>/validate-destination/` — Validate input (no write)
- `POST /api/diversions/<id>/update-destination/` — Update CFA destination
- `POST /api/diversions/<id>/refresh/` — Sync cached state from CUCM

#### Administration

- `GET /api/admin/users/` — List all users
- `POST /api/admin/users/` — Create user
- `GET /api/admin/users/<id>/` — User detail
- `PATCH /api/admin/users/<id>/` — Update user (role, active status)
- `DELETE /api/admin/users/<id>/` — Hard delete user
- Similar for groups: `GET /api/admin/groups/`, `POST`, `GET <id>`, `PATCH`, `DELETE`
- Diversions: `GET /api/admin/diversions/`, `POST`, `GET <id>`, `PATCH`, `DELETE`
- Audit: `GET /api/admin/audit/`, `GET /api/admin/audit/export.csv`

### 7. Deployment Architecture

#### Development (Local)

```
Quasar dev server (port 9000)
  ↓ (proxies /api)
Django dev server (port 8000)
  ↓
SQLite database (db.sqlite3)
  ↓
CUCM (if configured)
```

#### Production (RHEL 9 bare-metal)

```
Client Browser (HTTPS)
  ↓
nginx (port 443)
  ├─ /static/*       → /var/www/telephonytoolbox/dist/spa/ (SPA files)
  └─ /api/*          → proxy_pass 127.0.0.1:8010 (Gunicorn)
        ↓
Gunicorn (127.0.0.1:8010, 4 workers)
  ↓
Django WSGI app
  ├─ Session store   → PostgreSQL
  ├─ Models, Audit   → PostgreSQL
  └─ External calls  → CUCM AXL, LDAP, Entra
        ↓
PostgreSQL (TCP 5432, local or remote)
```

**Key Files**:

- Application root: `/opt/telephonytoolbox`
- App user: `telephonytoolbox` (no login shell)
- Environment: `/etc/telephonytoolbox/backend.env` (symlinked to repo `.env`)
- Gunicorn socket: `/run/telephonytoolbox/gunicorn.sock` (managed by systemd)
- Logs: `/var/log/telephonytoolbox/`
- Systemd service: `/etc/systemd/system/telephonytoolbox.service`
- nginx site config: `/etc/nginx/sites-available/telephonytoolbox.conf`

**SELinux Policies** (if enabled):

- App directory: `chcon -R -t usr_t /opt/telephonytoolbox`
- Quasar SPA output: `chcon -R -t httpd_sys_content_t /opt/telephonytoolbox/frontend/dist/spa`
- nginx log directory: `chcon -R -t httpd_log_t /var/log/telephonytoolbox`
- Allow Gunicorn proxy: `setsebool httpd_can_network_connect on`

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete production setup.

## Data Flow Diagrams

### Diversion Update Sequence

```
Standard User
    │
    ├─→ GET /api/diversions/                    (list assigned)
    │   ←─ [Diversion, Diversion, ...]
    │
    ├─→ POST /api/diversions/<id>/validate-destination/
    │   (request: { "destination": "02 9999 8888" })
    │   ┌─────────────────────────────────────────────────┐
    │   │ Backend:                                         │
    │   │ - Validate & normalise → +61299998888          │
    │   │ - Return validation result (no DB change)       │
    │   └─────────────────────────────────────────────────┘
    │   ←─ { "is_valid": true, "normalised_destination": "+61299998888", ... }
    │
    ├─→ POST /api/diversions/<id>/update-destination/
    │   (request: { "destination": "+61299998888" })
    │   ┌─────────────────────────────────────────────────┐
    │   │ Backend:                                         │
    │   │ 1. Check permission (user in diversion's group) │
    │   │ 2. Check CUCM health                            │
    │   │ 3. Validate destination (re-check)              │
    │   │ 4. Call CUCM updateLine(pattern, ...partition, │
    │   │    callForwardAll=+61299998888)                 │
    │   │ 5. Read back current state from CUCM            │
    │   │ 6. Verify returned destination matches          │
    │   │ 7. Update local cache                           │
    │   │ 8. Record audit event (success)                 │
    │   │ 9. Return updated Diversion object              │
    │   └─────────────────────────────────────────────────┘
    │   ←─ { "diversion": {..., "cached_current_destination": "+61299998888", ...}, "cucm_status": "available" }
    │
    └─→ Diversion list updated, user sees change
```

### User Provisioning (Entra OIDC)

```
User at browser
  │
  ├─→ GET /login
  │   ←─ AuthLoginPage
  │
  ├─→ GET /api/auth/options/
  │   ←─ { "auth_mode": "entra", "local_auth_enabled": false }
  │
  ├─→ GET /api/auth/login/entra/
  │   ├─ Backend generates OAuth state + nonce
  │   ├─ Redirects to Entra authorize endpoint
  │   ├─→ https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize?...
  │   │   ↓
  │   │   (User logs into Entra)
  │   │   ↓
  │   │   Entra redirects back to callback
  │
  └─→ GET /api/auth/login/entra/callback/?code=...&state=...
      ┌────────────────────────────────────────────────────────┐
      │ Backend:                                               │
      │ 1. Exchange code for ID token (via Entra token URL)   │
      │ 2. Validate token signature + claims                  │
      │ 3. Extract email from token                           │
      │ 4. Check if user exists in DB                         │
      │ 5. If not: create user (auth_source=entra, role=standard_user) │
      │ 6. If yes: sync display_name and active status        │
      │ 7. Create Django session                              │
      │ 8. Redirect to /diversions or /admin                  │
      └────────────────────────────────────────────────────────┘
      ←─ Redirect: 302 /diversions
```

## Security Considerations

### Authentication & Sessions

- **Session hijacking**: HttpOnly + Secure + SameSite=Strict cookies (production)
- **CSRF**: Django middleware + CSRF token in form data and headers
- **Password storage**: Django PBKDF2 hashing for local users
- **External auth**: Token validation and signature verification; no secrets in URL

### Authorization

- **Permission checks** on every protected endpoint
- **Group membership** verified at query time (not cached)
- **Role hierarchy** enforced: App Admin > Standard User

### Data Protection

- **Audit immutability**: Text fields instead of FKs prevent audit tampering via cascade deletes
- **User hard delete**: Audit events preserve actor details as snapshots
- **Sensitive data**: Passwords, API credentials in environment (not DB)
- **CUCM credentials**: Stored in environment; never logged or returned to frontend

### External Integrations

- **CUCM TLS**: Configurable TLS verification (`CUCM_AXL_VERIFY_TLS`)
- **LDAP**: Bind via service account; LDAP injection prevention (filter escaping)
- **Entra**: OAuth 2.0 PKCE flow; token validation; state/nonce checks

## Performance & Scalability

### Caching Strategy

- **Diversion state**: Cached in DB (`cached_current_destination`); updates via CUCM write-then-read
- **User groups**: Loaded at request time; no explicit cache (Django ORM handles DB connection pooling)
- **Session store**: Default Django session backend (DB-backed)

### Database Indexing

- Primary keys: UUIDs (indexed automatically)
- Unique constraints: `source_number` on Diversion, `email` on User, `(user, group)` on memberships
- Audit queries: Indexed on `timestamp` for log queries

### Horizontal Scaling

- **Stateless backend**: Session state in DB (can be shared across multiple Gunicorn instances)
- **Load balancer**: Distribute across multiple Gunicorn processes (sticky sessions not required)
- **CUCM client**: Thread-safe; connection pooling via Zeep

## Error Handling & Observability

### Logging

- **Application logs**: Django logger `telephony_toolbox.api` captures request/response/exceptions
- **Audit logs**: AuditEvent model tracks all user actions
- **Log levels**: Configurable via `DJANGO_LOG_LEVEL` (INFO, DEBUG, WARNING, ERROR)
- **Log destination**: File (`DJANGO_LOG_FILE`) or console

### Exception Handling

- **API exceptions**: Custom `api_exception_handler` logs warnings + returns structured responses
- **CUCM unavailable**: Caught, logged, returned as 503 Service Unavailable
- **Auth failures**: Logged as audit event with actor email (for security review)
- **Validation failures**: Returned as 400 Bad Request with error_code for frontend handling

## Future Extensibility

The codebase is designed to support future features without major refactoring:

- **Approval workflow**: Add `DiversionChangeRequest` model; extend update views to create requests instead of direct updates
- **Bulk operations**: Add bulk endpoint; iterate across diversions with transaction rollback
- **Additional phone number types**: Extend `dialplan/validators.py` with new validation rules
- **Multi-cluster CUCM**: Add cluster selector to Diversion model; route CUCM calls via cluster-specific client
- **Notification integration**: Extend AuditService to emit events; implement notification handlers (Teams, email, etc.)

All changes can be made via new app modules without modifying core authentication or CUCM integration.
