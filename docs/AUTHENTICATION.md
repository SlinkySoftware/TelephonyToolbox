# Telephony Toolbox Authentication Guide

Complete reference for authentication flows, identity provider setup, and user provisioning.

## Overview

Telephony Toolbox supports flexible authentication:

- **Primary Provider**: Entra (OIDC), generic OIDC/OAuth, or LDAP (selected via `AUTH_MODE`)
- **Local Fallback**: Always available; credentials stored in local User table
- **Session Management**: Django session cookies (HttpOnly, Secure, SameSite=Strict)
- **Frontend Provider Label**: `EXTERNAL_AUTH_NAME` controls the display name shown on login screens

## Authentication Flows

### Local Authentication Flow

```
User enters email + password
         ↓
POST /api/auth/login/local/
         ↓
Backend validates credentials against User model (PBKDF2 hash)
         ↓
If valid & is_active & is_local:
  ├─ Create Django session
  ├─ Record audit event
  └─ Set Set-Cookie: sessionid=...
         ↓
Return user data (email, role, display_name)
```

**Use Cases**:
- Development/testing without external auth provider
- Emergency access when Entra/LDAP unavailable
- Local accounts for app bootstrapping

**User Creation**:
```bash
# Via management command
python backend/manage.py bootstrap_local_app_admin \
  --email admin@example.com \
  --display-name "Admin Name" \
  --password "SecurePassword123!"

# Via admin API (App Admin only)
POST /api/admin/users/
{
  "email": "user@example.com",
  "display_name": "User Name",
  "role": "standard_user",
  "password": "InitialPassword123!"
}
```

---

### LDAP Authentication Flow

```
User enters email + password
         ↓
POST /api/auth/login/ldap/
         ↓
Backend:
  1. Check if AUTH_MODE = ldap (else 404)
  2. Connect to LDAP as service account (LDAP_BIND_DN)
  3. Search for user by email (LDAP_USER_SEARCH_BASE)
  4. If found, attempt bind with user DN + password
  5. If bind succeeds:
     - Check group membership (LDAP_GROUP_SEARCH_FILTER if set)
     - Fetch display_name, email from LDAP attributes
     - Sync user to local DB (create if new, update if exists)
     - Create Django session
  6. If bind fails or not provisioned: return 400/403
         ↓
Return user data
```

**LDAP Configuration** (`CONFIGURATION.md`):
- `LDAP_SERVER_URI` — LDAP server URL (ldap:// or ldaps://)
- `LDAP_BIND_DN` — Service account DN for searches
- `LDAP_BIND_PASSWORD` — Service account password
- `LDAP_USER_SEARCH_BASE` — Base DN for user searches
- `LDAP_USER_EMAIL_ATTRIBUTE` — Attribute containing email (default: `mail`)
- `LDAP_USER_DISPLAY_NAME_ATTRIBUTE` — Attribute for display name (default: `displayName`)
- `LDAP_USER_ENABLED_ATTRIBUTE` — Optional; checks if user is enabled
- `LDAP_GROUP_SEARCH_FILTER` — Optional; restricts login to specific groups

**Example Setup** (Active Directory):

```bash
LDAP_SERVER_URI=ldaps://ldap.company.internal:636
LDAP_BIND_DN=cn=ldap-service,cn=users,dc=company,dc=internal
LDAP_BIND_PASSWORD=ServiceAccountPassword123!
LDAP_USER_SEARCH_BASE=cn=users,dc=company,dc=internal
LDAP_USER_EMAIL_ATTRIBUTE=mail
LDAP_USER_DISPLAY_NAME_ATTRIBUTE=displayName
LDAP_USER_ENABLED_ATTRIBUTE=userAccountControl
LDAP_GROUP_SEARCH_FILTER=(&(mail=%email)(memberOf=cn=TelephonyToolboxUsers,ou=Groups,dc=company,dc=internal))
```

**Troubleshooting LDAP**:

1. **Test LDAP connectivity**:
   ```bash
   ldapsearch -H ldaps://ldap.company.internal:636 \
     -D "cn=ldap-service,cn=users,dc=company,dc=internal" \
     -w "ServicePassword" \
     -b "cn=users,dc=company,dc=internal" \
     "(mail=user@company.com)"
   ```

2. **Verify email attribute**:
   Look for `mail:` field in LDAP search result. Update `LDAP_USER_EMAIL_ATTRIBUTE` if different.

3. **Check group membership** (if filter set):
   Confirm user appears in `memberOf` attribute:
   ```bash
   ldapsearch ... "(mail=user@company.com)" memberOf
   ```

4. **Application logs**:
   Check backend logs for LDAP exceptions:
   ```bash
   tail -f /var/log/telephonytoolbox/application.log | grep -i ldap
   ```

---

### Entra OAuth2 (OIDC) Authentication Flow

```
User clicks "Login with Entra"
         ↓
GET /api/auth/login/entra/
         ↓
Backend:
  1. Check if AUTH_MODE = entra (else 404)
  2. Generate random state (CSRF protection)
  3. Generate random nonce (replay protection)
  4. Build OAuth authorize URL
  5. Redirect to Entra login page
         ↓
User authenticates in Entra (MFA, etc.)
         ↓
Entra redirects back to callback URL with authorization code
         ↓
GET /api/auth/login/entra/callback/?code=...&state=...
         ↓
Backend:
  1. Validate state parameter (matches session)
  2. Exchange code for access token + ID token
  3. Validate ID token (signature, claims, nonce)
  4. Extract email from ID token
  5. Sync user to local DB (create if new, update if exists)
  6. Create Django session
         ↓
Redirect to /diversions or /admin
```

**OAuth2 Configuration** (`CONFIGURATION.md`):
- `ENTRA_CLIENT_ID` — Application ID from Azure Portal
- `ENTRA_CLIENT_SECRET` — Client secret from Azure Portal
- `ENTRA_TENANT_ID` — Directory ID (tenant ID)
- `ENTRA_REDIRECT_URI` — Callback URL registered in Entra

---

### Generic OIDC/OAuth Authentication Flow

```
User clicks provider sign-in button
             ↓
GET /api/auth/login/oidc/
             ↓
Backend:
   1. Check if AUTH_MODE = oidc (else 404)
   2. Load authorization endpoint from OIDC discovery metadata
   3. Generate random state/nonce values
   4. Redirect to provider login page
             ↓
User authenticates with provider (for example Authentik, Okta, Keycloak)
             ↓
Provider redirects back with authorization code
             ↓
GET /api/auth/login/oidc/callback/?code=...&state=...
             ↓
Backend:
   1. Validate state parameter
   2. Exchange code for tokens
   3. Validate ID token / userinfo claims
   4. Extract email, username, and display name using configured claim names
   5. Sync user to local DB (update only; user must already be provisioned)
   6. Create Django session
             ↓
Redirect to /diversions or /admin
```

**OIDC Configuration** (`CONFIGURATION.md`):
- `OIDC_CLIENT_ID`
- `OIDC_CLIENT_SECRET`
- `OIDC_METADATA_URL`
- `OIDC_REDIRECT_URI`
- `OIDC_SCOPES`
- `OIDC_EMAIL_CLAIM`
- `OIDC_USERNAME_CLAIM`
- `OIDC_DISPLAY_NAME_CLAIM`

**Provisioning Note**:
- Generic OIDC/OAuth providers do not expose a standard directory search API.
- App Admins can still create external users manually by email.
- The admin-side `validate external user` helper is available only for Entra and LDAP in the current implementation.

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

## Entra Setup (Azure Portal)

### Authentication Methods Comparison

| Method | Security | Complexity | Expiration | Production Ready |
|--------|----------|-----------|-----------|------------------|
| **Client Secret** | Lower | Simple | Manual renewal | Development only |
| **Client Certificate** | Higher | Moderate | Auto-managed | ✅ Recommended |

**Recommendation**: Use **Client Certificates** for production deployments. Certificates are more secure because:
- Not transmitted over network (stored locally)
- Harder to compromise than secrets in environment files
- Can be issued with hardware security module (HSM) backing
- Automatic expiration alerts from certificate authority
- Can be rotated without downtime

---

### Step 1: Create App Registration

1. Go to **Azure Portal** → **Entra ID** → **App registrations**
2. Click **New registration**
3. Enter:
   - **Name**: Telephony Toolbox
   - **Supported account types**: Accounts in this organizational directory only
   - **Redirect URI**: 
     - Platform: Web
     - URI: `https://telephonytoolbox.example.internal/api/auth/login/entra/callback/`
4. Click **Register**

### Step 2: Note Application Details

- Copy **Application (client) ID** → `ENTRA_CLIENT_ID`
- Copy **Directory (tenant) ID** → `ENTRA_TENANT_ID`

### Step 3a: Configure Client Certificate (Recommended for Production)

#### Generate Self-Signed Certificate (Development)

```bash
# Generate private key (3072-bit RSA, stronger than 2048)
openssl genrsa -out /etc/telephonytoolbox/entra-cert/entra-key.pem 3072

# Generate certificate (valid 2 years)
openssl req -new -x509 -key /etc/telephonytoolbox/entra-cert/entra-key.pem \
  -out /etc/telephonytoolbox/entra-cert/entra-cert.pem \
  -days 730 \
  -subj "/C=AU/ST=NSW/L=Sydney/O=Company/CN=TelephonyToolbox"

# Create PKCS12 bundle (for Azure Portal upload)
openssl pkcs12 -export \
  -in /etc/telephonytoolbox/entra-cert/entra-cert.pem \
  -inkey /etc/telephonytoolbox/entra-cert/entra-key.pem \
  -out /etc/telephonytoolbox/entra-cert/entra-cert.p12 \
  -name "Telephony Toolbox" \
  -passout pass:""  # Empty password for server use

# Set permissions
sudo chmod 600 /etc/telephonytoolbox/entra-cert/entra-key.pem
sudo chmod 644 /etc/telephonytoolbox/entra-cert/entra-cert.pem
sudo chmod 600 /etc/telephonytoolbox/entra-cert/entra-cert.p12

# Set ownership
sudo chown telephonytoolbox:telephonytoolbox /etc/telephonytoolbox/entra-cert/*
```

#### Upload Certificate to Entra

1. Go to **Azure Portal** → **Entra ID** → **App registrations** → [Your app]
2. Click **Certificates & secrets**
3. Click **Certificates** tab
4. Click **Upload certificate**
5. Select the `.p12` or `.cer` file (from `entra-cert.p12` or `entra-cert.pem` above)
6. Enter **Description**: `Telephony Toolbox Production`
7. Click **Add**
8. Note the **Thumbprint** (you'll need this)

#### Get Certificate Thumbprint

```bash
# Extract thumbprint from certificate
openssl x509 -in /etc/telephonytoolbox/entra-cert/entra-cert.pem -noout -fingerprint -sha1 | sed 's/://g' | sed 's/SHA1 Fingerprint=//'
# Output: ABC123DEF456...
```

Copy this thumbprint for environment configuration.

#### Using a Company-Signed Certificate (Recommended for Production)

```bash
# Request certificate from your company CA with:
# - Subject: CN=telephonytoolbox.example.internal
# - Key usage: Digital Signature
# - Extended key usage: Server Authentication, Client Authentication
# - Validity: 2-3 years

# Receive certificate as .pem or .pfx from CA

# Convert .pfx to .pem (if needed)
openssl pkcs12 -in company-cert.pfx -out entra-cert.pem -clcerts -nokeys
openssl pkcs12 -in company-cert.pfx -out entra-key.pem -nocerts -nodes

# Extract thumbprint
openssl x509 -in entra-cert.pem -noout -fingerprint -sha1 | sed 's/://g' | sed 's/SHA1 Fingerprint=//'

# Upload to Azure Portal as above
```

---

### Step 3b: Create Client Secret (Alternative - Development Only)

**Skip this if using Client Certificates above.**

1. Go to **Certificates & secrets** → **Client secrets** tab
2. Click **New client secret**
3. Enter:
   - **Description**: Telephony Toolbox Backend
   - **Expires**: 24 months (or desired lifespan)
4. Click **Add**
5. Copy the **Value** (appears once) → `ENTRA_CLIENT_SECRET`

⚠️ **Important**: Save the secret immediately; it won't be shown again.

**Security Note**: Secrets should only be used in development. For production, prefer certificates.

---

### Step 4: Configure API Permissions

1. Go to **API permissions**
2. Click **Add a permission**
3. Select **Microsoft Graph**
4. Select **Delegated permissions**
5. Search for and add:
   - `User.Read` — Read basic user profile
6. Click **Add permissions**

(Optional but recommended for user provisioning)

---

### Step 5: Add Redirect URI (if needed)

1. Go to **Authentication**
2. Under **Redirect URIs**, verify your callback URL is listed
3. For development, you can add additional URIs:
   - `http://localhost:8000/api/auth/login/entra/callback/`

---

### Step 6: Environment Configuration

#### Option A: Using Client Certificate (Recommended)

```bash
# Application credentials
ENTRA_CLIENT_ID=12345678-1234-1234-1234-123456789012
ENTRA_TENANT_ID=87654321-4321-4321-4321-210987654321
ENTRA_REDIRECT_URI=https://telephonytoolbox.example.internal/api/auth/login/entra/callback/

# Certificate authentication (preferred)
ENTRA_AUTH_METHOD=certificate
ENTRA_CERTIFICATE_PATH=/etc/telephonytoolbox/entra-cert/entra-cert.pem
ENTRA_PRIVATE_KEY_PATH=/etc/telephonytoolbox/entra-cert/entra-key.pem
ENTRA_CERTIFICATE_THUMBPRINT=ABC123DEF456...  # Optional; for validation

# Leave secrets empty
ENTRA_CLIENT_SECRET=
```

**File Permissions** (on RHEL/production):

```bash
# Certificate files readable by app user only
sudo chmod 600 /etc/telephonytoolbox/entra-cert/entra-key.pem
sudo chmod 640 /etc/telephonytoolbox/entra-cert/entra-cert.pem
sudo chown telephonytoolbox:telephonytoolbox /etc/telephonytoolbox/entra-cert/*
```

#### Option B: Using Client Secret (Development Only)

```bash
# Application credentials
ENTRA_CLIENT_ID=12345678-1234-1234-1234-123456789012
ENTRA_TENANT_ID=87654321-4321-4321-4321-210987654321
ENTRA_REDIRECT_URI=https://telephonytoolbox.example.internal/api/auth/login/entra/callback/

# Secret authentication (development only)
ENTRA_AUTH_METHOD=secret
ENTRA_CLIENT_SECRET=your-client-secret-here

# Leave certificate paths empty
ENTRA_CERTIFICATE_PATH=
ENTRA_PRIVATE_KEY_PATH=
ENTRA_CERTIFICATE_THUMBPRINT=
```

---

### Step 7: Certificate Management (If Using Certificates)

#### Monitor Certificate Expiration

```bash
# Check certificate expiration date
openssl x509 -in /etc/telephonytoolbox/entra-cert/entra-cert.pem -noout -dates

# Expected output:
# notBefore=Jun 16 10:00:00 2026 GMT
# notAfter=Jun 16 10:00:00 2028 GMT

# Create monitoring alert (cron job)
# Check every month
0 0 1 * * root openssl x509 -in /etc/telephonytoolbox/entra-cert/entra-cert.pem -noout -checkend 2592000 || echo "Certificate expiring within 30 days" | mail -s "Entra Certificate Expiration Warning" admin@company.com
```

#### Rotate Certificate (Before Expiration)

1. **Generate new certificate** (same commands as Step 3a above)
2. **Upload to Azure Portal**:
   - Go to Certificates & secrets → Certificates
   - Click "Upload certificate"
   - Select new certificate file
   - Click "Add"
3. **Update environment file**:
   ```bash
   sudo cp /etc/telephonytoolbox/entra-cert/entra-cert.pem.old /etc/telephonytoolbox/entra-cert/entra-cert.pem.backup
   sudo cp /etc/telephonytoolbox/entra-cert/entra-cert-new.pem /etc/telephonytoolbox/entra-cert/entra-cert.pem
   ```
4. **Update thumbprint in .env** (if using ENTRA_CERTIFICATE_THUMBPRINT)
5. **Restart application**:
   ```bash
   sudo systemctl restart telephonytoolbox
   ```
6. **Delete old certificate from Azure** (optional, after verification)

#### Verify Certificate is Being Used

```bash
# Check application logs for successful Entra authentication
sudo journalctl -u telephonytoolbox | grep -i entra

# Should see successful token exchange
# If certificate is invalid, you'll see:
# "Certificate validation failed" or "CERTIFICATE_VERIFY_FAILED"
```

---

### Step 8: Troubleshooting Entra (Certificates vs. Secrets)

#### Certificate-Related Issues

1. **"Certificate Verify Failed"**:
   ```
   Error: SSL: CERTIFICATE_VERIFY_FAILED
   ```
   **Causes**:
   - Certificate file corrupted or wrong path
   - Certificate expired
   - Private key doesn't match certificate
   - File permissions prevent reading
   
   **Fix**:
   ```bash
   # Verify certificate is valid
   openssl x509 -in /etc/telephonytoolbox/entra-cert/entra-cert.pem -text -noout
   
   # Verify key matches certificate
   openssl pkey -in /etc/telephonytoolbox/entra-cert/entra-key.pem -pubout -outform pem | openssl dgst -sha256
   openssl x509 -in /etc/telephonytoolbox/entra-cert/entra-cert.pem -pubkey -noout | openssl dgst -sha256
   # Both should output same hash
   
   # Check file permissions
   ls -la /etc/telephonytoolbox/entra-cert/
   # App user should have read access
   ```

2. **"Invalid Certificate Thumbprint"**:
   ```
   Error: Thumbprint mismatch in token validation
   ```
   **Causes**:
   - ENTRA_CERTIFICATE_THUMBPRINT doesn't match uploaded certificate
   - Thumbprint copied incorrectly
   
   **Fix**:
   ```bash
   # Get correct thumbprint
   openssl x509 -in /etc/telephonytoolbox/entra-cert/entra-cert.pem -noout -fingerprint -sha1 | sed 's/://g' | sed 's/SHA1 Fingerprint=//'
   
   # Update .env
   sudo sed -i 's/ENTRA_CERTIFICATE_THUMBPRINT=.*/ENTRA_CERTIFICATE_THUMBPRINT=<correct-thumbprint>/' /etc/telephonytoolbox/backend.env
   
   # Restart
   sudo systemctl restart telephonytoolbox
   ```

3. **"Certificate File Not Found"**:
   ```
   Error: [Errno 2] No such file or directory: '/etc/telephonytoolbox/entra-cert/entra-cert.pem'
   ```
   **Causes**:
   - Wrong path in ENTRA_CERTIFICATE_PATH
   - Certificate file deleted or moved
   
   **Fix**:
   ```bash
   # Verify file exists
   ls -la /etc/telephonytoolbox/entra-cert/
   
   # Check .env has correct paths
   grep ENTRA_CERTIFICATE /etc/telephonytoolbox/backend.env
   
   # If paths wrong, recreate certificates and update .env
   ```

#### Secret-Related Issues (If Not Using Certificates)

1. **"Invalid Client Secret"**:
   ```
   Error: AADSTS7000215: Invalid client secret provided.
   ```
   **Causes**:
   - Secret value copied incorrectly
   - Secret expired or deleted in Azure Portal
   - Different secret for multiple deployments
   
   **Fix**:
   ```bash
   # Go to Azure Portal → Entra ID → App registrations → [App]
   # → Certificates & secrets → Client secrets
   
   # Delete old secret
   # Create new secret
   # Copy value immediately and update .env
   
   sudo sed -i 's/ENTRA_CLIENT_SECRET=.*/ENTRA_CLIENT_SECRET=<new-value>/' /etc/telephonytoolbox/backend.env
   
   # Restart
   sudo systemctl restart telephonytoolbox
   ```

2. **"Secret About to Expire"**:
   - Azure Portal shows warning icon next to secret
   - Create new secret before expiration
   - Update environment and restart

#### General Entra Issues (Both Methods)

3. **"Invalid redirect_uri"**: 
   - Verify exact match (case-sensitive, trailing slash)
   - Check registration in Azure Portal

4. **"Token validation failed"**:
   - Check application logs for detailed error
   - Verify `ENTRA_TENANT_ID` is correct
   - Verify application (client) ID matches `ENTRA_CLIENT_ID`

5. **User not created after login**:
   - Check user has email attribute in Entra
   - Verify email is returned in ID token (usually automatic)

---

### Certificate vs. Secret Security Comparison

| Aspect | Certificate | Secret |
|--------|-------------|--------|
| **Transmission Risk** | ✅ Never transmitted | ⚠️ In environment variable |
| **Storage Risk** | ✅ Private key in file | ⚠️ Plain text in .env |
| **Expiration** | ✅ Auto-enforced by OS/CA | ⚠️ Manual tracking needed |
| **Compromise Impact** | ✅ Limited to cert duration | ⚠️ Indefinite until rotated |
| **Hardware Security** | ✅ Can be HSM-backed | ❌ Not applicable |
| **Audit Trail** | ✅ CA maintains full history | ⚠️ Manual logging only |
| **Operational Complexity** | ⚠️ Requires cert management | ✅ Simple but risky |
| **Compliance** | ✅ Meets strict standards | ⚠️ May not meet requirements |

**Recommendation for Production**: Always use **Client Certificates**. They provide significantly better security and operational visibility.

---

## LDAP Setup

### Active Directory Example

**Prerequisites**: LDAP service account with read permissions

**Configuration**:

```bash
LDAP_SERVER_URI=ldaps://ldap.company.internal:636
LDAP_BIND_DN=cn=ldap-service,cn=users,dc=company,dc=internal
LDAP_BIND_PASSWORD=ServicePassword123!
LDAP_USER_SEARCH_BASE=cn=users,dc=company,dc=internal
LDAP_USER_EMAIL_ATTRIBUTE=mail
LDAP_USER_DISPLAY_NAME_ATTRIBUTE=displayName
LDAP_USER_ENABLED_ATTRIBUTE=
LDAP_GROUP_SEARCH_FILTER=
```

### OpenLDAP Example

**Configuration**:

```bash
LDAP_SERVER_URI=ldap://ldap.company.internal:389
LDAP_BIND_DN=cn=admin,dc=company,dc=internal
LDAP_BIND_PASSWORD=AdminPassword
LDAP_USER_SEARCH_BASE=ou=people,dc=company,dc=internal
LDAP_USER_EMAIL_ATTRIBUTE=mail
LDAP_USER_DISPLAY_NAME_ATTRIBUTE=cn
LDAP_USER_ENABLED_ATTRIBUTE=
LDAP_GROUP_SEARCH_FILTER=
```

### Group-Based Access Control

Restrict login to members of specific group:

```bash
# Active Directory: Users in "TelephonyToolbox" group
LDAP_GROUP_SEARCH_FILTER=(&(mail=%email)(memberOf=cn=TelephonyToolbox,ou=Groups,dc=company,dc=internal))

# OpenLDAP: Users in "telephony" posixGroup
LDAP_GROUP_SEARCH_FILTER=(&(mail=%email)(cn=telephony))
```

The `%email` placeholder is automatically escaped to prevent LDAP injection.

---

## User Roles and Provisioning

### User Roles

| Role | Permissions |
|------|-------------|
| **Standard User** | View assigned diversions, update CFA destinations |
| **App Admin** | User/group management, diversion CRUD, audit access |

### User States

| State | Meaning | Can Log In? |
|-------|---------|-----------|
| `is_active=true` | User provisioned, enabled | Yes |
| `is_active=false` | User disabled by admin | No |
| `is_local=true` | Local credentials (password set) | Via local auth |
| `is_local=false` | External auth only (Entra/LDAP) | Via external provider |

### Provisioning Flows

#### Manual Provisioning (App Admin)

```bash
# Create new user
POST /api/admin/users/
{
  "email": "newuser@company.com",
  "display_name": "New User",
  "role": "standard_user"
}

# Add to group(s)
PATCH /api/admin/groups/{group_id}/
{
  "member_ids": ["user1-uuid", "user2-uuid", "newuser-uuid"]
}
```

#### Automatic Provisioning (External Auth)

On first login via Entra or LDAP:
1. User authenticates with external provider
2. Backend creates local user record if not exists
3. User assigned `role=standard_user` by default
4. App Admin must manually add to groups

#### Just-In-Time (JIT) Provisioning

When user logs in via LDAP/Entra and doesn't exist in app:
1. User is automatically created with:
   - `email` from provider
   - `display_name` from provider attributes
   - `is_active=true`
   - `role=standard_user` (default)
2. App Admin can change role/groups after initial login
3. User can immediately access assigned diversions (or none if not yet added to groups)

---

## Session Management

### Session Configuration

- **Backend**: Django session framework (database-backed)
- **Cookie**: `sessionid` set as `Set-Cookie` header
- **Expiration**: Django default (2 weeks); configurable via `SESSION_COOKIE_AGE` in settings
- **Security**:
  - `HttpOnly` — Prevents JavaScript access (XSS mitigation)
  - `Secure` — Transmitted only over HTTPS (production)
  - `SameSite=Strict` — CSRF protection

### Session Lifecycle

```
User logs in
  ↓
Backend creates session record in database
  ↓
Backend sets Set-Cookie: sessionid=xyz...
  ↓
Browser stores cookie; includes in subsequent requests
  ↓
Backend validates sessionid on each request
  ↓
User logs out or cookie expires
  ↓
Session destroyed; cookie cleared
```

### CSRF Protection

All state-changing requests (POST, PATCH, DELETE) require CSRF token:

```javascript
// Get CSRF token from cookie or meta tag
const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;

// Include in request header
fetch('/api/diversions/123/update-destination/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-CSRFToken': csrfToken
  },
  body: JSON.stringify({ destination: '+61299998888' })
});
```

---

## Multi-Factor Authentication (MFA)

**Backend**: No native MFA implementation.

**Recommendations**:
- Use **Entra conditional access** to enforce MFA for cloud users
- Use **LDAP/Active Directory** with enforced MFA via authentication infrastructure
- Use **nginx**-level authentication (reverse proxy MFA) if desired

---

## Account Recovery & Password Reset

### Local Users

Password reset via admin:

```bash
# App Admin changes user password
PATCH /api/admin/users/{user_id}/
{
  "password": "NewTemporaryPassword123!"
}
```

Currently no self-service password reset (can be added as future feature).

### Entra Users

Password reset via **azure.microsoft.com** (user self-service) or **Entra Admin** dashboard.

### LDAP Users

Password reset via LDAP directory management tools (Active Directory Users & Computers, etc.).

---

## Audit Trail

All authentication events are logged to `AuditEvent` table:

| Event | Details |
|-------|---------|
| `auth.login.success` | User successfully authenticated |
| `auth.login.failure` | Invalid credentials or unavailable provider |
| `auth.logout.success` | User logged out |

**Audit queries**:

```bash
# Export last 30 days of auth events
GET /api/admin/audit/?limit=1000&event_type=auth.login.success

# Export to CSV
GET /api/admin/audit/export.csv?event_type=auth.login.success
```

---

## Security Best Practices

1. **Use HTTPS**: Always use HTTPS in production; redirects HTTP to HTTPS
2. **Secure Secrets**: Never commit passwords/secrets to repository
3. **Token Rotation**: Rotate Entra client secrets, LDAP service account passwords periodically
4. **TLS Verification**: Enable `CUCM_AXL_VERIFY_TLS=true` and `LDAP_SERVER_URI=ldaps://` in production
5. **Audit Review**: Regularly review audit logs for suspicious login activity
6. **Rate Limiting**: Implement at nginx level to prevent brute-force attacks
7. **Account Lockout**: Consider implementing failed login attempt tracking (future feature)

---

## Troubleshooting Authentication Issues

### User Cannot Log In

1. **Check `is_active` status**:
   ```bash
   python backend/manage.py shell
   from accounts.models import User
   User.objects.get(email='user@company.com').is_active
   ```
   If `False`, enable: `User.objects.filter(email='user@company.com').update(is_active=True)`

2. **Check external provider**:
   - Entra: Verify user exists in Azure AD
   - LDAP: Verify user exists in LDAP directory

3. **Check logs**:
   ```bash
   tail -f /var/log/telephonytoolbox/application.log | grep auth
   ```

4. **Check audit events**:
   ```bash
   GET /api/admin/audit/?actor_email=user@company.com&event_type=auth.login.failure
   ```

### Session Expires Too Quickly

1. **Check session timeout setting** (`SESSION_COOKIE_AGE` in Django settings)
2. **Check cookie configuration** (HttpOnly, Secure, SameSite)
3. **Check client-side clock** (browser system time must be accurate)

### CSRF Token Mismatch

1. **Verify `CSRF_TRUSTED_ORIGINS`** includes frontend URL
2. **Verify frontend includes `X-CSRFToken` header** on POST/PATCH/DELETE
3. **Check cookie settings**: CSRF token must be in cookie

---

## API Authentication Examples

### JavaScript/Fetch

```javascript
// Login
const loginResponse = await fetch('/api/auth/login/local/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@company.com',
    password: 'password123'
  }),
  credentials: 'include'  // Include cookies
});

// Subsequent requests
const diversionsResponse = await fetch('/api/diversions/', {
  credentials: 'include'  // Auto-include sessionid cookie
});
```

### Python/Requests

```python
import requests

session = requests.Session()

# Login
response = session.post('http://localhost:8000/api/auth/login/local/', json={
    'email': 'user@company.com',
    'password': 'password123'
})

# Get CSRF token from cookies
csrf_token = session.cookies.get('csrftoken')

# Subsequent requests auto-include sessionid
response = session.get('http://localhost:8000/api/diversions/')
```

### cURL

```bash
# Login and save cookies
curl -c cookies.txt -X POST http://localhost:8000/api/auth/login/local/ \
  -H "Content-Type: application/json" \
  -d '{"email":"user@company.com","password":"password123"}'

# Use cookies in subsequent requests
curl -b cookies.txt http://localhost:8000/api/diversions/
```

---

## Future Enhancements

Potential authentication improvements for future releases:

- **Self-service password reset** (email link)
- **Account lockout** after failed login attempts
- **WebAuthn/FIDO2** support (passwordless)
- **Device-based conditional access**
- **Audit dashboard** for login analytics
