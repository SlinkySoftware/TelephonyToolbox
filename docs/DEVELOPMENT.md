# Telephony Toolbox Development Guide

Complete setup and development workflow for Telephony Toolbox contributors.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Running Services](#running-services)
4. [Testing](#testing)
5. [Code Organization](#code-organization)
6. [Common Development Tasks](#common-development-tasks)
7. [Debugging](#debugging)
8. [Git Workflow](#git-workflow)

## Prerequisites

- **Python**: 3.10+ (check with `python3 --version`)
- **Node.js**: 24+ (check with `node --version`)
- **npm**: 11+ (check with `npm --version`)
- **Git**: 2.0+ (check with `git --version`)
- **PostgreSQL** (optional; SQLite used by default for development)

**macOS**:
```bash
brew install python@3.11 node
```

**Ubuntu/Debian**:
```bash
sudo apt install python3 python3-venv python3-pip nodejs npm
```

**Windows**: Use WSL 2 or native installations via installers.

---

## Initial Setup

### Step 1: Clone Repository

```bash
git clone git@github.com:SlinkySoftware/TelephonyToolbox.git
cd TelephonyToolbox
```

### Step 2: Create Environment File

```bash
cp scripts/env.example .env
```

Edit `.env` for your environment:

```bash
# Core Django
DJANGO_SECRET_KEY=dev-secret-key
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_DEBUG=true
DJANGO_LOG_LEVEL=DEBUG

# Database (use SQLite by default; PostgreSQL optional)
# Leave DATABASE_NAME empty for SQLite
DATABASE_NAME=

# Authentication
AUTH_MODE=entra
LOCAL_AUTH_ENABLED=true

# Leave auth provider secrets empty; use local login during development
ENTRA_CLIENT_ID=
ENTRA_CLIENT_SECRET=
ENTRA_TENANT_ID=
ENTRA_REDIRECT_URI=

# Leave CUCM empty if not available
CUCM_AXL_HOST=
```

### Step 3: Setup Python Virtual Environment

```bash
# Create virtual environment
python3 -m venv .venv

# Activate
source .venv/bin/activate  # macOS/Linux
# OR
.venv\Scripts\activate  # Windows

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r backend/requirements.txt
```

### Step 4: Install Frontend Dependencies

```bash
npm --prefix frontend install
```

### Step 5: Database Setup

```bash
# Run migrations
python backend/manage.py migrate

# Create bootstrap app admin (optional but helpful for testing)
python backend/manage.py bootstrap_local_app_admin \
  --email admin@example.com \
  --display-name "Dev Admin" \
  --password 'ChangeMe123!'

# Create some test data (optional)
python backend/manage.py shell << 'EOF'
from access_groups.models import AccessGroup
from accounts.models import User

# Create test group
group = AccessGroup.objects.create(
    name='Test Group',
    description='Test group for development'
)
print(f'Created group: {group.id}')
EOF
```

### Step 6: Verify Setup

```bash
# Test backend
python backend/manage.py runserver --nothreading
# Should see "Starting development server at http://127.0.0.1:8000/"

# In new terminal, test frontend
npm --prefix frontend run dev
# Should see "ready in 500ms" or similar

# Check http://localhost:9000
# Should see login page
```

---

## Running Services

### Backend Development Server

```bash
# Terminal 1
source .venv/bin/activate
python backend/manage.py runserver 0.0.0.0:8000
```

**Accessible at**: `http://localhost:8000/api/`

**Features**:
- Auto-reload on code changes
- Full traceback on errors
- Debugger available with `pdb`

### Frontend Development Server

```bash
# Terminal 2
npm --prefix frontend run dev
```

**Accessible at**: `http://localhost:9000`

**Features**:
- Hot module reload (HMR) — changes reflected immediately
- Proxies `/api/*` to `http://localhost:8000` (see `quasar.conf.js`)
- Development-only error overlay

### Database (if using PostgreSQL)

```bash
# Option 1: Local PostgreSQL
brew install postgresql@15  # macOS
brew services start postgresql@15

# Create user and database
createuser telephonytoolbox
createdb -O telephonytoolbox telephonytoolbox

# Update .env
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=telephonytoolbox
DATABASE_USER=telephonytoolbox
DATABASE_PASSWORD=

# Option 2: Docker
docker run --name telephonytoolbox-postgres \
  -e POSTGRES_USER=telephonytoolbox \
  -e POSTGRES_DB=telephonytoolbox \
  -p 5432:5432 \
  -d postgres:15
```

---

## Testing

### Backend Tests

Run pytest from repository root:

```bash
# All tests
pytest

# Specific test file
pytest backend/accounts/tests/test_models.py

# Specific test class
pytest backend/accounts/tests/test_models.py::TestUserModel

# Specific test function
pytest backend/accounts/tests/test_models.py::TestUserModel::test_user_creation

# With verbose output
pytest -v

# With coverage
pytest --cov=backend --cov-report=html
# Open htmlcov/index.html in browser
```

**Test Structure**:
```
backend/
  accounts/tests/
    __init__.py
    test_models.py
    test_views.py
    test_serializers.py
```

### Frontend Validation

```bash
# Formatting and lint
npm --prefix frontend run lint:check

# Production build
npm --prefix frontend run build
```

There is currently no dedicated frontend unit test script in `frontend/package.json`; build and lint checks are the authoritative frontend validation commands.

### Manual Testing Checklist

**Authentication**:
- [ ] Local login works
- [ ] Invalid credentials rejected
- [ ] Session persists across page refresh
- [ ] Logout destroys session

**Diversions**:
- [ ] Standard user sees only assigned diversions
- [ ] App Admin sees all diversions
- [ ] Destination validation works (test various formats)
- [ ] Update destination writes to local cache
- [ ] Refresh reads from cache

**Admin Functions**:
- [ ] User CRUD works
- [ ] Group CRUD works
- [ ] Diversion CRUD works
- [ ] Audit log displays events

**Edge Cases**:
- [ ] CUCM unavailable → UI shows "unavailable", edits blocked
- [ ] Invalid destination → validation error displayed
- [ ] Session expires → redirect to login
- [ ] Permission denied → error message or redirect

---

## Code Organization

### Backend Structure

```
backend/
  accounts/                    # User management
    migrations/
    tests/                    # Unit & integration tests
    __init__.py
    apps.py                  # App configuration
    models.py                # User, AuthSource, UserRole
    serializers.py          # JSON serializers for API
    views.py                # API views (auth, CRUD)
    permissions.py          # Permission classes (IsAppAdmin, etc.)
    services.py             # Business logic (auth flows, LDAP, Entra)
    urls.py                 # URL routing

  access_groups/              # Group management
    models.py               # AccessGroup, UserGroupMembership
    serializers.py
    views.py
    urls.py
    tests/

  diversions/                 # Diversion CRUD & updates
    models.py               # Diversion model
    serializers.py
    views.py
    permissions.py          # visible_diversions_queryset
    services.py             # DiversionUpdateService
    urls.py
    tests/

  audit/                      # Audit event logging
    models.py               # AuditEvent
    serializers.py
    views.py
    services.py             # AuditService.record_event()
    urls.py
    tests/

  cucm/                       # CUCM AXL integration
    __init__.py
    client.py               # Abstract base class
    client_zeep.py         # Zeep SOAP client (main)
    client_14.py           # CUCM 14 specific
    client_105.py          # CUCM 10.5 legacy
    factory.py             # get_cucm_client()
    schemas.py             # Response data classes
    exceptions.py          # CucmError, CucmUnavailableError
    directory_numbers.py   # Normalization, pattern handling
    tests/

  dialplan/                   # Phone number validation
    validators.py           # validate_and_normalise_destination()
    tests/

  health/                     # Health check endpoints
    views.py
    services.py
    urls.py

  telephony_toolbox/          # Django configuration
    __init__.py
    settings.py             # Django settings
    urls.py                 # URL routing root
    wsgi.py
    asgi.py
    api.py                  # API exception handler
    env.py                  # Environment variable loading
    models.py              # Base models (UUIDModel, UUIDTimestampedModel)

  conftest.py                 # Pytest fixtures
  manage.py                   # Django management script
  requirements.txt            # Python dependencies
  db.sqlite3                  # Development database (git-ignored)
```

### Frontend Structure

```
frontend/
  src/
    pages/
      AuthLoginPage.vue       # Login form
      MyDiversionsPage.vue   # Standard user dashboard
      EditDiversionPage.vue  # Diversion editor
      AdminDashboardPage.vue
      AdminUsersPage.vue
      AdminGroupsPage.vue
      AdminDiversionsPage.vue
      AdminAuditPage.vue
      AdminHealthPage.vue
      ErrorNotFound.vue

    components/
      DiversionForm.vue       # Reusable form
      DiversionCard.vue
      UserTable.vue
      AuditTable.vue
      # etc.

    stores/                    # Pinia state management
      session.js             # User, auth state
      diversions.js          # Diversion list, detail
      audit.js              # Audit events

    services/
      api.js                # API client
      validation.js         # Destination validation logic

    router/
      index.js              # Router setup
      routes.js             # Route definitions

    layouts/
      MainLayout.vue        # App shell

    assets/
    css/
    boot/

  public/
    icons/
    images/

  quasar.conf.js           # Quasar build config
  jsconfig.json            # JS compiler config
  eslint.config.js         # Linter config
  package.json
  pnpm-workspace.yaml
```

---

## Common Development Tasks

### Adding a New Endpoint

**Example**: Add `/api/diversions/<id>/status/` to show live CFA status.

1. **Add view** in `diversions/views.py`:
```python
class DiversionStatusView(APIView):
    def get(self, request, diversion_id):
        diversion = get_object_or_404(visible_diversions_queryset(request.user), pk=diversion_id)
        # Fetch from CUCM
        try:
            dn = get_cucm_client().get_directory_number(...)
            return Response({
                'diversion_id': str(diversion.id),
                'live_destination': dn.call_forward_all_destination,
                'cached_destination': diversion.cached_current_destination,
            })
        except CucmUnavailableError:
            return Response({'message': 'CUCM unavailable'}, status=503)
```

2. **Add URL** in `diversions/urls.py`:
```python
path('diversions/<uuid:diversion_id>/status/', DiversionStatusView.as_view(), name='diversion-status'),
```

3. **Test** (add to `diversions/tests/test_views.py`):
```python
def test_diversion_status(self):
    response = self.client.get(f'/api/diversions/{self.diversion.id}/status/')
    self.assertEqual(response.status_code, 200)
    self.assertIn('live_destination', response.data)
```

4. **Frontend integration** — Call from page component:
```javascript
// In page component
const response = await fetch(`/api/diversions/${id}/status/`);
const data = await response.json();
this.liveDestination = data.live_destination;
```

### Adding a Model Field

**Example**: Add `notes` field to Diversion.

1. **Add field** in `diversions/models.py`:
```python
class Diversion(UUIDTimestampedModel):
    # ... existing fields ...
    notes = models.TextField(blank=True, default='')
```

2. **Create migration**:
```bash
python backend/manage.py makemigrations diversions
python backend/manage.py migrate
```

3. **Update serializer** in `diversions/serializers.py`:
```python
class DiversionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Diversion
        fields = ['diversion_id', 'name', 'notes', ...]
```

4. **Update views** to accept/return field (if needed).

### Running Code Quality Checks

```bash
# Format code
autopep8 --in-place --aggressive backend/**/*.py

# Linting
flake8 backend/

# Type checking (if mypy configured)
mypy backend/

# Frontend linting
npm --prefix frontend run lint
```

---

## Debugging

### Backend Debugging with pdb

```python
# In backend code
def update_destination(self, user, diversion, destination):
    print(f"Updating diversion {diversion.id} with {destination}")
    breakpoint()  # Pause here
    # ... continue ...
```

When code hits `breakpoint()`:
```
> /path/to/file.py(123)update_destination()
-> next_line()
(Pdb) p destination
'+61299998888'
(Pdb) c  # Continue
```

### Frontend Debugging with Browser DevTools

```javascript
// In frontend component
methods: {
  async updateDiversion() {
    debugger;  // Pause here
    const response = await fetch(...);
  }
}
```

Browser DevTools: F12 → Sources tab → step through code.

### Logs

**Backend logs**:
```bash
tail -f backend/logs/telephony_toolbox.log
# Or if logging to console (DEBUG mode):
# Appears in terminal running `runserver`
```

**Frontend logs**:
```bash
# Browser console: F12 → Console
# Vue DevTools extension: F12 → Vue tab (if installed)
```

### Testing CUCM Integration

If you have a test CUCM environment:

```bash
# Update .env
CUCM_AXL_HOST=test-cucm.example.internal
CUCM_AXL_USERNAME=axl-user
CUCM_AXL_PASSWORD=password
CUCM_AXL_VERSION=14
CUCM_AXL_VERIFY_TLS=false  # If using self-signed cert
CUCM_ROUTE_PARTITION=INTERNAL

# Test in shell
python backend/manage.py shell
>>> from cucm.factory import get_cucm_client
>>> client = get_cucm_client()
>>> client.health_check()
CucmHealthResult(available=True, ...)
```

---

## Git Workflow

### Branches

- **main** — Stable, production-ready code
- **feature/*** — Feature branches (e.g., `feature/ldap-auth`)
- **bugfix/*** — Bug fix branches (e.g., `bugfix/validation-error`)
- **docs/*** — Documentation updates

### Typical Workflow

```bash
# Create feature branch
git checkout -b feature/new-feature

# Make changes
# Test locally
pytest
npm --prefix frontend run lint

# Commit
git add .
git commit -m "Add new feature

- Describe what the feature does
- Bullet points for clarity"

# Push
git push origin feature/new-feature

# Create pull request on GitHub
# Code review
# Address feedback
# Merge to main
```

### Pre-Commit Checks

Before committing, run:

```bash
# Backend
pytest backend/
flake8 backend/

# Frontend
npm --prefix frontend run lint
```

**Tip**: Set up pre-commit hooks to automate this (see `setup-pre-commit` skill).

---

## Performance Development

### Database Query Analysis

```python
# In Django shell or views
from django.test.utils import override_settings
from django.db import connection, reset_queries

@override_settings(DEBUG=True)
def my_view(request):
    reset_queries()
    # ... your code ...
    print(len(connection.queries))  # Number of queries
    for query in connection.queries:
        print(query['sql'], query['time'])  # SQL and time
```

### Frontend Performance

```bash
# Build and analyze
npm --prefix frontend run build
npm --prefix frontend install --save-dev webpack-bundle-analyzer
```

### Load Testing (if needed)

```bash
# Install locust
pip install locust

# Create loadtest.py
# Run: locust -f loadtest.py
```

---

## Troubleshooting

### Port Already in Use

```bash
# Find process on port 8000
lsof -i :8000

# Kill process
kill -9 <PID>
```

### Virtual Environment Issues

```bash
# Recreate venv
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

### Database Locked (SQLite)

```bash
# Remove lock file
rm backend/db.sqlite3-wal backend/db.sqlite3-shm

# Restart migrations
python backend/manage.py migrate
```

### Module Not Found

```bash
# Ensure venv is activated
source .venv/bin/activate

# Reinstall dependencies
pip install -r backend/requirements.txt --force-reinstall
```

---

## Documentation

- [README.md](../README.md) — Project overview
- [ARCHITECTURE.md](ARCHITECTURE.md) — System design
- [API_SPECIFICATION.md](API_SPECIFICATION.md) — API reference
- [CONFIGURATION.md](CONFIGURATION.md) — Environment setup
- [AUTHENTICATION.md](AUTHENTICATION.md) — Auth flows
- [DEPLOYMENT.md](DEPLOYMENT.md) — Production deployment

---

## Getting Help

- **Code questions**: Check existing code and comments
- **API questions**: See `API_SPECIFICATION.md`
- **Architecture questions**: See `ARCHITECTURE.md`
- **Auth questions**: See `AUTHENTICATION.md`
- **Stuck**: Open an issue or ask team lead
