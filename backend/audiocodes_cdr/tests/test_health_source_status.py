# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

import json

import pytest

from audiocodes_cdr.connection import probe_source
from audiocodes_cdr.exceptions import SourceUnavailable
from audiocodes_cdr.models import CdrSourceProfile
from cucm.schemas import CucmHealthResult


@pytest.fixture(autouse=True)
def healthy_cucm(monkeypatch):
    class HealthyCucmClient:
        def health_check(self):
            return CucmHealthResult(available=True, status='ok', version='14')

    monkeypatch.setattr('health.services.get_cucm_client', lambda: HealthyCucmClient())


def test_not_configured_source_is_reported(db):
    assert probe_source() == {
        'active_source': 'replica',
        'status': 'not_configured',
        'message': 'The AudioCodes CDR source database is not configured.',
    }


def test_available_source_is_reported_ok(cdr_source):
    assert probe_source() == {'active_source': 'replica', 'status': 'ok'}


def test_unavailable_source_message_is_generic(db, monkeypatch):
    CdrSourceProfile.objects.create(
        role='replica', host='secret-db.example.internal', database_name='audiocodes', username='cdr_reader',
    )

    def unavailable(module_settings=None):
        raise SourceUnavailable()

    monkeypatch.setattr('audiocodes_cdr.connection.activate_source', unavailable)

    report = probe_source()

    assert report['status'] == 'failure'
    assert 'secret-db' not in json.dumps(report)


def test_admin_health_includes_source_status(admin_client):
    body = admin_client.get('/api/admin/health/').json()

    assert body['audiocodes_cdr']['status'] == 'not_configured'
    assert body['database']['status'] == 'ok'
