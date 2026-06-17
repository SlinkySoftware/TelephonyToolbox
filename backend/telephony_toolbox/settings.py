# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

from pathlib import Path
import sys

from telephony_toolbox.env import env_bool, env_int, env_list, env_str, load_env_file

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BASE_DIR.parent

load_env_file(REPO_ROOT / '.env')


def _default_external_auth_name(auth_mode):
    return {
        'entra': 'Entra',
        'ldap': 'LDAP',
        'oidc': 'OpenID Connect',
    }.get(auth_mode, 'External Sign In')

SECRET_KEY = env_str('DJANGO_SECRET_KEY', 'telephony-toolbox-dev-secret-key')
DEBUG = env_bool('DJANGO_DEBUG', True)
ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1')

if DEBUG or 'runserver' in sys.argv:
    # Quasar/Vite proxy and local tooling can vary host headers in dev.
    for host in ('localhost', '127.0.0.1', '0.0.0.0', '[::1]'):
        if host not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(host)

AUTH_MODE = env_str('AUTH_MODE', 'entra').lower()
LOCAL_AUTH_ENABLED = env_bool('LOCAL_AUTH_ENABLED', True)
EXTERNAL_AUTH_NAME = env_str('EXTERNAL_AUTH_NAME', _default_external_auth_name(AUTH_MODE)).strip() or _default_external_auth_name(AUTH_MODE)

CUCM_AXL_HOST = env_str('CUCM_AXL_HOST', '')
CUCM_AXL_USERNAME = env_str('CUCM_AXL_USERNAME', '')
CUCM_AXL_PASSWORD = env_str('CUCM_AXL_PASSWORD', '')
CUCM_AXL_VERSION = env_str('CUCM_AXL_VERSION', '14')
CUCM_ROUTE_PARTITION = env_str('CUCM_ROUTE_PARTITION', 'INTERNAL')
CUCM_AXL_VERIFY_TLS = env_bool('CUCM_AXL_VERIFY_TLS', True)

AUDIT_RETENTION_DAYS = env_int('AUDIT_RETENTION_DAYS', 90)

LOG_FILE = Path(env_str('DJANGO_LOG_FILE', str(BASE_DIR / 'logs' / 'telephony_toolbox.log')))
LOG_LEVEL = env_str('DJANGO_LOG_LEVEL', 'INFO').upper()
try:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
except OSError:
    # If the file path is invalid or not writable, keep startup alive with console logs.
    LOG_FILE = None

ENTRA_CLIENT_ID = env_str('ENTRA_CLIENT_ID', '')
ENTRA_CLIENT_SECRET = env_str('ENTRA_CLIENT_SECRET', '')
ENTRA_TENANT_ID = env_str('ENTRA_TENANT_ID', '')
ENTRA_REDIRECT_URI = env_str('ENTRA_REDIRECT_URI', '')

OIDC_CLIENT_ID = env_str('OIDC_CLIENT_ID', '')
OIDC_CLIENT_SECRET = env_str('OIDC_CLIENT_SECRET', '')
OIDC_METADATA_URL = env_str('OIDC_METADATA_URL', '')
OIDC_REDIRECT_URI = env_str('OIDC_REDIRECT_URI', '')
OIDC_SCOPES = env_str('OIDC_SCOPES', 'openid profile email')
OIDC_EMAIL_CLAIM = env_str('OIDC_EMAIL_CLAIM', 'email')
OIDC_USERNAME_CLAIM = env_str('OIDC_USERNAME_CLAIM', 'preferred_username')
OIDC_DISPLAY_NAME_CLAIM = env_str('OIDC_DISPLAY_NAME_CLAIM', 'name')

LDAP_SERVER_URI = env_str('LDAP_SERVER_URI', '')
LDAP_BIND_DN = env_str('LDAP_BIND_DN', '')
LDAP_BIND_PASSWORD = env_str('LDAP_BIND_PASSWORD', '')
LDAP_USER_SEARCH_BASE = env_str('LDAP_USER_SEARCH_BASE', '')
LDAP_USER_EMAIL_ATTRIBUTE = env_str('LDAP_USER_EMAIL_ATTRIBUTE', 'mail')
LDAP_USER_DISPLAY_NAME_ATTRIBUTE = env_str('LDAP_USER_DISPLAY_NAME_ATTRIBUTE', 'displayName')
LDAP_USER_ENABLED_ATTRIBUTE = env_str('LDAP_USER_ENABLED_ATTRIBUTE', '')
LDAP_GROUP_SEARCH_FILTER = env_str('LDAP_GROUP_SEARCH_FILTER', '')

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

SESSION_COOKIE_SECURE = not DEBUG and env_bool('SESSION_COOKIE_SECURE', True)
SESSION_COOKIE_HTTPONLY = env_bool('SESSION_COOKIE_HTTPONLY', True)
SESSION_COOKIE_SAMESITE = env_str('SESSION_COOKIE_SAMESITE', 'Lax')
CSRF_COOKIE_SECURE = not DEBUG and env_bool('CSRF_COOKIE_SECURE', True)
CSRF_COOKIE_HTTPONLY = env_bool('CSRF_COOKIE_HTTPONLY', False)
CSRF_COOKIE_SAMESITE = env_str('CSRF_COOKIE_SAMESITE', 'Lax')
CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS', '')

REQUIRED_CONFIGURATION = {
    'database': ['DATABASE_NAME', 'DATABASE_USER', 'DATABASE_PASSWORD', 'DATABASE_HOST'],
    'cucm': ['CUCM_AXL_HOST', 'CUCM_AXL_USERNAME', 'CUCM_AXL_PASSWORD', 'CUCM_AXL_VERSION'],
    'auth_entra': ['ENTRA_CLIENT_ID', 'ENTRA_CLIENT_SECRET', 'ENTRA_TENANT_ID', 'ENTRA_REDIRECT_URI'],
    'auth_oidc': ['OIDC_CLIENT_ID', 'OIDC_CLIENT_SECRET', 'OIDC_METADATA_URL', 'OIDC_REDIRECT_URI'],
    'auth_ldap': ['LDAP_SERVER_URI', 'LDAP_BIND_DN', 'LDAP_BIND_PASSWORD', 'LDAP_USER_SEARCH_BASE'],
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(asctime)s %(levelname)s %(name)s %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(LOG_FILE) if LOG_FILE else str(BASE_DIR / 'telephony_toolbox.log'),
            'maxBytes': env_int('DJANGO_LOG_MAX_BYTES', 5 * 1024 * 1024),
            'backupCount': env_int('DJANGO_LOG_BACKUP_COUNT', 5),
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': LOG_LEVEL,
    },
    'loggers': {
        'django.request': {
            'handlers': ['console', 'file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'telephony_toolbox': {
            'handlers': ['console', 'file'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
    },
}
