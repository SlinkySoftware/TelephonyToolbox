# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

from django.apps import AppConfig
from django.conf import settings
from django.core import checks
from django.core.exceptions import ImproperlyConfigured
from django.db.backends.signals import connection_created
from django.db.models.signals import pre_migrate

from audiocodes_cdr.constants import ROUTER_PATH, SOURCE_DB_ALIAS, STATEMENT_TIMEOUT_MS


def configure_source_session(sender, connection, **kwargs):
    if connection.alias != SOURCE_DB_ALIAS or connection.vendor != 'postgresql':
        return
    with connection.cursor() as cursor:
        cursor.execute(f'SET statement_timeout = {STATEMENT_TIMEOUT_MS}')
        cursor.execute('SET default_transaction_read_only = on')


def block_source_migrations(sender, using=None, **kwargs):
    if using == SOURCE_DB_ALIAS:
        raise ImproperlyConfigured('Migrations must never run against the AudioCodes source database.')


def check_cdr_configuration(app_configs, **kwargs):
    from audiocodes_cdr.crypto import KEY_INVALID, KEY_MISSING, key_status

    messages = []
    if SOURCE_DB_ALIAS not in settings.DATABASES:
        messages.append(checks.Error(
            f"DATABASES['{SOURCE_DB_ALIAS}'] placeholder is missing.",
            id='audiocodes_cdr.E001',
        ))
    if ROUTER_PATH not in getattr(settings, 'DATABASE_ROUTERS', []):
        messages.append(checks.Error(
            f'{ROUTER_PATH} must be listed in DATABASE_ROUTERS to keep the source read-only.',
            id='audiocodes_cdr.E002',
        ))
    status = key_status()
    if status == KEY_INVALID:
        messages.append(checks.Error(
            'CDR_SOURCE_ENCRYPTION_KEY is not a valid comma-separated list of Fernet keys.',
            id='audiocodes_cdr.E003',
        ))
    elif status == KEY_MISSING:
        messages.append(checks.Warning(
            'CDR_SOURCE_ENCRYPTION_KEY is not set; the AudioCodes CDR source credential cannot be stored or used.',
            id='audiocodes_cdr.W001',
        ))
    return messages


class AudiocodesCdrConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'audiocodes_cdr'
    verbose_name = 'AudioCodes CDR'

    def ready(self):
        connection_created.connect(configure_source_session, dispatch_uid='audiocodes_cdr.configure_source_session')
        pre_migrate.connect(block_source_migrations, dispatch_uid='audiocodes_cdr.block_source_migrations')
        checks.register(check_cdr_configuration)
