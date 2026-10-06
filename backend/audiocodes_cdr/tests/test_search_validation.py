# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

from datetime import UTC, datetime

import pytest

from audiocodes_cdr.timeutils import NonexistentLocalTime, parse_datetime_value, range_exceeds_limit

URL = '/api/admin/cdr/sdr/'
DAY = {'start': '2026-07-01T00:00:00+10:00', 'end': '2026-07-02T00:00:00+10:00'}


def _errors(response):
    body = response.json()
    assert body['error_code'] in ('invalid_filters', 'range_too_large')
    return body['errors']


def test_missing_range_is_rejected(admin_client, cdr_source):
    response = admin_client.get(URL)

    assert response.status_code == 400
    assert set(_errors(response)) == {'start', 'end'}


def test_end_before_start_is_rejected(admin_client, cdr_source):
    response = admin_client.get(URL, {'start': DAY['end'], 'end': DAY['start']})

    assert response.status_code == 400
    assert 'end' in _errors(response)


def test_range_over_twelve_months_is_rejected(admin_client, cdr_source):
    response = admin_client.get(URL, {'start': '2025-07-01T00:00:00+10:00', 'end': '2026-07-01T00:00:01+10:00'})

    assert response.status_code == 400
    assert response.json()['error_code'] == 'range_too_large'


def test_range_of_exactly_twelve_months_is_allowed(admin_client, cdr_source):
    response = admin_client.get(URL, {'start': '2025-07-01T00:00:00+10:00', 'end': '2026-07-01T00:00:00+10:00'})

    assert response.status_code == 200


@pytest.mark.parametrize(
    'params, field',
    [
        ({'ani': '02', 'ani_match': 'regex'}, 'ani_match'),
        ({'dnis_match': 'like'}, 'dnis_match'),
        ({'call_id_match': 'fuzzy'}, 'call_id_match'),
        ({'status': 'maybe'}, 'status'),
        ({'sort': 'sourceip'}, 'sort'),
        ({'sort': 'setuptime; DROP TABLE sdr'}, 'sort'),
        ({'direction': 'sideways'}, 'direction'),
        ({'page': 0}, 'page'),
        ({'page_size': 33}, 'page_size'),
        ({'page_size': 1000}, 'page_size'),
        ({'start': 'yesterday-ish'}, 'start'),
        ({'preset': 'forever'}, 'preset'),
    ],
)
def test_invalid_parameters_are_rejected(admin_client, cdr_source, params, field):
    response = admin_client.get(URL, {**DAY, **params})

    assert response.status_code == 400
    assert field in _errors(response)


def test_page_size_is_limited_by_module_settings(admin_client, cdr_source, module_settings):
    module_settings.max_page_size = 100
    module_settings.save()

    assert admin_client.get(URL, {**DAY, 'page_size': 100}).status_code == 200
    response = admin_client.get(URL, {**DAY, 'page_size': 250})
    assert response.status_code == 400
    assert 'page_size' in _errors(response)


def test_multiselect_is_limited_by_module_settings(admin_client, cdr_source, module_settings):
    module_settings.max_multiselect_values = 2
    module_settings.save()

    response = admin_client.get(URL, {**DAY, 'ingress_ip_group': ['A', 'B', 'C']})
    assert response.status_code == 400
    assert 'ingress_ip_group' in _errors(response)

    duplicates = admin_client.get(URL, {**DAY, 'ingress_ip_group': ['A', 'A', 'B']})
    assert duplicates.status_code == 200
    assert duplicates.json()['filters']['ingress_ip_group'] == ['A', 'B']


def test_bracketed_multi_value_params_are_accepted(admin_client, cdr_source):
    response = admin_client.get(URL, {**DAY, 'egress_ip_group[]': ['X', 'Y']})

    assert response.status_code == 200
    assert response.json()['filters']['egress_ip_group'] == ['X', 'Y']


def test_preset_today_resolves_to_sydney_midnight(admin_client, cdr_source):
    response = admin_client.get(URL, {'preset': 'today'})

    assert response.status_code == 200
    filters = response.json()['filters']
    assert filters['preset'] == 'today'
    assert 'T00:00:00' in filters['start']


def test_defaults_are_applied(admin_client, cdr_source):
    body = admin_client.get(URL, DAY).json()

    assert body['page'] == 1
    assert body['page_size'] == 100
    assert body['sort'] == {'field': 'setuptime', 'direction': 'desc'}
    assert body['filters']['status'] == 'all'


def test_naive_times_are_sydney_local_time():
    assert parse_datetime_value('2026-01-15T00:00:00') == datetime(2026, 1, 14, 13, 0, tzinfo=UTC)  # AEDT +11
    assert parse_datetime_value('2026-07-15T00:00:00') == datetime(2026, 7, 14, 14, 0, tzinfo=UTC)  # AEST +10
    assert parse_datetime_value('2026-07-15T00:00:00Z') == datetime(2026, 7, 15, 0, 0, tzinfo=UTC)


def test_nonexistent_local_time_at_dst_start_is_rejected(admin_client, cdr_source):
    with pytest.raises(NonexistentLocalTime):
        parse_datetime_value('2026-10-04T02:30:00')

    response = admin_client.get(URL, {'start': '2026-10-04T02:30:00', 'end': '2026-10-05T00:00:00'})
    assert response.status_code == 400
    assert 'start' in _errors(response)


def test_ambiguous_local_time_at_dst_end_uses_first_occurrence():
    assert parse_datetime_value('2026-04-05T02:30:00') == datetime(2026, 4, 4, 15, 30, tzinfo=UTC)  # still AEDT


def test_twelve_month_limit_clamps_to_month_end():
    start = parse_datetime_value('2025-02-28T00:00:00')
    assert not range_exceeds_limit(start, parse_datetime_value('2026-02-28T00:00:00'))
    assert range_exceeds_limit(start, parse_datetime_value('2026-02-28T00:00:01'))

    leap_start = parse_datetime_value('2024-02-29T00:00:00')
    assert not range_exceeds_limit(leap_start, parse_datetime_value('2025-02-28T00:00:00'))
    assert range_exceeds_limit(leap_start, parse_datetime_value('2025-03-01T00:00:00'))
