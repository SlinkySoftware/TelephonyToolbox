# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

import pytest
import requests
from requests.adapters import HTTPAdapter

from cucm.client_105 import Cucm105Client
from cucm.client_14 import Cucm14Client
from cucm import client_zeep
from cucm.exceptions import CucmUnavailableError


@pytest.fixture
def fake_zeep(monkeypatch):
    captured = {}

    class DummyTransport:
        def __init__(self, session, timeout):
            captured['session'] = session
            captured['timeout'] = timeout

    class DummyClient:
        def __init__(self, wsdl, transport, settings):
            captured['wsdl'] = wsdl
            captured['transport'] = transport
            captured['settings'] = settings

        def create_service(self, binding, location):
            captured['binding'] = binding
            captured['location'] = location
            return object()

    monkeypatch.setattr(client_zeep, 'Transport', DummyTransport)
    monkeypatch.setattr(client_zeep, 'Client', DummyClient)
    return captured


@pytest.mark.django_db
def test_cucm_105_mounts_legacy_tls_adapter(monkeypatch, fake_zeep):
    captured_ciphers = {}

    class DummyContext:
        def __init__(self):
            self.check_hostname = True

        def set_ciphers(self, value):
            captured_ciphers['ciphers'] = value

    monkeypatch.setattr(client_zeep.ssl, 'create_default_context', DummyContext)

    Cucm105Client('cucm.example.test', 'user', 'pass')

    adapter = fake_zeep['session'].get_adapter('https://cucm.example.test')
    assert isinstance(adapter, client_zeep.LegacyCucmTlsAdapter)
    assert captured_ciphers['ciphers'] == 'DEFAULT:@SECLEVEL=0'
    assert adapter._ssl_context.check_hostname is False


@pytest.mark.django_db
def test_cucm_14_keeps_default_https_adapter(monkeypatch, fake_zeep):
    monkeypatch.setattr(
        client_zeep.ssl,
        'create_default_context',
        lambda *args, **kwargs: pytest.fail('CUCM 14 should not create a legacy TLS context'),
    )

    Cucm14Client('cucm.example.test', 'user', 'pass')

    adapter = fake_zeep['session'].get_adapter('https://cucm.example.test')
    assert type(adapter) is HTTPAdapter


@pytest.mark.django_db
def test_cucm_105_wraps_requests_tls_errors_as_unavailable(monkeypatch):
    class DummyService:
        def getCCMVersion(self):
            raise requests.exceptions.SSLError('tls handshake failed')

        def getLine(self, *args, **kwargs):
            raise requests.exceptions.SSLError('tls handshake failed')

    monkeypatch.setattr(Cucm105Client, '_build_service', lambda self: DummyService())

    client = Cucm105Client('cucm.example.test', 'user', 'pass')

    with pytest.raises(CucmUnavailableError, match='tls handshake failed'):
        client.health_check()

    with pytest.raises(CucmUnavailableError, match='tls handshake failed'):
        client.get_directory_number('0299990000', 'INTERNAL')


@pytest.mark.django_db
def test_parse_line_handles_object_response_without_call_forward_all(monkeypatch):
    monkeypatch.setattr(Cucm105Client, '_build_service', lambda self: object())

    client = Cucm105Client('cucm.example.test', 'user', 'pass')

    response = type('DummyResponse', (), {})()
    setattr(response, 'return', type('DummyLine', (), {})())

    directory_number = client._parse_line(response, '0299990000', 'INTERNAL')

    assert directory_number.call_forward_all_destination is None
    assert directory_number.calling_search_space is None
    assert directory_number.secondary_calling_search_space is None