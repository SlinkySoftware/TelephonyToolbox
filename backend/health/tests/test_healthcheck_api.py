# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

import pytest

from cucm.exceptions import CucmUnavailableError
from cucm.schemas import CucmHealthResult


@pytest.fixture
def healthy_cucm_client():
    class HealthyCucmClient:
        def health_check(self):
            return CucmHealthResult(available=True, status='ok', version='14')

    return HealthyCucmClient()


def test_healthcheck_is_unauthenticated(api_client, db, monkeypatch, healthy_cucm_client):
    monkeypatch.setattr('health.services.get_cucm_client', lambda: healthy_cucm_client)

    response = api_client.get('/api/healthcheck')

    assert response.status_code == 200


def test_healthcheck_returns_200_when_all_ok(api_client, db, monkeypatch, healthy_cucm_client):
    monkeypatch.setattr('health.services.get_cucm_client', lambda: healthy_cucm_client)

    response = api_client.get('/api/healthcheck')

    assert response.status_code == 200
    body = response.json()
    assert body['status'] == 'healthy'
    assert body['checks']['database']['status'] == 'ok'
    assert body['checks']['cucm']['status'] == 'ok'


def test_healthcheck_returns_503_when_cucm_unavailable(api_client, db, monkeypatch):
    class UnavailableCucmClient:
        def health_check(self):
            raise CucmUnavailableError('connection refused')

    monkeypatch.setattr('health.services.get_cucm_client', lambda: UnavailableCucmClient())

    response = api_client.get('/api/healthcheck')

    assert response.status_code == 503
    body = response.json()
    assert body['status'] == 'unhealthy'
    assert body['checks']['database']['status'] == 'ok'
    assert body['checks']['cucm']['status'] == 'failure'


def test_healthcheck_returns_503_on_unexpected_cucm_error(api_client, db, monkeypatch):
    class BrokenCucmClient:
        def health_check(self):
            raise OSError('TLS CA bundle missing')

    monkeypatch.setattr('health.services.get_cucm_client', lambda: BrokenCucmClient())

    response = api_client.get('/api/healthcheck')

    assert response.status_code == 503
    assert response.json()['checks']['cucm']['status'] == 'failure'
