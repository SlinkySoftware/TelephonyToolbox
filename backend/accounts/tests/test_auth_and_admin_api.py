import pytest


@pytest.mark.django_db
def test_auth_options_sets_csrf_cookie(client, settings):
    settings.AUTH_MODE = 'entra'
    response = client.get('/api/auth/options/')

    assert response.status_code == 200
    assert response.json()['auth_mode'] == 'entra'
    assert 'csrftoken' in response.cookies


@pytest.mark.django_db
def test_auth_me_requires_authentication(client):
    response = client.get('/api/auth/me/')

    assert response.status_code == 401


@pytest.mark.django_db
def test_standard_user_cannot_access_admin_users_endpoint(standard_client):
    response = standard_client.get('/api/admin/users/')

    assert response.status_code == 403