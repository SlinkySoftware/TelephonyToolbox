# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

"""SDR session detail: the SDR by primary key plus every CDR sharing its ``sessionid``."""

from collections import Counter

from django.db.models import F

from audiocodes_cdr.connection import source_errors, source_session
from audiocodes_cdr.display import (
    DIRECTION_LABELS,
    DIRECTION_UNKNOWN,
    classify_direction,
    effective_start,
    is_blank,
    number_change,
    outcome,
    parse_tags,
    sdr_summary_display,
)
from audiocodes_cdr.exceptions import CdrSourceError, SdrNotFound
from audiocodes_cdr.source_models import CDR_FIELDS, SDR_FIELDS, Cdr, Sdr

MAX_BIGINT = 2**63 - 1
SEVERITY_INFO = 'info'
SEVERITY_WARNING = 'warning'


def _stripped(value):
    return None if is_blank(value) else value.strip()


def detect_anomalies(sdr, cdrs):
    """Correlation diagnostics. They never exclude a CDR. ``cdrs`` is None when the CDR query failed."""
    anomalies = []

    def add(code, severity, message, cdr_ids=None):
        anomalies.append({'code': code, 'severity': severity, 'message': message, 'cdr_ids': cdr_ids or []})

    if is_blank(sdr['sessionid']):
        add('sdr_blank_sessionid', SEVERITY_WARNING, 'The SDR has a blank session ID, so no CDRs can be correlated.')
    if cdrs is None:
        return anomalies
    if not cdrs and not is_blank(sdr['sessionid']):
        add('no_matching_cdrs', SEVERITY_WARNING, 'No CDRs share this SDR session ID.')

    leg_counts = Counter(cdr['legid'] for cdr in cdrs if cdr['legid'] is not None)
    duplicates = sorted(legid for legid, count in leg_counts.items() if count > 1)
    if duplicates:
        add(
            'duplicate_legid',
            SEVERITY_WARNING,
            f'Duplicate leg IDs: {", ".join(str(legid) for legid in duplicates)}.',
            [cdr['id'] for cdr in cdrs if cdr['legid'] in duplicates],
        )

    blank_legs = [cdr['id'] for cdr in cdrs if cdr['legid'] is None]
    if blank_legs:
        add('cdr_blank_legid', SEVERITY_INFO, 'One or more CDRs have a blank leg ID.', blank_legs)

    sdr_global_id = _stripped(sdr['globalsessionid'])
    different_global = [
        cdr['id'] for cdr in cdrs
        if _stripped(cdr['globalsessionid']) is not None and _stripped(cdr['globalsessionid']) != sdr_global_id
    ]
    if different_global:
        add('cdr_globalsessionid_mismatch', SEVERITY_WARNING, 'One or more CDRs have a different Global Session ID from the SDR.', different_global)

    if sdr_global_id is not None:
        blank_global = [cdr['id'] for cdr in cdrs if _stripped(cdr['globalsessionid']) is None]
        if blank_global:
            add('cdr_blank_globalsessionid', SEVERITY_INFO, 'One or more CDRs have a blank Global Session ID while the SDR has one.', blank_global)

    unknown_direction = [cdr['id'] for cdr in cdrs if classify_direction(cdr['callorig']) == DIRECTION_UNKNOWN]
    if unknown_direction:
        add('cdr_unknown_callorig', SEVERITY_WARNING, 'One or more CDRs have an unknown call origin (expected RMT or LCL).', unknown_direction)

    sdr_call_ids = {value for value in (_stripped(sdr['ingresscallid']), _stripped(sdr['egresscallid'])) if value}
    if cdrs and sdr_call_ids and not any(_stripped(cdr['callid']) in sdr_call_ids for cdr in cdrs):
        add('no_matching_callid', SEVERITY_WARNING, 'No CDR Call-ID matches the SDR ingress or egress Call-ID.')

    return anomalies


def anomaly_level(anomalies):
    severities = {anomaly['severity'] for anomaly in anomalies}
    if SEVERITY_WARNING in severities:
        return SEVERITY_WARNING
    if SEVERITY_INFO in severities:
        return SEVERITY_INFO
    return 'none'


def serialize_sdr(row):
    return {
        'raw': row,
        'display': {
            **sdr_summary_display(row),
            'number_changes': {
                'ani': number_change(row['ingressani'], row['egressani']),
                'dnis': number_change(row['ingressdnis'], row['egressdnis']),
            },
        },
    }


def serialize_cdr(row):
    direction = classify_direction(row['callorig'])
    start, start_source = effective_start(row)
    return {
        'raw': row,
        'display': {
            'direction': direction,
            'direction_label': DIRECTION_LABELS[direction],
            'outcome': outcome(row['callsuccess']),
            'effective_start': start,
            'effective_start_source': start_source,
        },
        'parsed_tags': {
            'sourcetags': parse_tags(row['sourcetags']),
            'destinationtags': parse_tags(row['destinationtags']),
        },
    }


def _fetch_cdrs(sessionid):
    ordered = Cdr.objects.filter(sessionid=sessionid).order_by(F('legid').asc(nulls_last=True), 'id')
    return list(ordered.values(*CDR_FIELDS))


def get_session_detail(sdr_id, module_settings):
    if sdr_id < 1 or sdr_id > MAX_BIGINT:
        raise SdrNotFound()

    with source_session(module_settings):
        sdr = Sdr.objects.filter(pk=sdr_id).values(*SDR_FIELDS).first()
    if sdr is None:
        raise SdrNotFound()

    cdrs, cdrs_error = [], None
    if not is_blank(sdr['sessionid']):
        # The SDR stays visible if the (potentially slow) CDR lookup fails.
        try:
            with source_errors():
                cdrs = _fetch_cdrs(sdr['sessionid'])
        except CdrSourceError as exc:
            cdrs, cdrs_error = None, {'detail': exc.message, 'error_code': exc.error_code}

    anomalies = detect_anomalies(sdr, cdrs)
    return {
        'sdr': serialize_sdr(sdr),
        'cdrs': [serialize_cdr(row) for row in cdrs] if cdrs is not None else None,
        'cdrs_error': cdrs_error,
        'anomalies': anomalies,
        'anomaly_level': anomaly_level(anomalies),
    }
