# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

"""Runtime activation of the read-only AudioCodes source connection.

The source profile and its encrypted credential live in the application database, so the
``audiocodes_source`` alias is populated at runtime. Each thread's connection wrapper is stamped
with the ``config_version`` it was built from and replaced when settings change.
"""

import logging
import threading
from contextlib import contextmanager

from django.db import DatabaseError, InterfaceError, OperationalError, connections

from audiocodes_cdr.constants import SOURCE_APPLICATION_NAME, SOURCE_DB_ALIAS, STATEMENT_TIMEOUT_MS
from audiocodes_cdr.crypto import decrypt_secret
from audiocodes_cdr.exceptions import (
    CdrSourceError,
    SourceConfigurationError,
    SourceNotConfigured,
    SourceQueryCancelled,
    SourceTimeout,
    SourceUnavailable,
)
from audiocodes_cdr.models import CdrModuleSettings, CdrSourceProfile

logger = logging.getLogger(__name__)

SQLSTATE_QUERY_CANCELED = '57014'
SQLSTATE_RECOVERY_CONFLICT = {'40001', '40P01'}
CONFIG_VERSION_ATTR = '_cdr_config_version'

_lock = threading.Lock()
_built_settings = {'version': None, 'settings': None}


def build_source_settings(profile, password):
    options = {
        'options': (
            f'-c statement_timeout={STATEMENT_TIMEOUT_MS} '
            '-c default_transaction_read_only=on '
            '-c search_path=public'
        ),
        'application_name': SOURCE_APPLICATION_NAME,
        'sslmode': profile.sslmode,
        'connect_timeout': profile.connect_timeout,
    }
    if profile.sslrootcert:
        options['sslrootcert'] = profile.sslrootcert
    return {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': profile.database_name,
        'USER': profile.username,
        'PASSWORD': password,
        'HOST': profile.host,
        'PORT': str(profile.port),
        'ATOMIC_REQUESTS': False,
        'AUTOCOMMIT': True,
        'CONN_MAX_AGE': 0,
        'CONN_HEALTH_CHECKS': False,
        'TIME_ZONE': None,
        'OPTIONS': options,
        'TEST': {'CHARSET': None, 'COLLATION': None, 'MIGRATE': False, 'MIRROR': 'default', 'NAME': None},
    }


def _settings_for(module_settings):
    version = module_settings.config_version
    if _built_settings['version'] == version:
        return _built_settings['settings']

    profile = CdrSourceProfile.objects.filter(role=module_settings.active_source).first()
    if profile is None or not profile.is_enabled or not (profile.host and profile.database_name and profile.username):
        raise SourceNotConfigured()
    password = decrypt_secret(profile.password_encrypted) if profile.password_encrypted else ''

    settings_dict = build_source_settings(profile, password)
    _built_settings.update(version=version, settings=settings_dict)
    return settings_dict


def activate_source(module_settings=None):
    """Point this thread's ``audiocodes_source`` connection at the active profile and return it."""
    if module_settings is None:
        module_settings = CdrModuleSettings.load()
    version = module_settings.config_version

    current = connections[SOURCE_DB_ALIAS]
    if getattr(current, CONFIG_VERSION_ATTR, None) == version:
        return current

    with _lock:
        settings_dict = _settings_for(module_settings)
        connections.settings[SOURCE_DB_ALIAS] = settings_dict
        current.close()
        replacement = connections.create_connection(SOURCE_DB_ALIAS)
        setattr(replacement, CONFIG_VERSION_ATTR, version)
        connections[SOURCE_DB_ALIAS] = replacement
    return replacement


def translate_database_error(exc):
    cause = exc.__cause__ or exc
    sqlstate = getattr(cause, 'sqlstate', None)
    logger.warning('AudioCodes source query failed error=%s sqlstate=%s', type(cause).__name__, sqlstate)
    if sqlstate == SQLSTATE_QUERY_CANCELED:
        return SourceTimeout()
    if sqlstate in SQLSTATE_RECOVERY_CONFLICT:
        return SourceQueryCancelled()
    if isinstance(exc, (OperationalError, InterfaceError)):
        return SourceUnavailable()
    return SourceConfigurationError()


@contextmanager
def source_errors():
    try:
        yield
    except DatabaseError as exc:
        raise translate_database_error(exc) from None


@contextmanager
def source_session(module_settings=None):
    """Activate the source and translate database failures into safe API errors."""
    activate_source(module_settings)
    with source_errors():
        yield


def probe_source():
    """Lightweight availability check for the admin health report. Never exposes connection details."""
    try:
        module_settings = CdrModuleSettings.load()
    except DatabaseError:
        return {'status': 'failure', 'message': 'AudioCodes CDR module settings are unavailable.'}

    report = {'active_source': module_settings.active_source}
    try:
        source = activate_source(module_settings)
        with source_errors(), source.cursor() as cursor:
            cursor.execute('SELECT 1')
    except SourceNotConfigured as exc:
        return {**report, 'status': 'not_configured', 'message': exc.message}
    except CdrSourceError as exc:
        return {**report, 'status': 'failure', 'message': exc.message}
    return {**report, 'status': 'ok'}
