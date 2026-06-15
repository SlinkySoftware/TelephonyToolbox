import os

from django.conf import settings
from django.db import connections

from cucm.exceptions import CucmAuthenticationError, CucmUnavailableError
from cucm.factory import get_cucm_client


def _database_status():
    try:
        with connections['default'].cursor() as cursor:
            cursor.execute('SELECT 1')
        return {'status': 'ok'}
    except Exception as exc:
        return {'status': 'failure', 'message': str(exc)}


def _cucm_status():
    if not settings.CUCM_AXL_HOST or not settings.CUCM_AXL_USERNAME or not settings.CUCM_AXL_PASSWORD:
        return {
            'status': 'failure',
            'host': 'missing',
            'version': settings.CUCM_AXL_VERSION,
            'route_partition': settings.CUCM_ROUTE_PARTITION,
            'message': 'CUCM configuration is incomplete.',
        }

    try:
        result = get_cucm_client().health_check()
        return {
            'status': result.status,
            'host': 'configured',
            'version': result.version or settings.CUCM_AXL_VERSION,
            'route_partition': settings.CUCM_ROUTE_PARTITION,
        }
    except CucmAuthenticationError as exc:
        return {
            'status': 'failure',
            'host': 'configured',
            'version': settings.CUCM_AXL_VERSION,
            'route_partition': settings.CUCM_ROUTE_PARTITION,
            'message': str(exc),
        }
    except CucmUnavailableError as exc:
        return {
            'status': 'failure',
            'host': 'configured',
            'version': settings.CUCM_AXL_VERSION,
            'route_partition': settings.CUCM_ROUTE_PARTITION,
            'message': str(exc),
        }


def _auth_status():
    provider_key = 'auth_entra' if settings.AUTH_MODE == 'entra' else 'auth_ldap'
    required = settings.REQUIRED_CONFIGURATION[provider_key]
    missing = [name for name in required if not os.getenv(name)]
    return {
        'mode': settings.AUTH_MODE,
        'status': 'ok' if not missing else 'failure',
        'local_auth_enabled': settings.LOCAL_AUTH_ENABLED,
        'missing': missing,
    }


def _required_env_status():
    common = [
        'DJANGO_SECRET_KEY',
        'DATABASE_HOST',
        'DATABASE_NAME',
        'DATABASE_USER',
        'DATABASE_PASSWORD',
        'CUCM_AXL_HOST',
        'CUCM_AXL_USERNAME',
        'CUCM_AXL_PASSWORD',
        'CUCM_AXL_VERSION',
    ]
    if settings.AUTH_MODE == 'entra':
        common.extend(settings.REQUIRED_CONFIGURATION['auth_entra'])
    else:
        common.extend(settings.REQUIRED_CONFIGURATION['auth_ldap'])

    missing = sorted({name for name in common if not os.getenv(name)})
    return {'required_variables_present': not missing, 'missing': missing}


def build_admin_health_report():
    return {
        'application': {'status': 'ok', 'version': '0.1.0'},
        'database': _database_status(),
        'cucm': _cucm_status(),
        'auth': _auth_status(),
        'environment': _required_env_status(),
    }