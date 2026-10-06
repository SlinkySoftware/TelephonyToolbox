# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

from datetime import UTC, datetime, timedelta

import pytest

from audiocodes_cdr.timeutils import BUCKET_DAY, BUCKET_HOUR, choose_bucket, generate_buckets, resolve_preset

BASE = '/api/admin/cdr/statistics/'


def _utc(*args):
    return datetime(*args, tzinfo=UTC)


def _get(client, kind, params):
    response = client.get(f'{BASE}{kind}/', params)
    assert response.status_code == 200, response.json()
    return response.json()


@pytest.fixture
def day_of_calls(cdr_source):
    s = cdr_source
    s.sdr(setuptime=_utc(2026, 7, 1, 1, 10), issuccess=True, callduration='100', timetoconnect=200,
          ingressipgroup='CARRIER_A', egressipgroup='PBX', egressterminationreason='GWAPP_NORMAL_CALL_CLEAR')
    s.sdr(setuptime=_utc(2026, 7, 1, 1, 20), issuccess=True, callduration='300', timetoconnect=400,
          ingressipgroup='CARRIER_A', egressipgroup='PBX', egressterminationreason='GWAPP_NORMAL_CALL_CLEAR')
    s.sdr(setuptime=_utc(2026, 7, 1, 3, 5), issuccess=False, callduration='', ingressipgroup='CARRIER_B',
          egressipgroup='PBX', egressterminationreason='GWAPP_USER_BUSY', egresssipterminationreason='486')
    s.sdr(setuptime=_utc(2026, 7, 1, 3, 15), issuccess=None, callduration='abc', ingressipgroup='CARRIER_A')
    s.sdr(setuptime=_utc(2026, 7, 1, 3, 25), issuccess=False, callduration='99999999999999999999')
    s.sdr(setuptime=_utc(2026, 7, 1, 3, 35), issuccess=False, callduration=None)
    s.sdr(setuptime=None, connecttime=_utc(2026, 7, 1, 2, 0), issuccess=True, callduration='5000')


RANGE = {'start': '2026-07-01T01:00:00Z', 'end': '2026-07-01T04:00:00Z'}


def test_summary_counts_and_averages(admin_client, day_of_calls):
    summary = _get(admin_client, 'summary', RANGE)['summary']

    assert summary['total'] == 6
    assert summary['successful'] == 2
    assert summary['unsuccessful'] == 3
    assert summary['unknown'] == 1
    assert summary['success_rate'] == 40.0
    assert summary['avg_call_duration'] == 200.0
    assert summary['call_duration_samples'] == 2
    assert summary['call_duration_excluded'] == 4
    assert summary['avg_time_to_connect'] == 300.0
    assert summary['time_to_connect_excluded'] == 4


def test_summary_response_includes_metadata(admin_client, day_of_calls):
    body = _get(admin_client, 'summary', RANGE)

    assert body['units'] == {'duration': 'hundredths_of_second'}
    assert body['filters']['start'] == '2026-07-01T11:00:00+10:00'
    assert body['cached'] is False
    assert _get(admin_client, 'summary', RANGE)['cached'] is True


def test_hourly_timeseries_zero_fills(admin_client, day_of_calls):
    body = _get(admin_client, 'timeseries', RANGE)

    assert body['bucket'] == 'hour'
    assert [point['total'] for point in body['points']] == [2, 0, 4]
    assert body['points'][0]['start'] == '2026-07-01T11:00:00+10:00'
    assert body['points'][1]['success_rate'] is None
    assert body['points'][2]['unknown'] == 1


def test_statistics_reuse_search_filters(admin_client, day_of_calls):
    summary = _get(admin_client, 'summary', {**RANGE, 'ingress_ip_group': 'CARRIER_A'})['summary']

    assert summary['total'] == 3


def test_ip_group_statistics(admin_client, day_of_calls):
    body = _get(admin_client, 'ip-groups', RANGE)

    assert body['ingress'][0] == {'ip_group': 'CARRIER_A', 'total': 3, 'successful': 2, 'unsuccessful': 0, 'unknown': 1}
    egress = {row['ip_group']: row['total'] for row in body['egress']}
    assert egress == {'PBX': 3, None: 3}


def test_top_termination_reasons(admin_client, day_of_calls):
    fields = _get(admin_client, 'termination-reasons', RANGE)['fields']

    assert fields['egressterminationreason'] == [
        {'value': 'GWAPP_NORMAL_CALL_CLEAR', 'total': 2},
        {'value': 'GWAPP_USER_BUSY', 'total': 1},
    ]
    assert fields['egresssipterminationreason'] == [{'value': '486', 'total': 1}]
    assert fields['ingressterminationreason'] == []


def test_daily_buckets_for_long_ranges_use_sydney_midnight(admin_client, cdr_source):
    # 2026-04-05 is the DST-end day in Sydney (25 hours long).
    cdr_source.sdr(setuptime=datetime.fromisoformat('2026-04-05T00:30:00+11:00'), issuccess=True)
    cdr_source.sdr(setuptime=datetime.fromisoformat('2026-04-05T23:30:00+10:00'), issuccess=True)
    cdr_source.sdr(setuptime=datetime.fromisoformat('2026-04-06T00:30:00+10:00'), issuccess=True)

    body = _get(admin_client, 'timeseries', {'start': '2026-04-01T00:00:00', 'end': '2026-04-11T00:00:00'})

    assert body['bucket'] == 'day'
    assert len(body['points']) == 10
    by_start = {point['start']: point for point in body['points']}
    dst_end_day = by_start['2026-04-05T00:00:00+11:00']
    assert dst_end_day['end'] == '2026-04-06T00:00:00+10:00'
    assert dst_end_day['total'] == 2
    assert by_start['2026-04-06T00:00:00+10:00']['total'] == 1


def test_hourly_buckets_keep_repeated_dst_hour_separate(admin_client, cdr_source):
    cdr_source.sdr(setuptime=datetime.fromisoformat('2026-04-05T02:10:00+11:00'), issuccess=True)
    cdr_source.sdr(setuptime=datetime.fromisoformat('2026-04-05T02:10:00+10:00'), issuccess=False)

    body = _get(admin_client, 'timeseries', {'start': '2026-04-05T00:00:00+11:00', 'end': '2026-04-05T06:00:00+10:00'})
    by_start = {point['start']: point for point in body['points']}

    assert len(body['points']) == 7
    assert by_start['2026-04-05T02:00:00+11:00']['successful'] == 1
    assert by_start['2026-04-05T02:00:00+10:00']['unsuccessful'] == 1


def test_dst_start_day_has_23_hourly_buckets():
    start = datetime.fromisoformat('2026-10-04T00:00:00+10:00')
    end = datetime.fromisoformat('2026-10-05T00:00:00+11:00')

    assert len(generate_buckets(start, end, BUCKET_HOUR)) == 23
    assert len(generate_buckets(start, end, BUCKET_DAY)) == 1


def test_bucket_threshold_is_inclusive_of_seven_days():
    start = _utc(2026, 7, 1)
    assert choose_bucket(start, start + timedelta(hours=168), 168) == BUCKET_HOUR
    assert choose_bucket(start, start + timedelta(hours=168, seconds=1), 168) == BUCKET_DAY


def test_partial_edge_buckets_are_clamped_to_the_range():
    start = _utc(2026, 7, 1, 1, 30)
    end = _utc(2026, 7, 1, 3, 15)

    buckets = generate_buckets(start, end, BUCKET_HOUR)

    assert buckets[0][1] == start
    assert buckets[-1][2] == end
    assert len(buckets) == 3


def test_last_month_preset_is_previous_calendar_month_in_sydney():
    start, end = resolve_preset('last_month', now=_utc(2026, 10, 6, 1, 0))

    assert start == datetime.fromisoformat('2026-09-01T00:00:00+10:00')
    assert end == datetime.fromisoformat('2026-10-01T00:00:00+10:00')

    # 1 March 00:30 in Sydney is still 28 Feb in UTC.
    start, end = resolve_preset('last_month', now=datetime.fromisoformat('2026-03-01T00:30:00+11:00'))
    assert start == datetime.fromisoformat('2026-02-01T00:00:00+11:00')
    assert end == datetime.fromisoformat('2026-03-01T00:00:00+11:00')


def test_rolling_presets():
    now = _utc(2026, 7, 1, 12, 34, 56)
    start, end = resolve_preset('last_24h', now=now)

    assert end == _utc(2026, 7, 1, 12, 35)
    assert end - start == timedelta(hours=24)
    start, end = resolve_preset('last_7d', now=now)
    assert end - start == timedelta(days=7)
    start, _ = resolve_preset('today', now=now)
    assert start == datetime.fromisoformat('2026-07-01T00:00:00+10:00')


def test_statistics_reject_invalid_ranges(admin_client, cdr_source):
    response = admin_client.get(f'{BASE}summary/', {'start': '2025-01-01T00:00:00Z', 'end': '2026-06-01T00:00:00Z'})

    assert response.status_code == 400
    assert response.json()['error_code'] == 'range_too_large'


def test_empty_range_returns_zero_points(admin_client, cdr_source):
    body = _get(admin_client, 'timeseries', RANGE)

    assert [point['total'] for point in body['points']] == [0, 0, 0]
    assert _get(admin_client, 'summary', RANGE)['summary']['avg_call_duration'] is None
