# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

import pytest
from django.db import OperationalError, ProgrammingError, connections

from audiocodes_cdr import connection as source_connection
from audiocodes_cdr.constants import SOURCE_DB_ALIAS
from audiocodes_cdr.crypto import encrypt_secret
from audiocodes_cdr.exceptions import (
    SourceConfigurationError,
    SourceNotConfigured,
    SourceQueryCancelled,
    SourceTimeout,
    SourceUnavailable,
)
from audiocodes_cdr.models import CdrModuleSettings, CdrSourceProfile


@pytest.fixture
def restore_source_alias():
    original_wrapper = connections[SOURCE_DB_ALIAS]
    original_settings = connections.settings[SOURCE_DB_ALIAS]
    source_connection._built_settings.update(version=None, settings=None)
    yield
    connections[SOURCE_DB_ALIAS].close()
    connections[SOURCE_DB_ALIAS] = original_wrapper
    connections.settings[SOURCE_DB_ALIAS] = original_settings
    source_connection._built_settings.update(version=None, settings=None)


@pytest.fixture
def replica_profile(db, encryption_key):
    return CdrSourceProfile.objects.create(
        role='replica',
        host='replica.example.internal',
        port=5433,
        database_name='audiocodes',
        username='cdr_reader',
        password_encrypted=encrypt_secret('reader-secret'),
        sslmode='require',
        sslrootcert='/etc/pki/tls/certs/ca.pem',
        connect_timeout=7,
    )


def test_build_source_settings_is_read_only_with_timeout(replica_profile):
    settings_dict = source_connection.build_source_settings(replica_profile, 'pw')

    options = settings_dict['OPTIONS']
    assert 'statement_timeout=60000' in options['options']
    assert 'default_transaction_read_only=on' in options['options']
    assert options['application_name'] == 'telephony-toolbox-cdr'
    assert options['sslmode'] == 'require'
    assert options['sslrootcert'] == '/etc/pki/tls/certs/ca.pem'
    assert options['connect_timeout'] == 7
    assert 'server_side_binding' not in options
    assert settings_dict['ATOMIC_REQUESTS'] is False
    assert settings_dict['CONN_MAX_AGE'] == 0


def test_activate_source_uses_active_profile_and_stamps_version(replica_profile, restore_source_alias):
    module_settings = CdrModuleSettings.load()

    wrapper = source_connection.activate_source(module_settings)

    assert connections[SOURCE_DB_ALIAS] is wrapper
    assert wrapper.settings_dict['HOST'] == 'replica.example.internal'
    assert wrapper.settings_dict['PORT'] == '5433'
    assert wrapper.settings_dict['PASSWORD'] == 'reader-secret'
    assert source_connection.activate_source(module_settings) is wrapper

    replica_profile.host = 'replica2.example.internal'
    replica_profile.save()
    module_settings.config_version += 1
    module_settings.save()

    replacement = source_connection.activate_source(module_settings)
    assert replacement is not wrapper
    assert replacement.settings_dict['HOST'] == 'replica2.example.internal'


def test_activate_source_does_not_fall_back_to_another_profile(replica_profile, restore_source_alias):
    module_settings = CdrModuleSettings.load()
    module_settings.active_source = 'primary'
    module_settings.save()

    with pytest.raises(SourceNotConfigured):
        source_connection.activate_source(module_settings)


def test_activate_source_refuses_disabled_profile(replica_profile, restore_source_alias):
    replica_profile.is_enabled = False
    replica_profile.save()

    with pytest.raises(SourceNotConfigured):
        source_connection.activate_source(CdrModuleSettings.load())


def test_activate_source_fails_closed_without_key(replica_profile, restore_source_alias, settings):
    settings.CDR_SOURCE_ENCRYPTION_KEY = ''

    with pytest.raises(SourceConfigurationError):
        source_connection.activate_source(CdrModuleSettings.load())


class _PsycopgError(Exception):
    def __init__(self, sqlstate):
        super().__init__('detail that must not leak: host=db.internal')
        self.sqlstate = sqlstate


def _django_error(error_class, sqlstate=None):
    exc = error_class('wrapped')
    exc.__cause__ = _PsycopgError(sqlstate)
    return exc


@pytest.mark.parametrize(
    'exc, expected',
    [
        (_django_error(OperationalError, '57014'), SourceTimeout),
        (_django_error(OperationalError, '40001'), SourceQueryCancelled),
        (_django_error(OperationalError, None), SourceUnavailable),
        (_django_error(ProgrammingError, '42501'), SourceConfigurationError),
    ],
)
def test_database_errors_translate_to_safe_api_errors(exc, expected):
    translated = source_connection.translate_database_error(exc)

    assert type(translated) is expected
    assert 'db.internal' not in str(translated.detail)


def test_source_errors_context_translates():
    with pytest.raises(SourceTimeout):
        with source_connection.source_errors():
            raise _django_error(OperationalError, '57014')
