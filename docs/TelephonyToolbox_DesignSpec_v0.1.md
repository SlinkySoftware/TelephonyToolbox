# Telephony Toolbox — Build-Ready Design Specification v0.1

**Document version:** v0.1  
**Application name:** Telephony Toolbox  
**Purpose:** Replacement for the diversion-management function in CCToolbox as Genesys is decommissioned  
**Frontend:** Quasar Framework  
**Backend:** Django + Django REST Framework  
**Deployment target:** Bare-metal RHEL 9, nginx, gunicorn, PostgreSQL  
**Primary integration:** Cisco UCM AXL API  
**CUCM versions:** Dev/UAT CUCM 10.5, Production CUCM 14  

---

## 1. Executive summary

Telephony Toolbox is an internal web application that allows authorised business operations users to update pre-defined telephony diversion destinations. Each diversion corresponds to a globally unique Cisco UCM Directory Number and is managed by updating the **Call Forward All** destination via the Cisco UCM AXL API.

The application replaces a subset of CCToolbox functionality previously used to control Genesys-related diversion behaviour. The new application does not control Genesys. Cisco UCM is the source of truth for live diversion state.

The MVP is intentionally single-purpose: manage diversion destinations only. It should be designed cleanly enough to allow future expansion, but no generic telephony platform or plugin framework is required for v0.1.

---

## 2. Design goals

### 2.1 Primary goals

- Allow authorised users to update diversion destinations safely.
- Use Cisco UCM as the authoritative source of diversion state.
- Validate and normalise destination numbers before writing to CUCM.
- Provide clear role-based access control using local application groups.
- Support Entra SSO or LDAP authentication, plus local fallback users.
- Provide a complete custom admin interface without using Django Admin.
- Provide audit visibility for operational and compliance purposes.
- Deploy cleanly on existing RHEL 9 infrastructure using nginx, gunicorn and PostgreSQL.

### 2.2 Non-goals for v0.1

The following are explicitly out of scope for MVP:

- Genesys integration.
- Approval workflow.
- Change-ticket enforcement.
- ServiceNow integration.
- Teams/email notifications.
- Bulk updates.
- Scheduled reconciliation.
- Multi-cluster CUCM support.
- User-managed dial plan rules.
- Django Admin usage.
- JWT-based frontend authentication.
- Clearing/removing CUCM Call Forward All values.
- Managing call-forward busy, no-answer, hunt pilots, CTI route points, route patterns or translation patterns.

---

## 3. System architecture

### 3.1 Logical architecture

```text
User Browser
  |
  | HTTPS
  v
nginx virtual host
  |
  |-- /                 -> Quasar static frontend
  |-- /assets/          -> Quasar static assets
  |-- /api/             -> proxy_pass to Django/gunicorn
  |-- /api/healthz      -> Django lightweight health endpoint
  |
  v
gunicorn
  |
  v
Django + Django REST Framework
  |
  |-- PostgreSQL
  |-- Cisco UCM AXL
  |-- Entra or LDAP, depending on AUTH_MODE
```

### 3.2 Runtime components

| Component | Responsibility |
|---|---|
| Quasar frontend | User and admin interface |
| nginx | TLS termination, static file serving, reverse proxy |
| gunicorn | Django application server |
| Django API | Business logic, auth/session, validation, AXL integration |
| PostgreSQL | Users, groups, diversion metadata, cache, audit records |
| CUCM AXL | Live source of truth for diversion destination |
| Entra or LDAP | External user validation/authentication |
| Local auth | Fallback authentication and super admin access |

---

## 4. Deployment model

### 4.1 Target platform

- Bare-metal RHEL 9.
- Existing host infrastructure.
- Existing PostgreSQL service/platform.
- New PostgreSQL database for Telephony Toolbox.
- New nginx virtual host.
- Quasar built as static files.
- Django served by gunicorn.
- nginx uses `proxy_pass` for `/api/`.

### 4.2 Recommended filesystem layout

```text
/opt/telephonytoolbox/
  backend/
    manage.py
    telephony_toolbox/
    accounts/
    access_groups/
    diversions/
    dialplan/
    cucm/
    audit/
    health/
  frontend/
    dist/
  .venv/
  logs/
```

### 4.3 Process model

- `telephonytoolbox-gunicorn.service` managed by systemd.
- nginx serves Quasar static files.
- nginx proxies API traffic to gunicorn via localhost TCP or Unix socket.
- Audit retention cleanup executed by cron or systemd timer using a Django management command.

---

## 5. Environment configuration

All secrets and environment-specific values must be externalised. No secrets are to be committed to source control or stored in the database.

### 5.1 Required environment variables

```text
DJANGO_SECRET_KEY=
DJANGO_ALLOWED_HOSTS=
DJANGO_DEBUG=false

DATABASE_HOST=
DATABASE_PORT=5432
DATABASE_NAME=
DATABASE_USER=
DATABASE_PASSWORD=

AUTH_MODE=entra
# Valid values:
# entra
# ldap

LOCAL_AUTH_ENABLED=true

CUCM_AXL_HOST=
CUCM_AXL_USERNAME=
CUCM_AXL_PASSWORD=
CUCM_AXL_VERSION=14
# Valid values:
# 10.5
# 14

CUCM_ROUTE_PARTITION=INTERNAL

AUDIT_RETENTION_DAYS=90
```

### 5.2 Entra-specific variables

Required only when `AUTH_MODE=entra`.

```text
ENTRA_CLIENT_ID=
ENTRA_CLIENT_SECRET=
ENTRA_TENANT_ID=
ENTRA_REDIRECT_URI=
```

### 5.3 LDAP-specific variables

Required only when `AUTH_MODE=ldap`.

```text
LDAP_SERVER_URI=
LDAP_BIND_DN=
LDAP_BIND_PASSWORD=
LDAP_USER_SEARCH_BASE=
LDAP_USER_EMAIL_ATTRIBUTE=mail
LDAP_USER_DISPLAY_NAME_ATTRIBUTE=displayName
LDAP_USER_ENABLED_ATTRIBUTE=
LDAP_GROUP_SEARCH_FILTER=
```

`LDAP_USER_ENABLED_ATTRIBUTE` may be blank if enabled/disabled state is not available or not required.

`LDAP_GROUP_SEARCH_FILTER` is optional. If specified, it restricts login to users matching the filter. Use `%email` as a placeholder for the user's email address (e.g. `(&(mail=%email)(memberOf=CN=TelephonyBoxUsers,OU=Groups,DC=example,DC=com))`). Leave blank to allow any valid LDAP user.

---

## 6. Authentication design

### 6.1 Supported authentication methods

Telephony Toolbox supports:

- Entra SSO.
- LDAP.
- Local fallback accounts.

Only one external provider is active per deployment:

- `AUTH_MODE=entra`, or
- `AUTH_MODE=ldap`.

Local fallback auth is available regardless of external provider mode, provided `LOCAL_AUTH_ENABLED=true`.

### 6.2 Session model

The application uses Django cookie-based sessions with CSRF protection.

All authentication methods establish the same local Django session:

- Entra SSO login creates a Django session.
- LDAP login creates a Django session.
- Local fallback login creates a Django session.

The frontend does not manage JWTs.

### 6.3 Logout

Logout is local only.

Logout destroys the Django session. It does not attempt full Entra, LDAP or browser identity-provider logout.

### 6.4 User provisioning

Users must be pre-provisioned in Telephony Toolbox before they can use the application.

Reason:

- Application access is controlled locally.
- Users must be assigned to one or more local application groups to see diversions.

### 6.5 Primary identifier

Email address is the canonical user identifier.

It is used for:

- login matching
- user records
- audit actor fields
- group membership display
- last updated fields

Email addresses should be normalised consistently, preferably lower-cased and trimmed.

---

## 7. Authorisation design

### 7.1 Roles

There are two application roles:

| Role | Description |
|---|---|
| Standard User | Business operations user who can update assigned diversions |
| App Admin | Telephony administrator who manages users, groups, diversions, audit and health |

Local fallback users may hold App Admin rights. At least one local App Admin must exist for bootstrap and break-glass access.

### 7.2 Standard User permissions

A Standard User can:

- log in
- view diversions assigned to groups they are a member of
- view cached diversion state
- manually refresh visible diversion state
- update diversion destination when CUCM is available
- view success/failure result for their own attempted update

A Standard User cannot:

- create diversions
- delete diversions
- manage groups
- manage users
- view unrelated diversions
- view audit logs
- view system health
- access admin API endpoints

### 7.3 App Admin permissions

An App Admin can:

- manage users
- validate external users
- create local fallback users
- hard delete users
- manage groups
- assign users to groups
- create diversions
- validate source DNs against CUCM
- assign each diversion to one group
- edit diversion metadata
- delete local diversion records
- refresh cached CUCM state
- view all diversions
- view and export audit logs
- view system health

### 7.4 Object access rules

A Standard User may access a diversion if:

- the user is active, and
- the user has role `STANDARD_USER` or `APP_ADMIN`, and
- the diversion is assigned to a group of which the user is a member.

An App Admin may access all diversions.

---

## 8. Data model

The model definitions below are implementation-oriented and suitable for Django ORM design.

### 8.1 User model

Use a custom Django user model from project start.

Suggested model: `accounts.User`

| Field | Type | Notes |
|---|---|---|
| id | UUID or bigint | Primary key |
| email | EmailField, unique | Canonical identifier |
| display_name | CharField | User-friendly name |
| auth_source | CharField | `entra`, `ldap`, `local` |
| role | CharField | `standard_user`, `app_admin` |
| is_active | Boolean | Login allowed |
| is_local | Boolean | True for local fallback user |
| password | Django password hash | Only used for local users |
| last_login | DateTime | Standard Django behaviour |
| created_at | DateTime | Auto |
| updated_at | DateTime | Auto |

Rules:

- Email must be unique.
- Local users must have usable local passwords.
- External users should not require a local password.
- Users are hard deleted when deleted by an App Admin.
- Audit records must not use a foreign key to this model.

### 8.2 Access group model

Suggested model: `access_groups.AccessGroup`

| Field | Type | Notes |
|---|---|---|
| id | UUID or bigint | Primary key |
| name | CharField, unique | Group name |
| description | TextField | Optional |
| created_at | DateTime | Auto |
| updated_at | DateTime | Auto |

Rules:

- Group names must be unique.
- A group may have zero users.
- A group may have zero diversions.
- A group cannot be deleted if any diversion is assigned to it.
- A group can be deleted if it contains users but no diversions.

### 8.3 User group membership

Suggested model: `access_groups.UserGroupMembership`

| Field | Type | Notes |
|---|---|---|
| id | UUID or bigint | Primary key |
| user | FK to User | Cascade delete |
| group | FK to AccessGroup | Cascade delete |
| created_at | DateTime | Auto |

Rules:

- A user can belong to one or more groups.
- Duplicate user/group memberships must be prevented with a unique constraint.

Unique constraint:

```text
unique(user, group)
```

### 8.4 Diversion model

Suggested model: `diversions.Diversion`

| Field | Type | Notes |
|---|---|---|
| id | UUID or bigint | Primary key |
| name | CharField | Human-friendly name |
| description | TextField | Optional |
| source_number | CharField, unique | CUCM Directory Number |
| source_partition | CharField | From `CUCM_ROUTE_PARTITION`, default `INTERNAL` |
| cached_current_destination | CharField | Last known CUCM value |
| group | FK to AccessGroup | One diversion belongs to exactly one group |
| last_refreshed_at | DateTime | Last successful CUCM read |
| last_updated_at | DateTime | Last successful CUCM write |
| last_updated_by_text | CharField | Email/display text, not FK |
| created_at | DateTime | Auto |
| created_by_text | CharField | Admin email/display text |
| updated_at | DateTime | Auto |

Rules:

- `source_number` is immutable after creation.
- `source_number` must be globally unique in Telephony Toolbox.
- `source_number` must exist in CUCM during creation.
- The source partition is configured, not user-entered.
- The route partition is not displayed to standard users.
- Each diversion belongs to exactly one group.
- Deleting a diversion removes only the local record and does not modify CUCM.

### 8.5 Audit event model

Suggested model: `audit.AuditEvent`

| Field | Type | Notes |
|---|---|---|
| id | UUID or bigint | Primary key |
| timestamp | DateTime | Auto |
| event_type | CharField | Structured event key |
| result | CharField | `success`, `failure`, `warning` |
| actor_user_id_text | CharField | Text only |
| actor_email | CharField | Text only |
| actor_display_name | CharField | Text only |
| actor_auth_source | CharField | Text only |
| object_type | CharField | `diversion`, `user`, `group`, `auth`, `system` |
| object_id_text | CharField | Text only |
| object_name | CharField | Text only |
| source_number | CharField | Optional |
| destination_number | CharField | Full destination value where relevant |
| message | TextField | Human-readable summary |
| metadata_json | JSONField | Structured details |

Rules:

- No required FK to User.
- No required FK to Diversion.
- Audit records must remain readable after user hard deletion or diversion deletion.
- Destination numbers are stored in full.
- Retention is 90 days / 3 months.
- App Admins can export audit records to CSV.

---

## 9. Diversion business rules

### 9.1 Source DN rules

- Source DN is always a Cisco UCM Directory Number.
- Source DN is globally unique in CUCM.
- Source DN is globally unique in Telephony Toolbox.
- Source DN always uses configured route partition.
- Route partition is externally configured using `CUCM_ROUTE_PARTITION`.
- Default partition value is `INTERNAL`.
- Route partition is not requested from users.
- Route partition does not need to be displayed to users.

### 9.2 Call forwarding rule

The application manages only:

- Call Forward All destination.

The application must not manage:

- Call Forward Busy.
- Call Forward No Answer.
- Hunt pilot forwarding.
- Translation patterns.
- Route patterns.
- SIP URIs.
- Any Genesys state.

### 9.3 Destination must always exist

The system must reject any destination update that results in:

- blank value
- null value
- whitespace-only value
- clearing Call Forward All

There is no “remove diversion” operation.

### 9.4 Diversion deletion

When an App Admin deletes a diversion:

- delete the local Telephony Toolbox diversion record
- remove its application visibility
- remove its group association
- do not update CUCM
- do not clear CUCM forwarding
- do not validate CUCM state during deletion unless needed for display only
- write an audit record indicating that CUCM was not modified

Admin UI confirmation text should state:

```text
This will remove the diversion from Telephony Toolbox only. CUCM will not be changed.
```

---

## 10. Destination validation and normalisation

### 10.1 Allowed destination types

Allowed:

| Type | Example input | Normalised output |
|---|---|---|
| Australian FNN | `02 9999 1234` | `+61299991234` |
| Australian mobile | `0412 345 678` | `+61412345678` |
| Australian E.164 | `+61299991234` | `+61299991234` |

### 10.2 Blocked destination types

Blocked:

- International numbers.
- Internal extensions.
- SIP URIs.
- Empty values.
- Non-number strings.
- Unsupported dial strings.
- Any value that cannot be normalised to Australian +E.164.

Although CUCM Calling Search Space may also block some destinations, the UI and API must reject invalid destinations before attempting an AXL update.

### 10.3 Normalisation rules

The application should accept friendly formatting characters and strip them before validation:

- spaces
- hyphens
- brackets

Examples:

```text
(02) 9999 1234 -> +61299991234
02-9999-1234   -> +61299991234
0412 345 678   -> +61412345678
+61 2 9999 1234 -> +61299991234
```

### 10.4 Canonical format

The canonical format written to CUCM is Australian +E.164.

Reason:

- CUCM read-back will return +E.164.
- Save confirmation must revalidate the CUCM returned value.
- Comparing expected and actual values is simpler when both are canonical.

### 10.5 Backend validation authority

Frontend validation may provide immediate user feedback, but backend validation is authoritative.

The backend must validate every destination update even if the frontend already validated it.

### 10.6 Suggested backend function

```text
validate_and_normalise_destination(raw_input: str) -> NormalisedDestination
```

Suggested result object:

```text
NormalisedDestination:
  original_input: str
  stripped_input: str
  normalised_e164: str
  destination_type: "fnn" | "mobile"
  is_valid: bool
  error_code: str | None
  error_message: str | None
```

### 10.7 Suggested validation outcomes

| Input | Expected result |
|---|---|
| `02 9999 1234` | valid, `+61299991234` |
| `(02) 9999 1234` | valid, `+61299991234` |
| `0412 345 678` | valid, `+61412345678` |
| `+61299991234` | valid, `+61299991234` |
| `+61412345678` | valid, `+61412345678` |
| `12345` | invalid, internal extension not allowed |
| `001144...` | invalid, international not allowed |
| `+44123456789` | invalid, non-Australian E.164 |
| `sip:user@example.com` | invalid, SIP URI not allowed |
| blank | invalid, destination required |

---

## 11. CUCM AXL integration

### 11.1 CUCM environments

| Environment | CUCM version |
|---|---|
| Dev/UAT | CUCM 10.5 |
| Production | CUCM 14 |

The active version is configured using:

```text
CUCM_AXL_VERSION=10.5
```

or

```text
CUCM_AXL_VERSION=14
```

### 11.2 WSDL handling

The implementation must support version-specific AXL WSDL files for:

- CUCM 10.5
- CUCM 14

The implementing developer or LLM should analyse both WSDLs to confirm whether required operations differ between versions.

WSDL files are stored in the wsdl/ directory of the project, with specific directories for each version.

### 11.3 AXL client abstraction

The backend must abstract CUCM operations behind a service/client layer.

Suggested interface:

```text
CucmClient:
  get_directory_number(pattern: str, route_partition: str) -> CucmDirectoryNumber
  update_call_forward_all(pattern: str, route_partition: str, destination: str) -> CucmUpdateResult
  health_check() -> CucmHealthResult
```

### 11.4 Required CUCM operations

The application requires the ability to:

- look up a Directory Number by pattern and route partition
- read current Call Forward All destination
- update Call Forward All destination
- read back Call Forward All destination after update
- perform a lightweight AXL health/authentication check

### 11.5 CUCM permissions

The AXL account uses full admin rights because constrained AXL permissions are not viable for this use case.

Implementation must:

- store the AXL username and password in environment variables
- never log the password
- never expose credentials through the health page
- treat failed AXL authentication as an admin-visible health failure

---

## 12. CUCM source-of-truth behaviour

### 12.1 Cached list state

The diversion list displays cached CUCM state stored in PostgreSQL.

Displayed fields:

- diversion name
- description
- source number
- cached current destination
- group
- last refreshed time
- last updated time
- last updated by

### 12.2 Manual refresh

Users can manually refresh visible diversion state.

Refresh behaviour:

- query CUCM for the relevant visible diversion or diversions
- update cached current destination
- update `last_refreshed_at`
- write audit event for success/failure
- show success/failure result in UI

Because total diversions are fewer than 50, refresh can be synchronous.

### 12.3 Update flow

Destination update flow:

1. User submits destination.
2. Backend verifies the user has access to the diversion.
3. Backend validates and normalises destination.
4. Backend writes Call Forward All destination to CUCM via AXL.
5. Backend reads back the destination from CUCM.
6. Backend validates returned CUCM destination.
7. Backend compares returned value to expected normalised +E.164 value.
8. If matched, backend updates cached current destination.
9. Backend records success audit event.
10. Frontend shows success.

### 12.4 Update failure behaviour

If the CUCM write fails:

- do not update cached destination as successful
- write failed audit event
- return a user-friendly error
- log technical details server-side

If CUCM write appears to succeed but read-back fails or mismatches:

- do not show clean success
- record warning/failure audit event
- if returned value is valid, cache what CUCM returned
- show a warning/error to the user

---

## 13. CUCM unavailable behaviour

If CUCM is unavailable:

- users can still log in
- cached diversion state is shown
- warning banner is displayed
- diversion edits are blocked
- manual refresh fails gracefully
- App Admin health page shows CUCM health failure

Suggested banner text:

```text
CUCM is currently unavailable. Cached diversion information is displayed. Diversion updates are temporarily disabled.
```

The application must not queue or retry user updates in the background for MVP.

---

## 14. API design

All API endpoints use Django session authentication and CSRF protection where required.

### 14.1 HTTP response conventions

| Condition | Status |
|---|---|
| Unauthenticated | `401 Unauthorized` |
| Authenticated but not permitted | `403 Forbidden` |
| Validation failure | `400 Bad Request` |
| Not found or inaccessible object | `404 Not Found` |
| Successful read | `200 OK` |
| Successful create | `201 Created` |
| Successful update action | `200 OK` |
| Successful delete | `204 No Content` |
| CUCM unavailable | `503 Service Unavailable` or `409 Conflict`, depending context |

Recommendation:

- Use `503` for health/connectivity failure.
- Use `400` for invalid user input.
- Use `403` for RBAC denial.
- Use `404` where the user must not know whether an inaccessible diversion exists.

### 14.2 Auth endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/auth/me/` | Current user and permissions |
| `GET` | `/api/auth/login/entra/` | Start Entra login, when enabled |
| `POST` | `/api/auth/login/ldap/` | LDAP login, when enabled |
| `POST` | `/api/auth/login/local/` | Local fallback login |
| `POST` | `/api/auth/logout/` | Destroy local session |

#### `GET /api/auth/me/` response

```json
{
  "id": "123",
  "email": "user@example.com",
  "display_name": "Example User",
  "role": "standard_user",
  "auth_source": "entra",
  "groups": [
    {
      "id": "10",
      "name": "Retail Operations"
    }
  ],
  "permissions": {
    "is_app_admin": false
  }
}
```

### 14.3 Diversion endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/diversions/` | List visible diversions |
| `GET` | `/api/diversions/{id}/` | Get diversion detail |
| `POST` | `/api/diversions/{id}/validate-destination/` | Validate and normalise destination |
| `POST` | `/api/diversions/{id}/update-destination/` | Write destination to CUCM |
| `POST` | `/api/diversions/{id}/refresh/` | Refresh cached state from CUCM |

#### `GET /api/diversions/` response

```json
{
  "results": [
    {
      "id": "div_123",
      "name": "Retail Support Main Line",
      "description": "Retail support after-hours diversion",
      "source_number": "0299990000",
      "cached_current_destination": "+61288881111",
      "group": {
        "id": "grp_1",
        "name": "Retail Operations"
      },
      "last_refreshed_at": "2026-06-15T04:20:00Z",
      "last_updated_at": "2026-06-15T04:10:00Z",
      "last_updated_by": "operator@example.com",
      "cucm_status": "available"
    }
  ]
}
```

#### `POST /api/diversions/{id}/validate-destination/` request

```json
{
  "destination": "(02) 9999 1234"
}
```

#### Successful validation response

```json
{
  "is_valid": true,
  "original_input": "(02) 9999 1234",
  "normalised_destination": "+61299991234",
  "destination_type": "fnn",
  "message": "Destination is valid."
}
```

#### Failed validation response

```json
{
  "is_valid": false,
  "original_input": "12345",
  "error_code": "internal_extension_not_allowed",
  "message": "Internal extensions are not permitted. Enter an Australian FNN, mobile or +E.164 number."
}
```

#### `POST /api/diversions/{id}/update-destination/` request

```json
{
  "destination": "0412 345 678"
}
```

#### Successful update response

```json
{
  "result": "success",
  "diversion": {
    "id": "div_123",
    "name": "Retail Support Main Line",
    "source_number": "0299990000",
    "cached_current_destination": "+61412345678",
    "last_refreshed_at": "2026-06-15T04:25:00Z",
    "last_updated_at": "2026-06-15T04:25:00Z",
    "last_updated_by": "operator@example.com"
  },
  "message": "Diversion updated successfully."
}
```

#### CUCM unavailable response

```json
{
  "result": "failure",
  "error_code": "cucm_unavailable",
  "message": "CUCM is currently unavailable. Cached diversion information is displayed and updates are temporarily disabled."
}
```

### 14.4 Admin user endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/admin/users/` | List users |
| `POST` | `/api/admin/users/validate/` | Validate external user |
| `POST` | `/api/admin/users/` | Create user |
| `GET` | `/api/admin/users/{id}/` | Get user detail |
| `PATCH` | `/api/admin/users/{id}/` | Update user |
| `DELETE` | `/api/admin/users/{id}/` | Hard delete user |

#### `POST /api/admin/users/validate/` request

```json
{
  "email": "user@example.com"
}
```

#### Response

```json
{
  "exists": true,
  "provider": "entra",
  "email": "user@example.com",
  "display_name": "Example User",
  "username": "user@example.com",
  "enabled": true
}
```

### 14.5 Admin group endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/admin/groups/` | List groups |
| `POST` | `/api/admin/groups/` | Create group |
| `GET` | `/api/admin/groups/{id}/` | Get group detail |
| `PATCH` | `/api/admin/groups/{id}/` | Rename/update group |
| `DELETE` | `/api/admin/groups/{id}/` | Delete if no diversions |

Group delete failure response:

```json
{
  "result": "failure",
  "error_code": "group_contains_diversions",
  "message": "This group cannot be deleted because it contains diversions."
}
```

### 14.6 Admin diversion endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/admin/diversions/` | List all diversions |
| `POST` | `/api/admin/diversions/validate-source/` | Validate source DN in CUCM |
| `POST` | `/api/admin/diversions/` | Create diversion |
| `GET` | `/api/admin/diversions/{id}/` | Get diversion detail |
| `PATCH` | `/api/admin/diversions/{id}/` | Update metadata/group |
| `DELETE` | `/api/admin/diversions/{id}/` | Delete local record only |

#### Validate source request

```json
{
  "source_number": "0299990000"
}
```

#### Validate source response

```json
{
  "is_valid": true,
  "source_number": "0299990000",
  "route_partition": "INTERNAL",
  "exists_in_cucm": true,
  "already_exists_in_app": false,
  "current_destination": "+61288881111"
}
```

#### Create diversion request

```json
{
  "name": "Retail Support Main Line",
  "description": "Retail support after-hours diversion",
  "source_number": "0299990000",
  "group_id": "grp_1"
}
```

### 14.7 Audit endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/admin/audit/` | Search/filter audit records |
| `GET` | `/api/admin/audit/export.csv` | Export filtered audit records |

Supported filters:

- start date
- end date
- actor email
- event type
- result
- object type
- source number
- destination number

### 14.8 Health endpoints

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| `GET` | `/api/healthz` | No | Load balancer health |
| `GET` | `/api/admin/health/` | App Admin | Full health page data |

#### `/api/healthz`

Should be lightweight.

Response:

```json
{
  "status": "ok"
}
```

It should confirm Django is running. It should not perform expensive CUCM checks.

#### `/api/admin/health/`

Response:

```json
{
  "application": {
    "status": "ok",
    "version": "0.1.0"
  },
  "database": {
    "status": "ok"
  },
  "cucm": {
    "status": "ok",
    "host": "configured",
    "version": "14",
    "route_partition": "INTERNAL"
  },
  "auth": {
    "mode": "entra",
    "status": "ok",
    "local_auth_enabled": true
  },
  "environment": {
    "required_variables_present": true
  }
}
```

Sensitive values must never be returned.

---

## 15. Frontend screen specification

### 15.1 Login screen

Displayed options depend on config:

If `AUTH_MODE=entra`:

- Entra login button.
- Local fallback login form/link.

If `AUTH_MODE=ldap`:

- LDAP username/email and password form.
- Local fallback login form/link.

Requirements:

- show validation errors clearly
- do not reveal sensitive auth failure details
- redirect authenticated users to correct landing page:
  - App Admin -> Admin Dashboard
  - Standard User -> My Diversions

### 15.2 My Diversions screen

Purpose: Standard user landing page.

Display:

- warning banner if CUCM unavailable
- list/table of accessible diversions
- name
- description
- source number
- cached current destination
- last refreshed time
- last updated time
- last updated by
- refresh button
- edit action, disabled if CUCM unavailable

Behaviour:

- Standard Users see only diversions assigned to their groups.
- App Admins may access all diversions, but their primary landing page is Admin Dashboard.

### 15.3 Edit Diversion screen

Display:

- diversion name
- description
- source number
- current cached destination
- last refreshed time
- destination input field
- validation feedback
- save button
- cancel/back button

Save behaviour:

1. User enters destination.
2. Frontend performs basic validation.
3. Backend validates destination.
4. UI shows confirmation prompt including:
   - diversion name
   - source number
   - entered destination
   - normalised destination
5. User confirms.
6. Backend performs CUCM update.
7. UI shows success/failure.

No reason/comment required.

No restore previous destination action.

### 15.4 Admin Dashboard

Display cards/links:

- Manage Users
- Manage Groups
- Manage Diversions
- Audit Log
- System Health

May display summary counts:

- total users
- total groups
- total diversions
- CUCM health status

### 15.5 Manage Users screen

Capabilities:

- list users
- search/filter by email/display name/role/auth source
- validate external user
- create user
- create local fallback user
- assign role
- assign groups
- hard delete user

Delete confirmation should state that audit history remains but user record will be removed.

### 15.6 Manage Groups screen

Capabilities:

- list groups
- show user count
- show diversion count
- create group
- rename group
- delete group when diversion count is zero

Deletion blocked if group contains diversions.

### 15.7 Manage Diversions screen

Capabilities:

- list all diversions
- create diversion
- validate source DN against CUCM
- assign diversion to exactly one group
- edit name/description/group
- refresh cached state
- delete local diversion record

Delete confirmation must state:

```text
This removes the diversion from Telephony Toolbox only. CUCM will not be changed.
```

### 15.8 Audit Log screen

Capabilities:

- filter audit records
- view audit event details
- export filtered CSV

Display fields:

- timestamp
- actor email
- actor display name
- event type
- result
- object type
- object name
- source number
- destination number
- message

### 15.9 System Health screen

App Admin only.

Display:

- application status
- database status
- CUCM AXL status
- configured CUCM version
- configured route partition
- auth mode
- auth provider status
- local auth enabled
- required environment variable presence

Do not display secret values.

---

## 16. Audit specification

### 16.1 Required event types

Auth:

```text
auth.login.success
auth.login.failure
auth.logout
```

Diversions:

```text
diversion.created
diversion.updated_metadata
diversion.deleted
diversion.source_validation.success
diversion.source_validation.failure
diversion.destination_validation.failure
diversion.destination_update.success
diversion.destination_update.failure
diversion.destination_update.warning
diversion.refresh.success
diversion.refresh.failure
```

Users:

```text
user.validated.success
user.validated.failure
user.created
user.updated
user.deleted
```

Groups:

```text
group.created
group.updated
group.deleted
group.delete_blocked
```

Health/system:

```text
system.health_check.failure
```

### 16.2 Audit retention

Retention period:

```text
90 days
```

Implement as a Django management command:

```text
python manage.py purge_old_audit_events
```

This command deletes audit events older than `AUDIT_RETENTION_DAYS`.

### 16.3 CSV export

CSV export must include denormalised fields and must not depend on joined user/diversion records.

Recommended columns:

```text
timestamp
event_type
result
actor_user_id_text
actor_email
actor_display_name
actor_auth_source
object_type
object_id_text
object_name
source_number
destination_number
message
metadata_json
```

---

## 17. Security requirements

### 17.1 Session and CSRF

- Use Django sessions.
- Use secure cookies in production.
- Use CSRF protection on mutating requests.
- Use same-origin frontend/API deployment where practical.

Recommended production cookie settings:

```text
SESSION_COOKIE_SECURE=true
CSRF_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true
CSRF_COOKIE_HTTPONLY=false
SESSION_COOKIE_SAMESITE=Lax
CSRF_COOKIE_SAMESITE=Lax
```

### 17.2 Secrets

- Store all passwords, keys and client secrets in environment variables.
- Never commit secrets.
- Never log secrets.
- Never display secrets in health endpoints.
- Health page may show whether required config is present, not values.

### 17.3 RBAC enforcement

RBAC must be enforced in backend API, not only frontend.

Every diversion read/update endpoint must verify object-level access.

### 17.4 Input validation

Validate:

- email addresses
- group names
- source numbers
- destination numbers
- role values
- UUID/object IDs
- query filters

### 17.5 Logging

Server logs may include:

- request ID
- event type
- actor email
- object ID
- source number
- result

Server logs must not include:

- passwords
- client secrets
- session cookies
- CSRF tokens

Destination numbers may appear in audit logs by design.

---

## 18. Suggested Django project structure

```text
backend/
  manage.py
  telephony_toolbox/
    settings.py
    urls.py
    asgi.py
    wsgi.py

  accounts/
    models.py
    serializers.py
    views.py
    auth_backends.py
    services.py
    urls.py
    tests/

  access_groups/
    models.py
    serializers.py
    views.py
    services.py
    urls.py
    tests/

  diversions/
    models.py
    serializers.py
    views.py
    services.py
    permissions.py
    urls.py
    tests/

  dialplan/
    validators.py
    tests/

  cucm/
    client.py
    client_105.py
    client_14.py
    factory.py
    exceptions.py
    schemas.py
    tests/

  audit/
    models.py
    serializers.py
    views.py
    services.py
    management/
      commands/
        purge_old_audit_events.py
    tests/

  health/
    views.py
    services.py
    urls.py
    tests/
```

Avoid naming the groups app `groups` to reduce confusion with Django auth groups.

---

## 19. Suggested service layer

### 19.1 Diversion update service

Suggested service:

```text
DiversionUpdateService.update_destination(
  user,
  diversion_id,
  raw_destination
)
```

Responsibilities:

1. Load diversion.
2. Check access.
3. Check CUCM availability.
4. Validate and normalise destination.
5. Update CUCM Call Forward All.
6. Read back from CUCM.
7. Validate read-back value.
8. Compare expected vs actual.
9. Update cached state.
10. Write audit event.
11. Return structured result.

### 19.2 Source DN validation service

Suggested service:

```text
DiversionAdminService.validate_source_number(
  source_number
)
```

Responsibilities:

1. Check local duplicate.
2. Query CUCM using configured partition.
3. Confirm DN exists.
4. Return current destination if available.
5. Return structured validation result.

### 19.3 Identity validation service

Suggested service:

```text
IdentityValidationService.validate_user(email)
```

Responsibilities:

1. Check configured `AUTH_MODE`.
2. Query Entra or LDAP.
3. Return normalised identity details.
4. Do not create user automatically.

### 19.4 Audit service

Suggested service:

```text
AuditService.record_event(...)
```

Responsibilities:

- denormalise actor fields
- denormalise object fields
- store metadata JSON
- never require FK references to mutable/deletable records

---

## 20. Testing requirements

### 20.1 Unit tests

Required unit test areas:

- dial plan validation
- normalisation
- role checks
- group deletion rules
- diversion deletion rules
- audit denormalisation
- auth mode selection
- CUCM client factory selection

### 20.2 API tests

Required API test areas:

- unauthenticated access returns 401
- Standard User cannot access admin endpoints
- Standard User cannot access unrelated diversion
- App Admin can access admin endpoints
- destination validation endpoint
- diversion update success path with mocked CUCM
- CUCM unavailable path
- CUCM read-back mismatch path
- user hard delete
- group delete blocked when diversions exist
- diversion delete leaves CUCM untouched

### 20.3 CUCM integration tests

Use mocked CUCM client for automated tests.

Test:

- DN exists
- DN missing
- update success
- update failure
- read-back success
- read-back mismatch
- CUCM unavailable
- AXL auth failure

### 20.4 Frontend tests

Recommended:

- Login screen renders correct provider mode.
- My Diversions shows only allowed diversions.
- Warning banner appears when CUCM unavailable.
- Edit button disabled when CUCM unavailable.
- Confirmation modal shows entered and normalised destination.
- Admin screens hidden from Standard Users.
- Group delete blocked message shown.
- Diversion delete confirmation includes CUCM unchanged warning.

---

## 21. Acceptance criteria

### 21.1 Authentication

- Given `AUTH_MODE=entra`, the login screen presents Entra login and local fallback login.
- Given `AUTH_MODE=ldap`, the login screen presents LDAP login and local fallback login.
- Given a valid local App Admin account, the user can log in even if external auth is unavailable.
- Given a user logs out, only the local Django session is destroyed.

### 21.2 User provisioning

- Given an App Admin validates a user, the system checks the configured external provider only.
- Given user validation succeeds, the App Admin can create the local user record.
- Given a user is not provisioned locally, external login does not grant application access.
- Given a user is hard deleted, audit records remain readable.

### 21.3 Group access

- Given a Standard User belongs to one group, they see only diversions assigned to that group.
- Given a Standard User belongs to multiple groups, they see diversions from all assigned groups.
- Given a diversion belongs to another group, the Standard User cannot retrieve it by ID.
- Given a group contains diversions, deletion is blocked.
- Given a group contains users but no diversions, deletion is allowed.

### 21.4 Diversion creation

- Given an App Admin enters a source DN that exists in CUCM, validation succeeds.
- Given a source DN does not exist in CUCM, validation fails.
- Given a source DN already exists in Telephony Toolbox, creation is blocked.
- Given a diversion is created, it is assigned to exactly one group.
- Given a diversion is created, route partition is sourced from configuration.

### 21.5 Destination validation

- Given `02 9999 1234`, the system normalises to `+61299991234`.
- Given `(02) 9999 1234`, the system normalises to `+61299991234`.
- Given `0412 345 678`, the system normalises to `+61412345678`.
- Given `+61299991234`, the system accepts it unchanged.
- Given `12345`, the system rejects it.
- Given an international number, the system rejects it.
- Given a SIP URI, the system rejects it.
- Given a blank value, the system rejects it.

### 21.6 CUCM update

- Given CUCM is available and destination is valid, the system updates Call Forward All via AXL.
- Given CUCM read-back returns the expected +E.164 value, success is shown.
- Given CUCM update fails, failure is shown and audit is recorded.
- Given CUCM read-back mismatches, clean success is not shown and audit is recorded.
- Given CUCM is unavailable, edits are blocked.

### 21.7 Cached state

- Given a user opens My Diversions, cached destination is shown.
- Given a user clicks refresh, the system queries CUCM and updates cached state.
- Given refresh fails, cached state remains visible and warning/error is shown.

### 21.8 Diversion deletion

- Given an App Admin deletes a diversion, the local record is removed.
- Given a diversion is deleted, CUCM is not modified.
- Given a diversion is deleted, an audit record states that CUCM was not changed.

### 21.9 Audit

- Given a diversion update succeeds, audit is recorded.
- Given a diversion update fails, audit is recorded.
- Given a user is deleted, historical audit still displays actor text.
- Given an App Admin exports audit logs, CSV contains filtered records.
- Given audit records are older than 90 days, retention cleanup removes them.

### 21.10 Health

- Given Django is running, `/api/healthz` returns OK.
- Given App Admin opens System Health, database, CUCM and auth provider health are displayed.
- Given CUCM is unavailable, System Health shows CUCM failure.
- Given required environment variables are missing, System Health indicates configuration issue without exposing secret values.

---

## 22. Implementation order recommendation

### Phase 1 — Backend foundation

- Django project setup.
- Custom user model.
- Session auth and CSRF.
- Local auth.
- PostgreSQL config.
- Audit model/service.
- Health endpoint.

### Phase 2 — Core data and RBAC

- Access groups.
- User/group memberships.
- Roles.
- Diversion model.
- Object-level permissions.

### Phase 3 — Dial plan

- Hard-coded validation module.
- Normalisation to Australian +E.164.
- Unit tests.

### Phase 4 — CUCM abstraction

- `CucmClient` interface.
- CUCM 10.5 and 14 client selection.
- WSDL integration.
- Mock client for tests.
- Health check.

### Phase 5 — Diversion workflows

- Source DN validation.
- Diversion creation.
- Manual refresh.
- Destination update.
- Read-back validation.
- Failure handling.

### Phase 6 — Admin API

- Manage users.
- Validate external users.
- Manage groups.
- Manage diversions.
- Audit search/export.
- Admin health.

### Phase 7 — Quasar frontend

- Login.
- My Diversions.
- Edit Diversion.
- Admin Dashboard.
- Manage Users.
- Manage Groups.
- Manage Diversions.
- Audit Log.
- System Health.

### Phase 8 — Deployment packaging

- gunicorn systemd unit.
- nginx virtual host.
- static frontend build process.
- environment file template.
- database migration process.
- audit retention scheduled task.

---

## 23. Open implementation details for developers to confirm during build

These are not product design blockers, but should be confirmed during implementation:

1. Exact Entra OIDC library/package to use.
2. Exact LDAP package/config pattern.
3. Whether Django primary keys should be UUIDs or bigint IDs.
4. Exact CUCM AXL Python library approach after reviewing CUCM 10.5 and 14 WSDL files.
5. Whether nginx proxies gunicorn via TCP or Unix socket.
6. Exact local bootstrap method for the first App Admin account.
7. Exact production hostname and TLS certificate handling.
8. Exact PostgreSQL database name, user and schema convention.

---

## 24. v0.1 completion definition

Telephony Toolbox v0.1 is complete when:

- a local App Admin can be bootstrapped
- App Admin can create users, groups and diversions
- App Admin can validate external users
- App Admin can validate source DNs against CUCM
- Standard Users can log in and see assigned diversions
- Standard Users can update valid destinations
- invalid destinations are rejected
- CUCM updates are performed synchronously
- CUCM read-back is validated
- cached state can be manually refreshed
- CUCM unavailable state blocks edits but allows read-only cached viewing
- audit events are recorded and exportable
- health endpoints exist
- the application runs behind nginx/gunicorn on RHEL 9
- Quasar static frontend is served by nginx
- Django Admin is not required or exposed
