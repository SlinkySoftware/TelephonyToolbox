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
        def get_ccm_version(self):
            raise requests.exceptions.SSLError('tls handshake failed')

        def get_line(self, *args, **kwargs):
            raise requests.exceptions.SSLError('tls handshake failed')

        def __getattr__(self, name):
            if name == 'getCCMVersion':
                return self.get_ccm_version
            if name == 'getLine':
                return self.get_line
            raise AttributeError(name)

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


@pytest.mark.django_db
def test_parse_line_handles_nested_axl_line_response(monkeypatch):
    monkeypatch.setattr(Cucm105Client, '_build_service', lambda self: object())

    client = Cucm105Client('cucm.example.test', 'user', 'pass')

    response = {
        'return': {
            'line': {
                'description': 'Extn 36501',
                'alertingName': 'Extn 36501',
                'asciiAlertingName': 'Extn 36501',
                'callForwardAll': {
                    'destination': '+61404100741',
                    'callingSearchSpaceName': {'_value_1': 'INTERNAL'},
                    'secondaryCallingSearchSpaceName': {'_value_1': 'INTERNAL'},
                },
            }
        }
    }

    directory_number = client._parse_line(response, '36501', 'INTERNAL')

    assert directory_number.description == 'Extn 36501'
    assert directory_number.alerting_name == 'Extn 36501'
    assert directory_number.call_forward_all_destination == '+61404100741'
    assert directory_number.calling_search_space == 'INTERNAL'
    assert directory_number.secondary_calling_search_space == 'INTERNAL'


@pytest.mark.django_db
def test_get_directory_number_escapes_leading_plus_for_cucm(monkeypatch):
    class DummyService:
        def __init__(self):
            self.patterns = []

        def get_line(self, **kwargs):
            self.patterns.append(kwargs['pattern'])
            return {'return': {'callForwardAll': {}}}

        def __getattr__(self, name):
            if name == 'getLine':
                return self.get_line
            raise AttributeError(name)

    service = DummyService()
    monkeypatch.setattr(Cucm105Client, '_build_service', lambda self: service)

    client = Cucm105Client('cucm.example.test', 'user', 'pass')
    directory_number = client.get_directory_number('\\+61288836590', 'INTERNAL')

    assert service.patterns == ['\\+61288836590']
    assert directory_number.pattern == '+61288836590'


@pytest.mark.django_db
def test_update_call_forward_all_escapes_dn_but_not_destination(monkeypatch):
    class DummyService:
        def __init__(self):
            self.get_line_patterns = []
            self.update_line_calls = []

        def get_line(self, **kwargs):
            self.get_line_patterns.append(kwargs['pattern'])
            return {
                'return': {
                    'callForwardAll': {
                        'destination': '+61412345678',
                        'callingSearchSpaceName': {'_value_1': 'INTERNAL'},
                        'secondaryCallingSearchSpaceName': {'_value_1': 'INTERNAL'},
                    }
                }
            }

        def update_line(self, **kwargs):
            self.update_line_calls.append(kwargs)
            return {'return': {}}

        def __getattr__(self, name):
            if name == 'getLine':
                return self.get_line
            if name == 'updateLine':
                return self.update_line
            raise AttributeError(name)

    service = DummyService()
    monkeypatch.setattr(Cucm105Client, '_build_service', lambda self: service)

    client = Cucm105Client('cucm.example.test', 'user', 'pass')
    result = client.update_call_forward_all('\\+61288836590', 'INTERNAL', '+61412345678')

    assert service.get_line_patterns == ['\\+61288836590', '\\+61288836590']
    assert service.update_line_calls == [
        {
            'pattern': '\\+61288836590',
            'routePartitionName': {'_value_1': 'INTERNAL'},
            'callForwardAll': {
                'callingSearchSpaceName': {'_value_1': 'INTERNAL'},
                'secondaryCallingSearchSpaceName': {'_value_1': 'INTERNAL'},
                'destination': '+61412345678',
            },
        }
    ]
    assert result.pattern == '+61288836590'
    assert result.returned_destination == '+61412345678'


@pytest.mark.django_db
def test_update_call_forward_all_omits_empty_css_references(monkeypatch):
    class DummyService:
        def __init__(self):
            self.update_line_calls = []

        def get_line(self, **kwargs):
            return {
                'return': {
                    'line': {
                        'callForwardAll': {
                            'destination': '+61412345678',
                            'callingSearchSpaceName': {'_value_1': None, 'uuid': ''},
                            'secondaryCallingSearchSpaceName': {'_value_1': None, 'uuid': ''},
                        }
                    }
                }
            }

        def update_line(self, **kwargs):
            self.update_line_calls.append(kwargs)
            return {'return': {}}

        def __getattr__(self, name):
            if name == 'getLine':
                return self.get_line
            if name == 'updateLine':
                return self.update_line
            raise AttributeError(name)

    service = DummyService()
    monkeypatch.setattr(Cucm105Client, '_build_service', lambda self: service)

    client = Cucm105Client('cucm.example.test', 'user', 'pass')
    result = client.update_call_forward_all('36501', 'INTERNAL', '+61404100741')

    assert service.update_line_calls == [
        {
            'pattern': '36501',
            'routePartitionName': {'_value_1': 'INTERNAL'},
            'callForwardAll': {
                'destination': '+61404100741',
            },
        }
    ]
    assert result.pattern == '36501'
    assert result.returned_destination == '+61412345678'


@pytest.mark.django_db
def test_fk_value_returns_none_for_empty_zeep_fk_object(monkeypatch):
    monkeypatch.setattr(Cucm105Client, '_build_service', lambda self: object())

    client = Cucm105Client('cucm.example.test', 'user', 'pass')
    fk_object = type('FkObject', (), {'_value_1': None, 'uuid': ''})()

    assert client._fk_value(fk_object) is None