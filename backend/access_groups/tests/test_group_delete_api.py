import pytest


@pytest.mark.django_db
def test_group_delete_blocked_when_diversions_exist(admin_client, access_group, diversion):
    response = admin_client.delete(f'/api/admin/groups/{access_group.id}/')

    assert response.status_code == 400
    assert response.json()['error_code'] == 'group_contains_diversions'


@pytest.mark.django_db
def test_group_delete_allowed_when_no_diversions(admin_client, access_group):
    response = admin_client.delete(f'/api/admin/groups/{access_group.id}/')

    assert response.status_code == 204