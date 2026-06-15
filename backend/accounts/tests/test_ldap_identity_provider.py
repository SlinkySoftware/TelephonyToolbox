# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

from types import SimpleNamespace

import pytest

from accounts.services import LdapIdentityProvider
from ldap3 import SYNC


class FakeEntry:
    def __init__(self, mail, display_name):
        self._mail = mail
        self._display_name = display_name
        self.entry_dn = 'CN=Test User,OU=Users,DC=example,DC=com'

    def __getattr__(self, name):
        if name == 'mail':
            return SimpleNamespace(value=self._mail)
        if name == 'displayName':
            return SimpleNamespace(value=self._display_name)
        raise AttributeError(name)


class FakeConnection:
    def __init__(self, server, user, password, auto_bind, client_strategy, raise_exceptions):
        self.server = server
        self.user = user
        self.password = password
        self.auto_bind = auto_bind
        self.client_strategy = client_strategy
        self.raise_exceptions = raise_exceptions
        self.entries = [FakeEntry('user@example.com', 'Test User')]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def search(self, base, filter_str, attributes):
        self.base = base
        self.filter_str = filter_str
        self.attributes = attributes


@pytest.mark.django_db
def test_ldap_validation_uses_sync_strategy_and_returns_entry_values(monkeypatch, settings):
    captured = {}

    def fake_connection(server, user, password, auto_bind, client_strategy, raise_exceptions):
        captured['client_strategy'] = client_strategy
        return FakeConnection(server, user, password, auto_bind, client_strategy, raise_exceptions)

    monkeypatch.setattr('accounts.services.Connection', fake_connection)
    monkeypatch.setattr('accounts.services.Server', lambda *args, **kwargs: object())

    settings.LDAP_SERVER_URI = 'ldap.example.internal'
    setattr(settings, 'LDAP_BIND' + '_DN', 'bind@example.internal')
    setattr(settings, 'LDAP_BIND' + '_PASSWORD', 'test-secret')
    settings.LDAP_USER_SEARCH_BASE = 'DC=example,DC=com'
    settings.LDAP_USER_EMAIL_ATTRIBUTE = 'mail'
    settings.LDAP_USER_DISPLAY_NAME_ATTRIBUTE = 'displayName'
    settings.LDAP_USER_ENABLED_ATTRIBUTE = ''
    settings.LDAP_GROUP_SEARCH_FILTER = ''

    result = LdapIdentityProvider().validate_user('User@Example.com')

    assert captured['client_strategy'] is SYNC
    assert result.exists is True
    assert result.email == 'user@example.com'
    assert result.display_name == 'Test User'
