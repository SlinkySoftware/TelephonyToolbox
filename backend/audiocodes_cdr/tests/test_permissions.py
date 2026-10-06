# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

import pytest
from django.middleware.csrf import _get_new_csrf_string
from rest_framework.test import APIClient

GET_ENDPOINTS = [
    '/api/admin/cdr/sdr/',
    '/api/admin/cdr/sdr/1/',
    '/api/admin/cdr/lookups/ingress-ip-groups/',
    '/api/admin/cdr/lookups/egress-ip-groups/',
    '/api/admin/cdr/lookups/termination-reasons/',
    '/api/admin/cdr/statistics/summary/',
    '/api/admin/cdr/statistics/timeseries/',
    '/api/admin/cdr/statistics/ip-groups/',
    '/api/admin/cdr/statistics/termination-reasons/',
    '/api/admin/cdr/config/display/',
    '/api/admin/cdr/preferences/',
    '/api/admin/cdr/settings/',
]
PUT_ENDPOINTS = ['/api/admin/cdr/preferences/', '/api/admin/cdr/settings/']


@pytest.mark.parametrize('url', GET_ENDPOINTS)
def test_anonymous_get_is_rejected(api_client, db, url):
    assert api_client.get(url).status_code == 401


@pytest.mark.parametrize('url', PUT_ENDPOINTS)
def test_anonymous_put_is_rejected(api_client, db, url):
    assert api_client.put(url, {}, format='json').status_code == 401


@pytest.mark.parametrize('url', GET_ENDPOINTS)
def test_standard_user_get_is_forbidden(standard_client, url):
    assert standard_client.get(url).status_code == 403


@pytest.mark.parametrize('url', PUT_ENDPOINTS)
def test_standard_user_put_is_forbidden(standard_client, url):
    assert standard_client.put(url, {'duration_format': 'seconds'}, format='json').status_code == 403


def test_admin_responses_are_not_cacheable(admin_client):
    response = admin_client.get('/api/admin/cdr/config/display/')

    assert response.status_code == 200
    assert 'no-store' in response['Cache-Control']
    assert 'private' in response['Cache-Control']


def test_put_requires_csrf_token(admin_user):
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(admin_user)

    response = client.put('/api/admin/cdr/preferences/', {'duration_format': 'seconds'}, format='json')
    assert response.status_code == 403

    token = _get_new_csrf_string()
    client.cookies['csrftoken'] = token
    response = client.put(
        '/api/admin/cdr/preferences/',
        {'duration_format': 'seconds'},
        format='json',
        HTTP_X_CSRFTOKEN=token,
    )
    assert response.status_code == 200
