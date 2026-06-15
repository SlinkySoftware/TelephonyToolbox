import pytest

from access_groups.models import AccessGroup
from cucm.exceptions import CucmUnavailableError
from cucm.schemas import CucmDirectoryNumber, CucmUpdateResult
from diversions.models import Diversion


class SuccessfulCucmClient:
    def get_directory_number(self, pattern, route_partition):
        return CucmDirectoryNumber(
            pattern=pattern,
            route_partition=route_partition,
            call_forward_all_destination='+61412345678',
            calling_search_space='INTERNAL',
            secondary_calling_search_space='INTERNAL',
        )

    def update_call_forward_all(self, pattern, route_partition, destination):
        return CucmUpdateResult(True, pattern, route_partition, returned_destination=destination)

    def health_check(self):
        return type('Health', (), {'available': True, 'status': 'ok'})()


class UnavailableCucmClient(SuccessfulCucmClient):
    def update_call_forward_all(self, pattern, route_partition, destination):
        raise CucmUnavailableError('CUCM unavailable')


class MismatchCucmClient(SuccessfulCucmClient):
    def update_call_forward_all(self, pattern, route_partition, destination):
        return CucmUpdateResult(True, pattern, route_partition, returned_destination='+61299991234')


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
    assert response.status_code == 200
    assert response.json()['result'] == 'success'
    assert diversion.cached_current_destination == '+61412345678'


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