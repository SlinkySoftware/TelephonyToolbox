# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

import pytest
from cryptography.fernet import Fernet
from django.core.exceptions import ImproperlyConfigured
from django.core.management.sql import emit_pre_migrate_signal

from accounts.models import User
from audiocodes_cdr.apps import block_source_migrations, check_cdr_configuration, configure_source_session
from audiocodes_cdr.constants import ROUTER_PATH, SOURCE_DB_ALIAS
from audiocodes_cdr.exceptions import SourceWriteForbidden
from audiocodes_cdr.models import CdrModuleSettings
from audiocodes_cdr.routers import AudioCodesSourceRouter
from audiocodes_cdr.source_models import Cdr, Sdr

router = AudioCodesSourceRouter()


def test_source_models_are_unmanaged():
    assert Sdr._meta.managed is False
    assert Cdr._meta.managed is False
    assert Sdr._meta.db_table == 'sdr'
    assert Cdr._meta.db_table == 'cdr'


def test_reads_route_to_source_alias_only_for_source_models():
    assert router.db_for_read(Sdr) == SOURCE_DB_ALIAS
    assert router.db_for_read(Cdr) == SOURCE_DB_ALIAS
    assert router.db_for_read(CdrModuleSettings) is None
    assert router.db_for_read(User) is None


def test_writes_to_source_models_raise():
    with pytest.raises(SourceWriteForbidden):
        router.db_for_write(Sdr)
    assert router.db_for_write(CdrModuleSettings) is None


def test_migrations_never_target_source():
    assert router.allow_migrate(SOURCE_DB_ALIAS, 'audiocodes_cdr') is False
    assert router.allow_migrate(SOURCE_DB_ALIAS, 'accounts', model_name='user') is False
    assert router.allow_migrate('default', 'audiocodes_cdr', model_name='sdr') is False
    assert router.allow_migrate('default', 'audiocodes_cdr', model_name='Cdr') is False
    assert router.allow_migrate('default', 'audiocodes_cdr', model_name='cdrmodulesettings') is None


def test_relations_between_source_and_app_models_are_refused():
    assert router.allow_relation(Sdr(id=1), CdrModuleSettings()) is False
    assert router.allow_relation(Sdr(id=1), Cdr(id=1)) is True
    assert router.allow_relation(CdrModuleSettings(), CdrModuleSettings()) is None


@pytest.mark.parametrize(
    'operation',
    [
        lambda: Sdr(id=1).save(),
        lambda: Sdr(id=1).delete(),
        lambda: Sdr.objects.create(id=1),
        lambda: Sdr.objects.bulk_create([Sdr(id=1)]),
        lambda: Sdr.objects.get_or_create(id=1),
        lambda: Sdr.objects.update_or_create(id=1),
        lambda: Sdr.objects.filter(id=1).update(sessionid='x'),
        lambda: Sdr.objects.filter(id=1).delete(),
        lambda: Cdr.objects.select_for_update().filter(id=1),
        lambda: Cdr.objects.all().bulk_update([Cdr(id=1)], ['callid']),
    ],
)
def test_source_querysets_and_instances_refuse_writes(operation):
    with pytest.raises(SourceWriteForbidden):
        operation()


def test_pre_migrate_guard_blocks_source_alias():
    with pytest.raises(ImproperlyConfigured):
        block_source_migrations(sender=None, using=SOURCE_DB_ALIAS)
    block_source_migrations(sender=None, using='default')


def test_pre_migrate_guard_is_connected():
    with pytest.raises(ImproperlyConfigured):
        emit_pre_migrate_signal(verbosity=0, interactive=False, db=SOURCE_DB_ALIAS)


class _FakeCursor:
    def __init__(self, executed):
        self.executed = executed

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql):
        self.executed.append(sql)


class _FakeConnection:
    def __init__(self, alias, vendor='postgresql'):
        self.alias = alias
        self.vendor = vendor
        self.executed = []

    def cursor(self):
        return _FakeCursor(self.executed)


def test_connection_created_sets_timeout_and_read_only_on_source_only():
    source = _FakeConnection(SOURCE_DB_ALIAS)
    configure_source_session(sender=None, connection=source)
    assert source.executed == ['SET statement_timeout = 60000', 'SET default_transaction_read_only = on']

    other = _FakeConnection('default')
    configure_source_session(sender=None, connection=other)
    assert other.executed == []


def _ids(messages):
    return {message.id for message in messages}


def test_system_checks_fail_closed(settings):
    settings.CDR_SOURCE_ENCRYPTION_KEY = Fernet.generate_key().decode()
    assert _ids(check_cdr_configuration(None)) == set()

    settings.CDR_SOURCE_ENCRYPTION_KEY = ''
    assert 'audiocodes_cdr.W001' in _ids(check_cdr_configuration(None))

    settings.CDR_SOURCE_ENCRYPTION_KEY = 'not-a-fernet-key'
    assert 'audiocodes_cdr.E003' in _ids(check_cdr_configuration(None))

    settings.DATABASE_ROUTERS = [path for path in settings.DATABASE_ROUTERS if path != ROUTER_PATH]
    assert 'audiocodes_cdr.E002' in _ids(check_cdr_configuration(None))
