# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

import json

import pytest

from audit.models import AuditEvent
from audiocodes_cdr.crypto import decrypt_secret
from audiocodes_cdr.models import CdrModuleSettings, CdrSourceProfile, CdrUserPreference

URL = '/api/admin/cdr/settings/'
SECRET = 'replica-Secret-123'
REPLICA = {
    'host': 'replica.example.internal',
    'port': 5432,
    'database_name': 'audiocodes',
    'username': 'cdr_reader',
    'password': SECRET,
    'sslmode': 'require',
}


def _put(client, payload):
    return client.put(URL, payload, format='json')


def test_defaults(admin_client):
    body = admin_client.get(URL).json()

    assert body['active_source'] == 'replica'
    assert body['profiles'] == {'replica': None, 'primary': None}
    assert body['max_page_size'] == 500
    assert body['max_multiselect_values'] == 50
    assert body['lookup_cache_seconds'] == 900
    assert body['statistics_cache_seconds'] == 300
    assert body['termination_lookup_days'] == 30
    assert body['hourly_bucket_max_hours'] == 168
    assert body['media_quality']['local_jitter'] == {
        'warning': None, 'critical': None, 'unit': '', 'field': 'localjitter', 'configured': False,
    }
    assert body['user_defined_fields']['varcalluserdefined3']['label'] == 'User Defined 3'


def test_credential_is_encrypted_never_returned_and_audited(admin_client, encryption_key):
    response = _put(admin_client, {'profiles': {'replica': REPLICA}})

    assert response.status_code == 200
    assert SECRET not in json.dumps(response.json())
    assert 'password' not in response.json()['profiles']['replica']
    assert response.json()['profiles']['replica']['has_password'] is True

    profile = CdrSourceProfile.objects.get(role='replica')
    assert SECRET not in profile.password_encrypted
    assert decrypt_secret(profile.password_encrypted) == SECRET

    event = AuditEvent.objects.get(event_type='cdr.settings.updated')
    assert event.actor_email == 'admin@example.com'
    assert SECRET not in json.dumps(event.metadata_json)
    assert event.metadata_json['profile_changes'] == {'replica': ['created', 'password']}
    assert SECRET not in json.dumps(admin_client.get(URL).json())


def test_update_bumps_config_version(admin_client, encryption_key):
    before = CdrModuleSettings.load().config_version

    _put(admin_client, {'profiles': {'replica': REPLICA}})
    response = _put(admin_client, {'active_source': 'primary', 'max_page_size': 250})

    assert response.json()['config_version'] == before + 2
    events = {event.metadata_json['config_version']: event for event in AuditEvent.objects.filter(event_type='cdr.settings.updated')}
    assert events[before + 2].metadata_json['changes'] == {
        'active_source': {'from': 'replica', 'to': 'primary'},
        'max_page_size': {'from': 500, 'to': 250},
    }


def test_unchanged_update_is_not_audited(admin_client):
    before = CdrModuleSettings.load().config_version

    response = _put(admin_client, {'max_page_size': 500})

    assert response.status_code == 200
    assert response.json()['config_version'] == before
    assert not AuditEvent.objects.filter(event_type='cdr.settings.updated').exists()


def test_existing_password_is_kept_when_omitted(admin_client, encryption_key):
    _put(admin_client, {'profiles': {'replica': REPLICA}})
    original = CdrSourceProfile.objects.get(role='replica').password_encrypted

    without_password = {key: value for key, value in REPLICA.items() if key != 'password'}
    response = _put(admin_client, {'profiles': {'replica': {**without_password, 'host': 'replica2.example.internal'}}})

    assert response.status_code == 200
    profile = CdrSourceProfile.objects.get(role='replica')
    assert profile.password_encrypted == original
    assert profile.host == 'replica2.example.internal'


def test_new_profile_requires_password(admin_client, encryption_key):
    without_password = {key: value for key, value in REPLICA.items() if key != 'password'}

    response = _put(admin_client, {'profiles': {'replica': without_password}})

    assert response.status_code == 400
    assert not CdrSourceProfile.objects.exists()


def test_profile_can_be_removed(admin_client, encryption_key):
    _put(admin_client, {'profiles': {'replica': REPLICA}})

    response = _put(admin_client, {'profiles': {'replica': None}})

    assert response.json()['profiles']['replica'] is None
    assert not CdrSourceProfile.objects.exists()


def test_missing_encryption_key_fails_closed(admin_client, settings):
    settings.CDR_SOURCE_ENCRYPTION_KEY = ''

    response = _put(admin_client, {'profiles': {'replica': REPLICA}, 'max_page_size': 100})

    assert response.status_code == 503
    assert response.json()['error_code'] == 'encryption_key_missing'
    assert not CdrSourceProfile.objects.exists()
    assert CdrModuleSettings.load().max_page_size == 500


@pytest.mark.parametrize(
    'payload',
    [
        {'media_quality': {'local_jitter': {'warning': 10}}},
        {'media_quality': {'local_jitter': {'warning': 30, 'critical': 20, 'unit': 'ms'}}},
        {'media_quality': {'local_jitter': {'warning': -1, 'unit': 'ms'}}},
        {'field_help_overrides': {'sdr.not_a_field': 'x'}},
        {'max_page_size': 1000},
        {'active_source': 'standby'},
        {'profiles': {'replica': {**REPLICA, 'host': 'bad host; rm'}}},
        {'profiles': {'replica': {**REPLICA, 'sslmode': 'allow-anything'}}},
        {'profiles': {'replica': {**REPLICA, 'sslrootcert': 'relative/path.pem'}}},
    ],
)
def test_invalid_settings_are_rejected(admin_client, encryption_key, payload):
    assert _put(admin_client, payload).status_code == 400


def test_display_settings_flow_into_display_config(admin_client):
    response = _put(admin_client, {
        'user_defined_fields': {'varcalluserdefined1': {'label': 'Queue', 'description': 'Genesys queue'}},
        'media_quality': {'local_jitter': {'warning': 30, 'critical': 50, 'unit': 'ms'}},
        'field_help_overrides': {'sdr.callduration': 'Custom help.', 'termination.GWAPP_USER_BUSY': 'Called party busy.'},
    })
    assert response.status_code == 200

    config = admin_client.get('/api/admin/cdr/config/display/').json()

    assert config['user_defined_fields']['varcalluserdefined1'] == {'label': 'Queue', 'description': 'Genesys queue'}
    assert config['user_defined_fields']['varcalluserdefined2']['label'] == 'User Defined 2'
    assert config['media_quality']['local_jitter']['configured'] is True
    assert config['media_quality']['remote_jitter']['configured'] is False
    assert config['help']['sdr']['callduration'] == 'Custom help.'
    assert config['help']['termination_reasons'] == {'GWAPP_USER_BUSY': 'Called party busy.'}
    assert config['help']['version'] == 'AudioCodes SBC 7.4'
    assert config['default_page_size'] == 100
    assert config['timezone'] == 'Australia/Sydney'


def test_duration_preference_round_trip(admin_client, admin_user):
    assert admin_client.get('/api/admin/cdr/preferences/').json() == {'duration_format': 'hms'}

    response = admin_client.put('/api/admin/cdr/preferences/', {'duration_format': 'seconds'}, format='json')

    assert response.json() == {'duration_format': 'seconds'}
    assert CdrUserPreference.objects.get(user=admin_user).duration_format == 'seconds'
    assert admin_client.get('/api/admin/cdr/config/display/').json()['duration_format'] == 'seconds'
    assert admin_client.put('/api/admin/cdr/preferences/', {'duration_format': 'minutes'}, format='json').status_code == 400
