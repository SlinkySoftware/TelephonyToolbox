# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

import pytest

from access_groups.models import AccessGroup
from audit.models import AuditEvent
from cucm.exceptions import CucmUnavailableError
from cucm.schemas import CucmDirectoryNumber, CucmUpdateResult
from diversions.models import Diversion


class SuccessfulCucmClient:
    def get_directory_number(self, pattern, route_partition):
        return CucmDirectoryNumber(
            pattern=pattern,
            route_partition=route_partition,
            description='Retail Support Main Line',
            alerting_name='Retail Support',
            ascii_alerting_name='Retail',
            call_forward_all_destination='+61412345678',
            calling_search_space='INTERNAL',
            secondary_calling_search_space='INTERNAL',
        )

    def update_call_forward_all(self, pattern, route_partition, destination):
        return CucmUpdateResult(True, pattern, route_partition, returned_destination=destination)

    def health_check(self):
        return type('Health', (), {'available': True, 'status': 'ok'})()


class UnavailableCucmClient(SuccessfulCucmClient):
    def get_directory_number(self, pattern, route_partition):
        raise CucmUnavailableError('CUCM unavailable')

    def update_call_forward_all(self, pattern, route_partition, destination):
        raise CucmUnavailableError('CUCM unavailable')


class MismatchCucmClient(SuccessfulCucmClient):
    def update_call_forward_all(self, pattern, route_partition, destination):
        return CucmUpdateResult(True, pattern, route_partition, returned_destination='+61299991234')


class RecordingCucmClient(SuccessfulCucmClient):
    def __init__(self):
        self.patterns = []

    def get_directory_number(self, pattern, route_partition):
        self.patterns.append(pattern)
        return super().get_directory_number(pattern, route_partition)


@pytest.mark.django_db
def test_standard_user_only_sees_assigned_diversions(standard_client, standard_user_membership, diversion, admin_user):
    other_group = AccessGroup.objects.create(name='Unrelated', description='Other team')
    Diversion.objects.create(
        name='Unrelated Diversion',
        description='Should not be visible',
        source_number='0288880000',
        source_partition='INTERNAL',
        cached_current_destination='+61277770000',
        group=other_group,
        created_by_text=admin_user.email,
    )

    response = standard_client.get('/api/diversions/')

    assert response.status_code == 200
    assert len(response.json()['results']) == 1
    assert response.json()['results'][0]['source_number'] == '0299990000'


@pytest.mark.django_db
def test_destination_validation_endpoint_returns_normalised_value(standard_client, standard_user_membership, diversion):
    response = standard_client.post(
        f'/api/diversions/{diversion.id}/validate-destination/',
        {'destination': '0412 345 678'},
        format='json',
    )

    assert response.status_code == 200
    assert response.json()['normalised_destination'] == '+61412345678'


@pytest.mark.django_db
def test_diversion_update_success(monkeypatch, standard_client, standard_user_membership, diversion):
    monkeypatch.setattr('diversions.services.get_cucm_client', lambda: SuccessfulCucmClient())

    response = standard_client.post(
        f'/api/diversions/{diversion.id}/update-destination/',
        {'destination': '0412 345 678'},
        format='json',
    )

    diversion.refresh_from_db()
    audit_event = AuditEvent.objects.filter(event_type='diversion.destination_update.success').latest('timestamp')
    assert response.status_code == 200
    assert response.json()['result'] == 'success'
    assert response.json()['diversion']['cucm_status'] == 'available'
    assert audit_event.destination_number == '+61412345678'
    assert audit_event.message == 'Diversion updated successfully to +61412345678.'
    assert diversion.cached_current_destination == '+61412345678'


@pytest.mark.django_db
def test_diversion_refresh_success_includes_available_cucm_status(
    monkeypatch,
    standard_client,
    standard_user_membership,
    diversion,
):
    monkeypatch.setattr('diversions.services.get_cucm_client', lambda: SuccessfulCucmClient())

    response = standard_client.post(
        f'/api/diversions/{diversion.id}/refresh/',
        format='json',
    )

    assert response.status_code == 200
    assert response.json()['result'] == 'success'
    assert response.json()['diversion']['cucm_status'] == 'available'


@pytest.mark.django_db
def test_diversion_update_cucm_unavailable(monkeypatch, standard_client, standard_user_membership, diversion):
    monkeypatch.setattr('diversions.services.get_cucm_client', lambda: UnavailableCucmClient())

    response = standard_client.post(
        f'/api/diversions/{diversion.id}/update-destination/',
        {'destination': '0412 345 678'},
        format='json',
    )

    assert response.status_code == 503
    assert response.json()['error_code'] == 'cucm_unavailable'


@pytest.mark.django_db
def test_diversion_update_readback_mismatch(monkeypatch, standard_client, standard_user_membership, diversion):
    monkeypatch.setattr('diversions.services.get_cucm_client', lambda: MismatchCucmClient())

    response = standard_client.post(
        f'/api/diversions/{diversion.id}/update-destination/',
        {'destination': '0412 345 678'},
        format='json',
    )

    assert response.status_code == 409
    assert response.json()['error_code'] == 'cucm_readback_mismatch'


@pytest.mark.django_db
def test_diversion_delete_removes_local_record_only(admin_client, diversion):
    response = admin_client.delete(f'/api/admin/diversions/{diversion.id}/')

    assert response.status_code == 204
    assert Diversion.objects.filter(pk=diversion.id).exists() is False


@pytest.mark.django_db
def test_admin_validate_source_returns_503_when_cucm_unavailable(monkeypatch, admin_client):
    monkeypatch.setattr('diversions.services.get_cucm_client', lambda: UnavailableCucmClient())

    response = admin_client.post(
        '/api/admin/diversions/validate-source/',
        {'source_number': '0299990000'},
        format='json',
    )

    assert response.status_code == 503
    assert response.json()['message'] == 'CUCM is currently unavailable.'


@pytest.mark.django_db
def test_admin_validate_source_returns_line_name(monkeypatch, admin_client):
    monkeypatch.setattr('diversions.services.get_cucm_client', lambda: SuccessfulCucmClient())

    response = admin_client.post(
        '/api/admin/diversions/validate-source/',
        {'source_number': '0299990000'},
        format='json',
    )

    assert response.status_code == 200
    assert response.json()['line_name'] == 'Retail Support'


@pytest.mark.django_db
def test_admin_validate_source_strips_leading_escape(monkeypatch, admin_client):
    cucm_client = RecordingCucmClient()
    monkeypatch.setattr('diversions.services.get_cucm_client', lambda: cucm_client)

    response = admin_client.post(
        '/api/admin/diversions/validate-source/',
        {'source_number': '\\+61288836590'},
        format='json',
    )

    assert response.status_code == 200
    assert response.json()['source_number'] == '+61288836590'
    assert response.json()['line_name'] == 'Retail Support'
    assert cucm_client.patterns == ['+61288836590']


@pytest.mark.django_db
def test_admin_diversion_create_returns_503_when_cucm_unavailable(monkeypatch, admin_client, access_group):
    monkeypatch.setattr('diversions.services.get_cucm_client', lambda: UnavailableCucmClient())

    response = admin_client.post(
        '/api/admin/diversions/',
        {
            'name': 'Retail Support Main Line',
            'description': 'After-hours diversion',
            'source_number': '0299990000',
            'group_id': str(access_group.id),
        },
        format='json',
    )

    assert response.status_code == 503
    assert response.json()['message'] == 'CUCM is currently unavailable.'


@pytest.mark.django_db
def test_admin_diversion_create_strips_leading_escape(monkeypatch, admin_client, access_group):
    cucm_client = RecordingCucmClient()
    monkeypatch.setattr('diversions.services.get_cucm_client', lambda: cucm_client)

    response = admin_client.post(
        '/api/admin/diversions/',
        {
            'name': 'Retail Support',
            'description': 'After-hours diversion',
            'source_number': '\\+61288836590',
            'group_id': str(access_group.id),
        },
        format='json',
    )

    diversion = Diversion.objects.get(pk=response.json()['id'])

    assert response.status_code == 201
    assert response.json()['source_number'] == '+61288836590'
    assert diversion.source_number == '+61288836590'
    assert cucm_client.patterns == ['+61288836590']