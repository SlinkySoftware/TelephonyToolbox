from pathlib import Path

from telephony_toolbox.env import env_bool, env_int, env_list, env_str

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BASE_DIR.parent

SECRET_KEY = env_str('DJANGO_SECRET_KEY', 'telephony-toolbox-dev-secret-key')
DEBUG = env_bool('DJANGO_DEBUG', True)
ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1')

AUTH_MODE = env_str('AUTH_MODE', 'entra').lower()
LOCAL_AUTH_ENABLED = env_bool('LOCAL_AUTH_ENABLED', True)

CUCM_AXL_HOST = env_str('CUCM_AXL_HOST', '')
CUCM_AXL_USERNAME = env_str('CUCM_AXL_USERNAME', '')
CUCM_AXL_PASSWORD = env_str('CUCM_AXL_PASSWORD', '')
CUCM_AXL_VERSION = env_str('CUCM_AXL_VERSION', '14')
CUCM_ROUTE_PARTITION = env_str('CUCM_ROUTE_PARTITION', 'INTERNAL')
CUCM_AXL_VERIFY_TLS = env_bool('CUCM_AXL_VERIFY_TLS', True)

AUDIT_RETENTION_DAYS = env_int('AUDIT_RETENTION_DAYS', 90)

ENTRA_CLIENT_ID = env_str('ENTRA_CLIENT_ID', '')
ENTRA_CLIENT_SECRET = env_str('ENTRA_CLIENT_SECRET', '')
ENTRA_TENANT_ID = env_str('ENTRA_TENANT_ID', '')
ENTRA_REDIRECT_URI = env_str('ENTRA_REDIRECT_URI', '')

LDAP_SERVER_URI = env_str('LDAP_SERVER_URI', '')
LDAP_BIND_DN = env_str('LDAP_BIND_DN', '')
LDAP_BIND_PASSWORD = env_str('LDAP_BIND_PASSWORD', '')
LDAP_USER_SEARCH_BASE = env_str('LDAP_USER_SEARCH_BASE', '')
LDAP_USER_EMAIL_ATTRIBUTE = env_str('LDAP_USER_EMAIL_ATTRIBUTE', 'mail')
LDAP_USER_DISPLAY_NAME_ATTRIBUTE = env_str('LDAP_USER_DISPLAY_NAME_ATTRIBUTE', 'displayName')
LDAP_USER_ENABLED_ATTRIBUTE = env_str('LDAP_USER_ENABLED_ATTRIBUTE', '')

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'django_filters',
    'rest_framework',
    'accounts.apps.AccountsConfig',
    'access_groups.apps.AccessGroupsConfig',
    'audit.apps.AuditConfig',
    'cucm.apps.CucmConfig',
    'dialplan.apps.DialplanConfig',
    'diversions.apps.DiversionsConfig',
    'health.apps.HealthConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'telephony_toolbox.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
            ],
        },
    },
]

WSGI_APPLICATION = 'telephony_toolbox.wsgi.application'

if env_str('DATABASE_NAME', ''):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'HOST': env_str('DATABASE_HOST', 'localhost'),
            'PORT': env_int('DATABASE_PORT', 5432),
            'NAME': env_str('DATABASE_NAME'),
            'USER': env_str('DATABASE_USER'),
            'PASSWORD': env_str('DATABASE_PASSWORD', ''),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-au'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

AUTH_USER_MODEL = 'accounts.User'
AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.ModelBackend']

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'EXCEPTION_HANDLER': 'telephony_toolbox.api.api_exception_handler',
}

SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = 'Lax'

REQUIRED_CONFIGURATION = {
    'database': ['DATABASE_NAME', 'DATABASE_USER', 'DATABASE_PASSWORD', 'DATABASE_HOST'],
    'cucm': ['CUCM_AXL_HOST', 'CUCM_AXL_USERNAME', 'CUCM_AXL_PASSWORD', 'CUCM_AXL_VERSION'],
    'auth_entra': ['ENTRA_CLIENT_ID', 'ENTRA_CLIENT_SECRET', 'ENTRA_TENANT_ID', 'ENTRA_REDIRECT_URI'],
    'auth_ldap': ['LDAP_SERVER_URI', 'LDAP_BIND_DN', 'LDAP_BIND_PASSWORD', 'LDAP_USER_SEARCH_BASE'],
}
