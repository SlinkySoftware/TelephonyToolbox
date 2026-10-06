# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

from datetime import UTC, datetime, timedelta

import pytest
from django.db import OperationalError

from audiocodes_cdr.display import parse_tags
from audiocodes_cdr.source_models import CDR_FIELDS, SDR_FIELDS

START = datetime(2026, 7, 1, 2, 0, 0, 123000, tzinfo=UTC)
SESSION = 'session-1'
GSID = 'gsid-1'


def _url(sdr_id):
    return f'/api/admin/cdr/sdr/{sdr_id}/'


def _clean_session(source, sdr_id=1, session=SESSION):
    source.sdr(id=sdr_id, sessionid=session, globalsessionid=GSID, setuptime=START, issuccess=True,
               ingresscallid='in-call', egresscallid='out-call', ingressani='0299990000', egressani='+61299990000',
               ingressdnis='100', egressdnis='100')
    source.cdr(id=500, sessionid=session, globalsessionid=GSID, legid=1, callorig='RMT', callid='in-call', callsuccess=True,
               sourcetags='ROUTE=GENESYS_01;OWNER=NBNCO;ALLOWEDCLI=GENESYS')
    source.cdr(id=501, sessionid=session, globalsessionid=GSID, legid=2, callorig='LCL', callid='out-call', callsuccess=True)


def _codes(body):
    return {anomaly['code'] for anomaly in body['anomalies']}


def test_clean_session_has_no_anomalies(admin_client, cdr_source):
    _clean_session(cdr_source)

    body = admin_client.get(_url(1)).json()

    assert body['anomalies'] == []
    assert body['anomaly_level'] == 'none'
    assert [cdr['raw']['id'] for cdr in body['cdrs']] == [500, 501]
    assert body['cdrs_error'] is None


def test_every_sdr_field_present_and_nulls_kept(admin_client, cdr_source):
    _clean_session(cdr_source)

    sdr = admin_client.get(_url(1)).json()['sdr']

    assert set(sdr['raw']) == set(SDR_FIELDS)
    assert sdr['raw']['sourceip'] is None
    assert sdr['raw']['setuptime'] == '2026-07-01T02:00:00.123000Z'
    assert sdr['display']['outcome'] == 'successful'
    assert sdr['display']['number_changes'] == {'ani': 'changed', 'dnis': 'unchanged'}


def test_every_cdr_field_present(admin_client, cdr_source):
    _clean_session(cdr_source)

    cdr = admin_client.get(_url(1)).json()['cdrs'][0]

    assert set(cdr['raw']) == set(CDR_FIELDS)
    assert cdr['raw']['sourcetags'] == 'ROUTE=GENESYS_01;OWNER=NBNCO;ALLOWEDCLI=GENESYS'
    assert cdr['parsed_tags']['sourcetags'] == [
        {'key': 'ROUTE', 'value': 'GENESYS_01', 'malformed': False},
        {'key': 'OWNER', 'value': 'NBNCO', 'malformed': False},
        {'key': 'ALLOWEDCLI', 'value': 'GENESYS', 'malformed': False},
    ]
    assert cdr['parsed_tags']['destinationtags'] is None


def test_cdr_ordering_supports_many_legs_and_nulls_last(admin_client, cdr_source):
    cdr_source.sdr(id=1, sessionid=SESSION, setuptime=START)
    for cdr_id, legid in [(600, None), (601, 3), (602, 1), (603, 2), (604, 1)]:
        cdr_source.cdr(id=cdr_id, sessionid=SESSION, legid=legid, callorig='RMT', callsuccess=False)
    cdr_source.cdr(id=700, sessionid='other-session', legid=1)

    body = admin_client.get(_url(1)).json()

    assert [cdr['raw']['id'] for cdr in body['cdrs']] == [602, 604, 603, 601, 600]
    assert {'duplicate_legid', 'cdr_blank_legid'} <= _codes(body)


@pytest.mark.parametrize(
    'callorig, direction',
    [('RMT', 'inbound'), ('LCL', 'outbound'), ('rmt', 'inbound'), ('XYZ', 'unknown'), (None, 'unknown'), ('', 'unknown')],
)
def test_direction_classification_keeps_raw_callorig(admin_client, cdr_source, callorig, direction):
    cdr_source.sdr(id=1, sessionid=SESSION, setuptime=START)
    cdr_source.cdr(id=500, sessionid=SESSION, legid=1, callorig=callorig)

    cdr = admin_client.get(_url(1)).json()['cdrs'][0]

    assert cdr['display']['direction'] == direction
    assert cdr['raw']['callorig'] == callorig


def test_tag_parsing_is_defensive():
    assert parse_tags('A=b=c;malformed;;X=') == [
        {'key': 'A', 'value': 'b=c', 'malformed': False},
        {'key': None, 'value': 'malformed', 'malformed': True},
        {'key': 'X', 'value': '', 'malformed': False},
    ]
    assert parse_tags('') == []
    assert parse_tags(None) is None


def test_blank_sessionid_anomaly(admin_client, cdr_source):
    cdr_source.sdr(id=1, sessionid='  ', setuptime=START)

    body = admin_client.get(_url(1)).json()

    assert body['cdrs'] == []
    assert _codes(body) == {'sdr_blank_sessionid'}
    assert body['anomaly_level'] == 'warning'


def test_no_matching_cdrs_anomaly(admin_client, cdr_source):
    cdr_source.sdr(id=1, sessionid=SESSION, setuptime=START)

    body = admin_client.get(_url(1)).json()

    assert body['cdrs'] == []
    assert _codes(body) == {'no_matching_cdrs'}


def test_global_session_and_call_id_anomalies(admin_client, cdr_source):
    cdr_source.sdr(id=1, sessionid=SESSION, globalsessionid=GSID, setuptime=START, ingresscallid='in-call')
    cdr_source.cdr(id=500, sessionid=SESSION, legid=1, callorig='RMT', globalsessionid='other-gsid', callid='x')
    cdr_source.cdr(id=501, sessionid=SESSION, legid=2, callorig='???', globalsessionid=None, callid='y')

    body = admin_client.get(_url(1)).json()
    by_code = {anomaly['code']: anomaly for anomaly in body['anomalies']}

    assert by_code['cdr_globalsessionid_mismatch']['cdr_ids'] == [500]
    assert by_code['cdr_globalsessionid_mismatch']['severity'] == 'warning'
    assert by_code['cdr_blank_globalsessionid']['cdr_ids'] == [501]
    assert by_code['cdr_blank_globalsessionid']['severity'] == 'info'
    assert by_code['cdr_unknown_callorig']['cdr_ids'] == [501]
    assert 'no_matching_callid' in by_code
    assert len(body['cdrs']) == 2


def test_info_only_anomaly_level(admin_client, cdr_source):
    cdr_source.sdr(id=1, sessionid=SESSION, globalsessionid=GSID, setuptime=START)
    cdr_source.cdr(id=500, sessionid=SESSION, legid=None, callorig='RMT', globalsessionid=GSID)

    body = admin_client.get(_url(1)).json()

    assert _codes(body) == {'cdr_blank_legid'}
    assert body['anomaly_level'] == 'info'


def test_connect_time_fallback(admin_client, cdr_source):
    cdr_source.sdr(id=1, sessionid=SESSION, setuptime=None, connecttime=START + timedelta(seconds=5))

    display = admin_client.get(_url(1)).json()['sdr']['display']

    assert display['effective_start_source'] == 'connecttime'
    assert display['outcome'] == 'unknown'


def test_unknown_sdr_returns_404(admin_client, cdr_source):
    response = admin_client.get(_url(999))

    assert response.status_code == 404
    assert response.json()['error_code'] == 'sdr_not_found'
    assert admin_client.get(_url(2**63)).status_code == 404


def test_cdr_timeout_keeps_sdr_visible(admin_client, cdr_source, monkeypatch):
    cdr_source.sdr(id=1, sessionid=SESSION, setuptime=START)

    class QueryCanceled(Exception):
        sqlstate = '57014'

    def timeout(sessionid):
        error = OperationalError('canceling statement due to statement timeout')
        error.__cause__ = QueryCanceled()
        raise error

    monkeypatch.setattr('audiocodes_cdr.detail._fetch_cdrs', timeout)

    response = admin_client.get(_url(1))
    body = response.json()

    assert response.status_code == 200
    assert body['sdr']['raw']['id'] == 1
    assert body['cdrs'] is None
    assert body['cdrs_error']['error_code'] == 'source_timeout'
    assert 'no_matching_cdrs' not in _codes(body)
