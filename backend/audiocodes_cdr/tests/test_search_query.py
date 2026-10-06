# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

from datetime import UTC, datetime, timedelta

import pytest

from audiocodes_cdr.search import build_filter_q
from audiocodes_cdr.source_models import Sdr

URL = '/api/admin/cdr/sdr/'
BASE = datetime(2026, 7, 1, 2, 0, tzinfo=UTC)
RANGE = {'start': '2026-07-01T00:00:00Z', 'end': '2026-07-02T00:00:00Z'}


def _at(minutes):
    return BASE + timedelta(minutes=minutes)


@pytest.fixture
def seeded(cdr_source):
    s = cdr_source
    return {
        'a': s.sdr(id=10, setuptime=_at(0), ingressani='0299990000', egressani='+61299990000', ingressdnis='1300123456',
                   egressdnis='+611300123456', ingressipgroup='CARRIER_A', egressipgroup='PBX', issuccess=True,
                   ingresscallid='call-a-in', egresscallid='call-a-out', callduration='37501',
                   ingressterminationreason='GWAPP_NORMAL_CALL_CLEAR', egressterminationreason='GWAPP_NORMAL_CALL_CLEAR',
                   ingresssipterminationreason='BYE', egresssipterminationreason='BYE'),
        'b': s.sdr(id=11, setuptime=_at(10), ingressani='0388881111', egressani='0388881111', ingressdnis='0299990000',
                   egressdnis='0299990000', ingressipgroup='CARRIER_B', egressipgroup='PBX', issuccess=False,
                   egressterminationreason='GWAPP_USER_BUSY', egresssipterminationreason='486'),
        'c': s.sdr(id=12, setuptime=_at(20), ingressani='0411222333', egressani='+61411222333', ingressipgroup='CARRIER_A',
                   egressipgroup='TEAMS', issuccess=None),
        'd_same_time': s.sdr(id=13, setuptime=_at(20), ingressani='0500000000', ingressipgroup='CARRIER_C', issuccess=True),
        'outside': s.sdr(id=14, setuptime=BASE + timedelta(days=2), ingressani='0299990000', issuccess=True),
        'no_setup': s.sdr(id=15, setuptime=None, connecttime=_at(5), ingressani='0299990000', issuccess=True),
    }


def _ids(response):
    assert response.status_code == 200, response.json()
    return [row['id'] for row in response.json()['results']]


def test_range_excludes_outside_and_null_setuptime(admin_client, seeded):
    body = admin_client.get(URL, RANGE).json()

    assert body['count'] == 4
    assert [row['id'] for row in body['results']] == [13, 12, 11, 10]


def test_default_sort_is_setuptime_desc_with_id_tie_break(admin_client, seeded):
    assert _ids(admin_client.get(URL, RANGE))[:2] == [13, 12]
    assert _ids(admin_client.get(URL, {**RANGE, 'direction': 'asc'})) == [10, 11, 12, 13]


def test_sort_by_allowed_column(admin_client, seeded):
    assert _ids(admin_client.get(URL, {**RANGE, 'sort': 'ingressani', 'direction': 'asc'})) == [10, 11, 12, 13]


@pytest.mark.parametrize(
    'match, value, expected',
    [
        ('exact', '0299990000', [10]),
        ('exact', '+61299990000', [10]),
        ('startswith', '+614', [12]),
        ('endswith', '1111', [11]),
        ('contains', '9999', [10]),
    ],
)
def test_ani_match_modes_search_ingress_or_egress(admin_client, seeded, match, value, expected):
    assert _ids(admin_client.get(URL, {**RANGE, 'ani': value, 'ani_match': match})) == expected


def test_dnis_and_call_id_filters(admin_client, seeded):
    assert _ids(admin_client.get(URL, {**RANGE, 'dnis': '0299990000', 'dnis_match': 'exact'})) == [11]
    assert _ids(admin_client.get(URL, {**RANGE, 'call_id': 'call-a-out'})) == [10]
    assert _ids(admin_client.get(URL, {**RANGE, 'call_id': 'call-a', 'call_id_match': 'startswith'})) == [10]


def test_filters_combine_with_and(admin_client, seeded):
    params = {**RANGE, 'ani': '0', 'ani_match': 'startswith', 'ingress_ip_group': 'CARRIER_A', 'egress_ip_group': 'PBX'}

    assert _ids(admin_client.get(URL, params)) == [10]


def test_ip_group_multiselect_uses_in(admin_client, seeded):
    assert _ids(admin_client.get(URL, {**RANGE, 'ingress_ip_group': ['CARRIER_A', 'CARRIER_B']})) == [12, 11, 10]


@pytest.mark.parametrize(
    'status, expected',
    [('successful', [13, 10]), ('unsuccessful', [11]), ('unknown', [12]), ('all', [13, 12, 11, 10])],
)
def test_status_filter(admin_client, seeded, status, expected):
    assert _ids(admin_client.get(URL, {**RANGE, 'status': status})) == expected


def test_termination_filters_search_all_four_columns(admin_client, seeded):
    assert _ids(admin_client.get(URL, {**RANGE, 'termination_reason': ['486']})) == [11]
    assert _ids(admin_client.get(URL, {**RANGE, 'termination_text': 'NORMAL', 'termination_match': 'contains'})) == [10]


def test_pagination_and_exact_count(admin_client, seeded, cdr_source):
    for index in range(30):
        cdr_source.sdr(id=100 + index, setuptime=_at(100 + index), issuccess=True)

    first = admin_client.get(URL, {**RANGE, 'page_size': 25}).json()
    second = admin_client.get(URL, {**RANGE, 'page_size': 25, 'page': 2}).json()
    beyond = admin_client.get(URL, {**RANGE, 'page_size': 25, 'page': 3}).json()

    assert first['count'] == 34
    assert first['total_pages'] == 2
    assert len(first['results']) == 25
    assert len(second['results']) == 9
    assert {row['id'] for row in first['results']}.isdisjoint({row['id'] for row in second['results']})
    assert beyond['results'] == []
    assert beyond['count'] == 34


def test_result_rows_keep_raw_values_and_add_display(admin_client, seeded):
    row = next(row for row in admin_client.get(URL, RANGE).json()['results'] if row['id'] == 10)

    assert row['callduration'] == '37501'
    assert row['display']['outcome'] == 'successful'
    assert row['display']['effective_start_source'] == 'setuptime'
    assert row['display']['termination_summary'] == [
        {'value': 'GWAPP_NORMAL_CALL_CLEAR', 'fields': ['ingressterminationreason', 'egressterminationreason']},
        {'value': 'BYE', 'fields': ['ingresssipterminationreason', 'egresssipterminationreason']},
    ]
    assert 'cdrs' not in row


def test_list_response_shape(admin_client, seeded):
    body = admin_client.get(URL, {**RANGE, 'ani': '02', 'ani_match': 'startswith'}).json()

    assert set(body) == {'count', 'page', 'page_size', 'total_pages', 'sort', 'filters', 'results'}
    assert body['filters']['ani'] == {'value': '02', 'match': 'startswith'}


def test_setuptime_predicate_comes_first(cdr_source):
    filters = {
        'start': BASE,
        'end': BASE + timedelta(days=1),
        'ani': '02',
        'ani_match': 'startswith',
        'ingress_ip_group': ['A'],
        'status': 'unsuccessful',
    }
    sql = str(Sdr.objects.filter(build_filter_q(filters)).query)
    where = sql[sql.index('WHERE'):]

    assert where.index('"setuptime" >=') < where.index('"ingressipgroup"') < where.index('"ingressani"')
