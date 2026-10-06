# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

from datetime import timedelta

from django.utils import timezone

from audiocodes_cdr import lookups
from audiocodes_cdr.exceptions import SourceUnavailable

URL = '/api/admin/cdr/lookups/'


def test_ip_group_lookups_are_distinct_sorted_and_skip_blanks(admin_client, cdr_source):
    for ingress, egress in [('beta', 'PBX'), ('Alpha', 'PBX'), ('beta', None), ('', 'TEAMS'), (None, ' ')]:
        cdr_source.sdr(setuptime=timezone.now(), ingressipgroup=ingress, egressipgroup=egress)

    ingress = admin_client.get(f'{URL}ingress-ip-groups/').json()
    egress = admin_client.get(f'{URL}egress-ip-groups/').json()

    assert ingress['results'] == ['Alpha', 'beta']
    assert ingress['stale'] is False
    assert egress['results'] == ['PBX', 'TEAMS']


def test_termination_reasons_use_recent_window_across_all_four_columns(admin_client, cdr_source):
    now = timezone.now()
    cdr_source.sdr(setuptime=now, ingressterminationreason='GWAPP_NORMAL_CALL_CLEAR', egresssipterminationreason='BYE')
    cdr_source.sdr(setuptime=now, egressterminationreason='GWAPP_USER_BUSY', ingresssipterminationreason='486')
    cdr_source.sdr(setuptime=now - timedelta(days=60), egressterminationreason='OLD_REASON')

    body = admin_client.get(f'{URL}termination-reasons/').json()

    assert body['results'] == ['486', 'BYE', 'GWAPP_NORMAL_CALL_CLEAR', 'GWAPP_USER_BUSY']
    assert body['window_days'] == 30


def test_lookups_are_cached(admin_client, cdr_source):
    cdr_source.sdr(setuptime=timezone.now(), ingressipgroup='FIRST')
    assert admin_client.get(f'{URL}ingress-ip-groups/').json()['results'] == ['FIRST']

    cdr_source.sdr(setuptime=timezone.now(), ingressipgroup='SECOND')
    assert admin_client.get(f'{URL}ingress-ip-groups/').json()['results'] == ['FIRST']


def test_lookup_failure_serves_last_good_values(admin_client, cdr_source, module_settings, monkeypatch):
    cdr_source.sdr(setuptime=timezone.now(), ingressipgroup='CACHED')
    admin_client.get(f'{URL}ingress-ip-groups/')
    monkeypatch.setattr(lookups, 'cache_get', _drop_fresh_entries(lookups.cache_get))
    monkeypatch.setattr(lookups, '_distinct_values', _raise_unavailable)

    body = admin_client.get(f'{URL}ingress-ip-groups/').json()

    assert body['results'] == ['CACHED']
    assert body['stale'] is True
    assert body['error_code'] == 'source_unavailable'


def test_lookup_failure_without_cache_returns_controlled_error(admin_client, cdr_source, monkeypatch):
    monkeypatch.setattr(lookups, '_distinct_values', _raise_unavailable)

    response = admin_client.get(f'{URL}egress-ip-groups/')

    assert response.status_code == 503
    assert response.json()['error_code'] == 'source_unavailable'


def _drop_fresh_entries(cache_get):
    return lambda key: cache_get(key) if key.endswith(':last-good') else None


def _raise_unavailable(*args, **kwargs):
    raise SourceUnavailable()
