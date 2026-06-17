# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

from django.http import HttpResponseRedirect
import pytest

from accounts.models import AuthSource, User, UserRole
from accounts.services import IdentityValidationResult


@pytest.mark.django_db
def test_auth_options_sets_csrf_cookie(client, settings):
    settings.AUTH_MODE = 'oidc'
    settings.EXTERNAL_AUTH_NAME = 'Enterprise Sign In'
    response = client.get('/api/auth/options/')

    assert response.status_code == 200
    assert response.json()['auth_mode'] == 'oidc'
    assert response.json()['external_auth_name'] == 'Enterprise Sign In'
    assert 'csrftoken' in response.cookies


@pytest.mark.django_db
def test_auth_me_requires_authentication(client):
    response = client.get('/api/auth/me/')

    assert response.status_code == 401


@pytest.mark.django_db
def test_standard_user_cannot_access_admin_users_endpoint(standard_client):
    response = standard_client.get('/api/admin/users/')

    assert response.status_code == 403


@pytest.mark.django_db
def test_admin_user_create_requires_at_least_one_group(admin_client):
    response = admin_client.post(
        '/api/admin/users/',
        {
            'email': 'new.user@example.com',
            'display_name': 'New User',
            'auth_source': 'local',
            'role': 'standard_user',
            'group_ids': [],
            'is_active': True,
        },
        format='json',
    )

    assert response.status_code == 400
    assert response.json()['group_ids'] == ['Select at least one group.']


@pytest.mark.django_db
def test_oidc_login_redirects_to_generic_provider(client, settings, monkeypatch):
    settings.AUTH_MODE = 'oidc'

    def fake_authorize_redirect(request):
        return HttpResponseRedirect('/oidc/authorize/')

    monkeypatch.setattr('accounts.views.GenericOidcService.authorize_redirect', fake_authorize_redirect)

    response = client.get('/api/auth/login/oidc/')

    assert response.status_code == 302
    assert response['Location'] == '/oidc/authorize/'


@pytest.mark.django_db
def test_oidc_callback_logs_in_existing_user(client, settings, monkeypatch):
    settings.AUTH_MODE = 'oidc'
    user = User.objects.create_user(
        email='oidc.user@example.com',
        display_name='OIDC User',
        auth_source=AuthSource.OIDC,
        role=UserRole.STANDARD_USER,
    )

    def fake_handle_callback(request):
        return IdentityValidationResult(
            exists=True,
            provider='oidc',
            email=user.email,
            display_name='Updated OIDC User',
            username=user.email,
        )

    monkeypatch.setattr('accounts.views.GenericOidcService.handle_callback', fake_handle_callback)

    response = client.get('/api/auth/login/oidc/callback/')

    assert response.status_code == 302
    assert response['Location'] == '/'
    assert client.session['_auth_user_id'] == str(user.pk)


@pytest.mark.django_db
def test_admin_validate_external_user_returns_400_for_generic_oidc(admin_client, settings):
    settings.AUTH_MODE = 'oidc'

    response = admin_client.post('/api/admin/users/validate/', {'email': 'oidc.user@example.com'}, format='json')

    assert response.status_code == 400
    assert response.json()['message'] == 'External user validation is not supported for this authentication provider.'


@pytest.mark.django_db
def test_admin_can_create_oidc_user_without_external_validation(admin_client, access_group, settings, monkeypatch):
    settings.AUTH_MODE = 'oidc'

    def fail_validation(email):
        raise AssertionError('OIDC user creation should not call external validation.')

    monkeypatch.setattr('accounts.views.IdentityValidationService.validate_user', fail_validation)

    response = admin_client.post(
        '/api/admin/users/',
        {
            'email': 'new.oidc.user@example.com',
            'display_name': 'New OIDC User',
            'auth_source': 'oidc',
            'role': 'standard_user',
            'group_ids': [str(access_group.id)],
            'is_active': True,
        },
        format='json',
    )

    assert response.status_code == 201
    assert response.json()['auth_source'] == 'oidc'
    assert response.json()['display_name'] == 'New OIDC User'


@pytest.mark.django_db
def test_admin_user_create_rejects_mismatched_external_auth_source(admin_client, access_group, settings):
    settings.AUTH_MODE = 'oidc'

    response = admin_client.post(
        '/api/admin/users/',
        {
            'email': 'wrong.provider@example.com',
            'display_name': 'Wrong Provider',
            'auth_source': 'entra',
            'role': 'standard_user',
            'group_ids': [str(access_group.id)],
            'is_active': True,
        },
        format='json',
    )

    assert response.status_code == 400
    assert response.json()['auth_source'] == ['Auth source must match the configured external authentication provider.']