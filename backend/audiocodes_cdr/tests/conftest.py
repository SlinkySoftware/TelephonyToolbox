# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

import itertools

import pytest
from cryptography.fernet import Fernet
from django.db import connection, connections

from audiocodes_cdr.constants import SOURCE_DB_ALIAS
from audiocodes_cdr.models import CdrModuleSettings
from audiocodes_cdr.source_models import Cdr, Sdr


@pytest.fixture(scope='session')
def cdr_source_tables(django_db_setup, django_db_blocker):
    """Create the unmanaged source tables in the test database (no dev source DB exists)."""
    with django_db_blocker.unblock():
        existing = set(connection.introspection.table_names())
        with connection.schema_editor() as editor:
            for model in (Sdr, Cdr):
                if model._meta.db_table not in existing:
                    editor.create_model(model)


class SourceSeeder:
    """Inserts source rows with raw SQL, because the source models refuse every write."""

    def __init__(self):
        self._ids = itertools.count(1)

    def _insert(self, model, values):
        values.setdefault('id', next(self._ids))
        fields = [model._meta.get_field(name) for name in values]
        quote = connection.ops.quote_name
        sql = 'INSERT INTO {} ({}) VALUES ({})'.format(
            quote(model._meta.db_table),
            ', '.join(quote(field.column) for field in fields),
            ', '.join(['%s'] * len(fields)),
        )
        params = [field.get_db_prep_save(values[field.name], connection) for field in fields]
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
        return values['id']

    def sdr(self, **values):
        return self._insert(Sdr, values)

    def cdr(self, **values):
        return self._insert(Cdr, values)


@pytest.fixture
def cdr_source(db, cdr_source_tables, monkeypatch):
    """Serve the ``audiocodes_source`` alias from the test database inside the test transaction."""
    original = connections[SOURCE_DB_ALIAS]
    connections[SOURCE_DB_ALIAS] = connections['default']
    monkeypatch.setattr('audiocodes_cdr.connection.activate_source', lambda module_settings=None: connections['default'])
    yield SourceSeeder()
    connections[SOURCE_DB_ALIAS] = original


@pytest.fixture
def module_settings(db):
    return CdrModuleSettings.load()


@pytest.fixture
def encryption_key(settings):
    key = Fernet.generate_key().decode('ascii')
    settings.CDR_SOURCE_ENCRYPTION_KEY = key
    return key
