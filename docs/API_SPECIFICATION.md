# Telephony Toolbox API Specification

Complete REST API documentation for Telephony Toolbox frontend-to-backend communication.

## Base URL

```
http://localhost:8000/api   (development)
https://telephonytoolbox.example.internal/api   (production)
```

## Authentication

All endpoints except auth endpoints require an authenticated session:

- **Method**: Django Session Authentication (Cookie-based)
- **CSRF Protection**: Required for POST/PATCH/DELETE operations
- **Headers**:
  - `X-CSRFToken: <token>` (for POST/PATCH/DELETE) or cookie-based (form submission)
  - `Content-Type: application/json`

### Session Flow

1. Client sends `POST /api/auth/login/local/` with credentials
2. Server responds with `Set-Cookie: sessionid=...` and user data
3. Client includes `sessionid` cookie in subsequent requests
4. For POST/PATCH/DELETE, client includes `X-CSRFToken` header

## Error Responses

All errors return JSON with the following structure:

```json
{
  "detail": "Error message" 
}
```

Or for validation errors:

```json
{
  "field_name": ["Error message"],
  "another_field": ["Error 1", "Error 2"]
}
```

### HTTP Status Codes

| Code | Meaning | When |
|------|---------|------|
| 200 | OK | Successful GET, PATCH |
| 201 | Created | Successful POST creation |
| 400 | Bad Request | Validation error, invalid input |
| 401 | Unauthorized | Session expired, not logged in |
| 403 | Forbidden | User lacks permission (role, group membership) |
| 404 | Not Found | Resource doesn't exist |
| 503 | Service Unavailable | CUCM or LDAP/Entra provider unavailable |

---

## Authentication Endpoints

### Get Authentication Options

```http
GET /api/auth/options/
```

**Authentication**: None required

**Response** (200 OK):

```json
{
  "auth_mode": "entra",
  "local_auth_enabled": true
}
```

**Fields**:
- `auth_mode` — Primary auth provider: `"ldap"`, or `"entra"`
- `local_auth_enabled` — Whether local user login is available (boolean)

**Use Case**: Frontend determines which login forms to display.

---

### Get Current User

```http
GET /api/auth/me/
```

**Authentication**: Required (session)

**Response** (200 OK):

```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "display_name": "Jane Doe",
  "role": "standard_user",
  "auth_source": "entra",
  "is_active": true
}
```

**Fields**:
- `user_id` — UUID of user
- `email` — Canonical user email
- `display_name` — Human-readable name
- `role` — `"standard_user"` or `"app_admin"`
- `auth_source` — `"entra"`, `"ldap"`, or `"local"`
- `is_active` — Whether user can log in

**Use Case**: Check current session status and load user-specific data (role, permissions).

---

### Local User Login

```http
POST /api/auth/login/local/
```

**Authentication**: None required

**Request Body**:

```json
{
  "email": "user@example.com",
  "password": "ChangeMeNow!"
}
```

**Success Response** (200 OK):

```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "display_name": "Jane Doe",
  "role": "standard_user",
  "auth_source": "local",
  "is_active": true
}
```

Also sets `Set-Cookie: sessionid=...` header.

**Error Responses**:

```
400 Bad Request
{
  "message": "Invalid login credentials."
}

403 Forbidden
{
  "message": "User is not provisioned for Telephony Toolbox."
}
```

**Validation**:
- Email is normalized (lowercased, whitespace trimmed)
- Password validated against local user record
- User must have `is_active=true` and `is_local=true`
- Audit event logged regardless of success/failure

---

### LDAP User Login

```http
POST /api/auth/login/ldap/
```

**Authentication**: None required

**Request Body**:

```json
{
  "email": "user@example.com",
  "password": "LdapPassword"
}
```

**Success Response** (200 OK):

```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "display_name": "Jane Doe",
  "role": "standard_user",
  "auth_source": "ldap",
  "is_active": true
}
```

Also sets `Set-Cookie: sessionid=...` header.

**Error Responses**:

```
400 Bad Request
{
  "message": "Invalid login credentials."
}

403 Forbidden
{
  "message": "User is not provisioned for Telephony Toolbox."
}

404 Not Found
{
  "message": "LDAP authentication is not enabled."
}

503 Service Unavailable
{
  "message": "LDAP is currently unavailable."
}
```

**Flow**:
1. Validate email/password against LDAP server
2. If valid and enabled, sync user to local database (create if new)
3. Create Django session
4. Return user data

---

### Entra OAuth2 Login Redirect

```http
GET /api/auth/login/entra/
```

**Authentication**: None required

**Response** (302 Redirect):

Redirects to Entra login page:

```
https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize?
  client_id={ENTRA_CLIENT_ID}
  &redirect_uri={ENTRA_REDIRECT_URI}
  &response_type=code
  &scope=openid profile email
  &state={state}
  &nonce={nonce}
```

**Use Case**: Step 1 of Entra OIDC flow; frontend redirects user here.

---

### Entra OAuth2 Callback

```http
GET /api/auth/login/entra/callback/?code=...&state=...
```

**Authentication**: None required

**Query Parameters**:
- `code` — Authorization code from Entra
- `state` — State parameter (CSRF protection)

**Success Response** (302 Redirect):

Redirects to `/diversions` or `/admin` depending on user role:

```
Location: /diversions
Set-Cookie: sessionid=...
```

**Error Responses**:

```
302 Redirect to /login?error=invalid_state
302 Redirect to /login?error=invalid_code
302 Redirect to /login?error=not_provisioned
```

**Flow**:
1. Validate state parameter
2. Exchange authorization code for ID token
3. Validate token signature and claims
4. Extract email and create/sync user
5. Create Django session
6. Redirect to appropriate dashboard

---

### Logout

```http
POST /api/auth/logout/
```

**Authentication**: Required (session)

**Request Body**: (empty)

**Response** (200 OK):

```json
{
  "message": "Logged out successfully."
}
```

Also clears `sessionid` cookie.

**Use Case**: End user session; destroy session cookie.

---

## Diversion Endpoints

### List Visible Diversions

```http
GET /api/diversions/
```

**Authentication**: Required (Standard User or App Admin)

**Query Parameters**: None

**Response** (200 OK):

```json
{
  "results": [
    {
      "diversion_id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Main Office",
      "description": "Diverts main line to regional office",
      "source_number": "+61212345678",
      "source_partition": "INTERNAL",
      "cached_current_destination": "+61299998888",
      "group_id": "660e8400-e29b-41d4-a716-446655440001",
      "group_name": "Operations",
      "last_refreshed_at": "2026-06-15T10:30:00Z",
      "last_updated_at": "2026-06-15T09:15:00Z",
      "last_updated_by": "admin@example.com",
      "cucm_status": "available"
    },
    ...
  ]
}
```

**Filtering**:
- Standard Users: See only diversions in their group memberships
- App Admins: See all diversions

**Fields** (Diversion object):
- `diversion_id` — UUID of diversion
- `name` — Human-readable name
- `description` — Optional context
- `source_number` — Globally unique directory number (in +E.164 format if created with +)
- `source_partition` — CUCM partition name (default: INTERNAL)
- `cached_current_destination` — Last known CFA destination from CUCM
- `group_id` — UUID of managing access group
- `group_name` — Human-readable group name
- `last_refreshed_at` — ISO 8601 timestamp of last CUCM sync
- `last_updated_at` — ISO 8601 timestamp of last CFA change
- `last_updated_by` — Email of user who made last change
- `cucm_status` — `"available"` or `"unavailable"` (reflects current CUCM health)

**Use Case**: Populate user's dashboard with assigned diversions.

---

### Get Diversion Detail

```http
GET /api/diversions/{diversion_id}/
```

**Authentication**: Required (Standard User or App Admin)

**Path Parameters**:
- `diversion_id` — UUID of diversion

**Response** (200 OK):

Same Diversion object as list endpoint.

**Error Responses**:

```
404 Not Found
User is not in diversion's group (for Standard Users)
```

**Use Case**: Load single diversion for detail view/editing.

---

### Validate Destination (No Write)

```http
POST /api/diversions/{diversion_id}/validate-destination/
```

**Authentication**: Required (Standard User or App Admin)

**Path Parameters**:
- `diversion_id` — UUID of diversion

**Request Body**:

```json
{
  "destination": "02 9999 8888"
}
```

**Success Response** (200 OK):

```json
{
  "is_valid": true,
  "original_input": "02 9999 8888",
  "normalised_destination": "+61299998888",
  "destination_type": "fnn",
  "message": "Destination is valid."
}
```

**Validation Error Response** (400 Bad Request):

```json
{
  "is_valid": false,
  "original_input": "0011 1 202 555 5555",
  "error_code": "international_not_allowed",
  "message": "International numbers are not permitted. Enter an Australian FNN, mobile or +E.164 number."
}
```

**Possible error_code Values**:
- `destination_required` — Empty string
- `sip_uri_not_allowed` — Contains `sip:` or `@`
- `international_not_allowed` — Starts with `0011`
- `unsupported_dial_string` — Doesn't match known patterns
- `internal_extension_not_allowed` — < 10 digits
- `non_australian_e164` — +E.164 but not +61

**Use Case**: Real-time validation in UI as user types destination.

---

### Update Diversion Destination

```http
POST /api/diversions/{diversion_id}/update-destination/
```

**Authentication**: Required (Standard User or App Admin)

**Path Parameters**:
- `diversion_id` — UUID of diversion

**Request Body**:

```json
{
  "destination": "+61299998888"
}
```

**Success Response** (200 OK):

```json
{
  "message": "Destination updated successfully.",
  "diversion": {
    "diversion_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Main Office",
    "source_number": "+61212345678",
    "cached_current_destination": "+61299998888",
    "group_id": "660e8400-e29b-41d4-a716-446655440001",
    "last_updated_at": "2026-06-15T10:35:00Z",
    "last_updated_by": "user@example.com",
    "cucm_status": "available",
    ...
  }
}
```

**Error Responses**:

```
400 Bad Request (validation failed)
{
  "is_valid": false,
  "error_code": "sip_uri_not_allowed",
  "message": "SIP URIs are not permitted..."
}

403 Forbidden (permission denied)
{
  "message": "You do not have permission to update this diversion."
}

404 Not Found (diversion not found or not accessible)
{
  "message": "Not found."
}

503 Service Unavailable (CUCM offline)
{
  "message": "CUCM is currently unavailable. Cached diversion information is displayed and updates are temporarily disabled."
}
```

**Flow**:
1. Validate request body
2. Verify user has permission (group membership or admin)
3. Validate destination format and normalization
4. Call CUCM updateLine() AXL API
5. Read back from CUCM to verify write succeeded
6. Update local cached_current_destination
7. Record audit event
8. Return updated diversion

**Audit Trail**: Every update logged with actor email, before/after state, CUCM response.

**Use Case**: User submits new CFA destination; backend writes to CUCM and confirms success.

---

### Refresh Diversion from CUCM

```http
POST /api/diversions/{diversion_id}/refresh/
```

**Authentication**: Required (Standard User or App Admin)

**Path Parameters**:
- `diversion_id` — UUID of diversion

**Request Body**: (empty)

**Success Response** (200 OK):

```json
{
  "message": "Diversion refreshed successfully.",
  "diversion": {
    "diversion_id": "550e8400-e29b-41d4-a716-446655440000",
    "cached_current_destination": "+61299998888",
    "last_refreshed_at": "2026-06-15T10:40:00Z",
    "cucm_status": "available",
    ...
  }
}
```

**Error Responses**:

```
403 Forbidden (permission denied)
{
  "message": "You do not have permission to refresh this diversion."
}

404 Not Found (diversion not found)
{
  "message": "Not found."
}

503 Service Unavailable (CUCM offline)
{
  "message": "CUCM is currently unavailable..."
}
```

**Use Case**: User clicks "Refresh" button to sync latest CUCM state (e.g., after external change).

---

## Admin Endpoints

All admin endpoints require `role=app_admin`.

### List All Diversions (Admin)

```http
GET /api/admin/diversions/
```

**Authentication**: Required (App Admin only)

**Response** (200 OK):

```json
{
  "results": [
    { /* same Diversion object structure */ },
    ...
  ]
}
```

App Admins see all diversions regardless of group membership.

---

### Create Diversion

```http
POST /api/admin/diversions/
```

**Authentication**: Required (App Admin only)

**Request Body**:

```json
{
  "name": "Main Office",
  "description": "Diverts main line to regional office",
  "source_number": "+61212345678",
  "group_id": "660e8400-e29b-41d4-a716-446655440001"
}
```

**Success Response** (201 Created):

```json
{
  "diversion_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Main Office",
  "description": "Diverts main line to regional office",
  "source_number": "+61212345678",
  "source_partition": "INTERNAL",
  "cached_current_destination": "",
  "group_id": "660e8400-e29b-41d4-a716-446655440001",
  "group_name": "Operations",
  ...
}
```

**Error Responses**:

```
400 Bad Request (validation)
{
  "message": "Source number was not found in CUCM."
}

400 Bad Request (duplicate)
{
  "message": "This source number already exists in Telephony Toolbox."
}

403 Forbidden (not admin)
{
  "message": "You do not have permission to perform this action."
}

503 Service Unavailable (CUCM offline)
{
  "message": "CUCM is currently unavailable."
}
```

**Validation**:
- Source number must exist in CUCM
- Source number must not already exist in app
- Group must exist
- Name and source_number are required

**Use Case**: App Admin onboards new diversion to be managed by the app.

---

### Validate Source Number

```http
POST /api/admin/diversions/validate-source/
```

**Authentication**: Required (App Admin only)

**Request Body**:

```json
{
  "source_number": "+61212345678"
}
```

**Success Response** (200 OK):

```json
{
  "is_valid": true,
  "source_number": "+61212345678",
  "route_partition": "INTERNAL",
  "exists_in_cucm": true,
  "already_exists_in_app": false,
  "line_name": "John Smith",
  "current_destination": "+61299998888"
}
```

**Use Case**: Async validation as admin enters source number in create form.

---

### List Users (Admin)

```http
GET /api/admin/users/
```

**Authentication**: Required (App Admin only)

**Response** (200 OK):

```json
{
  "results": [
    {
      "user_id": "550e8400-e29b-41d4-a716-446655440000",
      "email": "admin@example.com",
      "display_name": "Jane Doe",
      "role": "app_admin",
      "auth_source": "local",
      "is_active": true,
      "created_at": "2026-06-01T09:00:00Z"
    },
    ...
  ]
}
```

---

### Create User (Admin)

```http
POST /api/admin/users/
```

**Authentication**: Required (App Admin only)

**Request Body**:

```json
{
  "email": "newuser@example.com",
  "display_name": "New User",
  "role": "standard_user",
  "password": "InitialPassword123!" 
}
```

**Note**: `password` only required for local users; omit for Entra/LDAP.

**Success Response** (201 Created):

```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "newuser@example.com",
  "display_name": "New User",
  "role": "standard_user",
  "auth_source": "local",
  "is_active": true
}
```

---

### Update User (Admin)

```http
PATCH /api/admin/users/{user_id}/
```

**Authentication**: Required (App Admin only)

**Request Body** (all optional):

```json
{
  "display_name": "Updated Name",
  "role": "app_admin",
  "is_active": false
}
```

**Success Response** (200 OK):

Returns updated User object.

---

### Delete User (Admin)

```http
DELETE /api/admin/users/{user_id}/
```

**Authentication**: Required (App Admin only)

**Response** (204 No Content)

User is hard-deleted from database. Audit events preserve actor details as text snapshots.

---

### List Groups (Admin)

```http
GET /api/admin/groups/
```

**Authentication**: Required (App Admin only)

**Response** (200 OK):

```json
{
  "results": [
    {
      "group_id": "660e8400-e29b-41d4-a716-446655440001",
      "name": "Operations",
      "description": "Operational team managing call diversions",
      "member_count": 5,
      "created_at": "2026-06-01T09:00:00Z"
    },
    ...
  ]
}
```

---

### Create Group (Admin)

```http
POST /api/admin/groups/
```

**Authentication**: Required (App Admin only)

**Request Body**:

```json
{
  "name": "Operations",
  "description": "Operational team managing call diversions"
}
```

**Success Response** (201 Created):

Returns Group object.

---

### Get Group Detail (Admin)

```http
GET /api/admin/groups/{group_id}/
```

**Authentication**: Required (App Admin only)

**Response** (200 OK):

```json
{
  "group_id": "660e8400-e29b-41d4-a716-446655440001",
  "name": "Operations",
  "description": "Operational team managing call diversions",
  "members": [
    {
      "user_id": "550e8400-e29b-41d4-a716-446655440000",
      "email": "user1@example.com",
      "display_name": "User 1",
      "role": "standard_user"
    },
    ...
  ],
  "created_at": "2026-06-01T09:00:00Z"
}
```

---

### Update Group (Admin)

```http
PATCH /api/admin/groups/{group_id}/
```

**Authentication**: Required (App Admin only)

**Request Body**:

```json
{
  "name": "Operations Team",
  "description": "Updated description",
  "member_ids": ["550e8400-e29b-41d4-a716-446655440000", "...]
}
```

**Note**: `member_ids` replaces the entire membership list.

**Success Response** (200 OK):

Returns updated Group object.

---

### List Audit Events (Admin)

```http
GET /api/admin/audit/
```

**Authentication**: Required (App Admin only)

**Query Parameters**:
- `limit` (default: 100) — Max results
- `offset` (default: 0) — Pagination offset
- `event_type` (optional) — Filter by event type (e.g., `diversion.update.success`)
- `result` (optional) — Filter by result (`success`, `failure`, `warning`)
- `actor_email` (optional) — Filter by actor email
- `object_type` (optional) — Filter by object type (`diversion`, `user`, `auth`, etc.)

**Response** (200 OK):

```json
{
  "count": 1523,
  "next": "/api/admin/audit/?limit=100&offset=100",
  "previous": null,
  "results": [
    {
      "event_id": "550e8400-e29b-41d4-a716-446655440000",
      "timestamp": "2026-06-15T10:35:00Z",
      "event_type": "diversion.update.success",
      "result": "success",
      "actor_email": "user@example.com",
      "actor_display_name": "User Name",
      "object_type": "diversion",
      "object_name": "Main Office",
      "source_number": "+61212345678",
      "destination_number": "+61299998888",
      "message": "Destination updated successfully.",
      "metadata_json": { "cucm_response": {...} }
    },
    ...
  ]
}
```

**Retention**: Events older than 90 days (configurable via `AUDIT_RETENTION_DAYS`) are automatically deleted.

**Use Case**: Compliance auditing and troubleshooting.

---

### Export Audit Events to CSV (Admin)

```http
GET /api/admin/audit/export.csv
```

**Authentication**: Required (App Admin only)

**Query Parameters**: Same as audit list endpoint.

**Response** (200 OK):

```
Content-Type: text/csv
Content-Disposition: attachment; filename="audit_export_20260615.csv"

timestamp,event_type,result,actor_email,actor_display_name,object_type,object_name,source_number,destination_number,message
2026-06-15T10:35:00Z,diversion.update.success,success,user@example.com,User Name,diversion,Main Office,+61212345678,+61299998888,Destination updated successfully.
...
```

**Use Case**: Export audit trail for external compliance review or archival.

---

## Health Endpoints

### Basic Health Check

```http
GET /api/healthz/
```

**Authentication**: None required

**Response** (200 OK):

```json
{
  "status": "ok"
}
```

**Use Case**: Load balancer health check; confirms application is responsive.

---

### Admin Health Report

```http
GET /api/admin/health/
```

**Authentication**: Required (App Admin only)

**Response** (200 OK):

```json
{
  "application_status": "ok",
  "cucm_status": "available",
  "cucm_host": "cucm.example.internal",
  "cucm_version": "14",
  "database_status": "ok",
  "auth_provider_status": "ok",
  "auth_mode": "entra"
}
```

**Fields**:
- `application_status` — `"ok"` or `"error"`
- `cucm_status` — `"available"` or `"unavailable"`
- `cucm_host` — Configured CUCM AXL host
- `cucm_version` — Configured AXL version
- `database_status` — `"ok"` or `"error"`
- `auth_provider_status` — `"ok"` or `"error"` (reflects LDAP/Entra availability)
- `auth_mode` — Configured auth provider

**Use Case**: Admin dashboard to verify system integration points.

---

## Common Request Patterns

### Handling Validation Errors

When destination validation fails:

```javascript
// Frontend
const response = await fetch('/api/diversions/123/validate-destination/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
  body: JSON.stringify({ destination: "sip:user@example.com" })
});

if (!response.ok) {
  const data = await response.json();
  console.error(data.error_code); // "sip_uri_not_allowed"
  console.error(data.message);    // User-facing message
} else {
  const data = await response.json();
  console.log(data.normalised_destination); // "+61212345678"
}
```

### Updating with Read-Back Verification

When updating a diversion:

```javascript
// User submits destination via /api/diversions/{id}/update-destination/
// Backend:
// 1. Validates input
// 2. Calls CUCM updateLine()
// 3. Reads back from CUCM
// 4. Verifies returned state matches requested state
// 5. If match: success; if mismatch: failure with detail

// Frontend receives either:
{
  "message": "Destination updated successfully.",
  "diversion": { /* updated state */ }
}
// OR
{
  "message": "Update failed: CUCM returned unexpected state",
  "cucm_response": { /* details */ }
}
```

### Pagination for Audit Logs

```javascript
// List first 100 events
const page1 = await fetch('/api/admin/audit/?limit=100&offset=0');
const data = await page1.json();

// Load next page
const page2 = await fetch(data.next);

// Filter by event type
const filtered = await fetch('/api/admin/audit/?event_type=diversion.update.success&limit=100');
```

---

## WebSocket Support

**Not currently implemented.** Real-time updates are not required for MVP; clients poll via GET requests.

Future enhancement: Emit audit events via WebSocket for admin dashboards.

---

## Rate Limiting

**Not currently implemented.** No rate limiting on API endpoints; deployments should implement at nginx level if needed.

---

## API Versioning

**Not implemented.** All endpoints are `/api/` (v1 implicit). Breaking changes would result in new `/api/v2/` endpoints.

---

## Changelog

### v1.0 (Initial Release)

- Authentication endpoints (local, LDAP, Entra)
- Diversion listing, detail, validation, update, refresh
- Admin user management
- Admin group management
- Admin diversion management
- Audit logging and export
- Health endpoints
