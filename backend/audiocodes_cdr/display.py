# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

"""Derived display values. These are returned separately from raw source fields and never replace them."""

from audiocodes_cdr.constants import TERMINATION_FIELDS

OUTCOME_SUCCESSFUL = 'successful'
OUTCOME_UNSUCCESSFUL = 'unsuccessful'
OUTCOME_UNKNOWN = 'unknown'

DIRECTION_INBOUND = 'inbound'
DIRECTION_OUTBOUND = 'outbound'
DIRECTION_UNKNOWN = 'unknown'
DIRECTION_LABELS = {
    DIRECTION_INBOUND: 'Inbound (remotely originated)',
    DIRECTION_OUTBOUND: 'Outbound (locally originated)',
    DIRECTION_UNKNOWN: 'Unknown',
}
CALLORIG_DIRECTIONS = {'RMT': DIRECTION_INBOUND, 'LCL': DIRECTION_OUTBOUND}


def is_blank(value):
    return value is None or (isinstance(value, str) and not value.strip())


def outcome(value):
    if value is True:
        return OUTCOME_SUCCESSFUL
    if value is False:
        return OUTCOME_UNSUCCESSFUL
    return OUTCOME_UNKNOWN


def classify_direction(callorig):
    if is_blank(callorig):
        return DIRECTION_UNKNOWN
    return CALLORIG_DIRECTIONS.get(callorig.strip().upper(), DIRECTION_UNKNOWN)


def effective_start(row):
    """Setup time when present, otherwise connect time, with the source field identified."""
    if row.get('setuptime') is not None:
        return row['setuptime'], 'setuptime'
    if row.get('connecttime') is not None:
        return row['connecttime'], 'connecttime'
    return None, None


def termination_summary(row):
    """Distinct non-blank SDR termination values, each listing every field that reported it."""
    summary = []
    by_value = {}
    for field in TERMINATION_FIELDS:
        value = row.get(field)
        if is_blank(value):
            continue
        if value in by_value:
            by_value[value]['fields'].append(field)
            continue
        entry = {'value': value, 'fields': [field]}
        by_value[value] = entry
        summary.append(entry)
    return summary


def number_change(ingress, egress):
    if is_blank(ingress) or is_blank(egress):
        return 'unknown'
    return 'unchanged' if ingress == egress else 'changed'


def parse_tags(value):
    """Parse ``KEY=VALUE;KEY=VALUE`` defensively: split on the first ``=``, keep malformed entries as-is."""
    if value is None:
        return None
    entries = []
    for segment in value.split(';'):
        if segment == '':
            continue
        if '=' in segment:
            key, tag_value = segment.split('=', 1)
            entries.append({'key': key, 'value': tag_value, 'malformed': False})
        else:
            entries.append({'key': None, 'value': segment, 'malformed': True})
    return entries


def sdr_summary_display(row):
    start, start_source = effective_start(row)
    return {
        'outcome': outcome(row.get('issuccess')),
        'effective_start': start,
        'effective_start_source': start_source,
        'termination_summary': termination_summary(row),
    }
