# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

"""SDR search: bounded setup-time range first, allow-listed filters and sorting, exact count."""

import math
from functools import reduce
from operator import or_

from django.db.models import Q

from audiocodes_cdr.connection import source_session
from audiocodes_cdr.constants import TERMINATION_FIELDS
from audiocodes_cdr.display import sdr_summary_display
from audiocodes_cdr.source_models import Sdr
from audiocodes_cdr.timeutils import to_sydney_iso

TEXT_FILTERS = {
    'ani': (('ingressani', 'egressani'), 'ani_match'),
    'dnis': (('ingressdnis', 'egressdnis'), 'dnis_match'),
    'call_id': (('ingresscallid', 'egresscallid'), 'call_id_match'),
    'termination_text': (TERMINATION_FIELDS, 'termination_match'),
}
MULTI_FILTERS = {
    'ingress_ip_group': ('ingressipgroup',),
    'egress_ip_group': ('egressipgroup',),
    'termination_reason': TERMINATION_FIELDS,
}
STATUS_Q = {
    'successful': Q(issuccess=True),
    'unsuccessful': Q(issuccess=False),
    'unknown': Q(issuccess__isnull=True),
}
SORT_FIELDS = (
    'setuptime',
    'ingressani',
    'ingressdnis',
    'egressani',
    'egressdnis',
    'ingressipgroup',
    'egressipgroup',
    'issuccess',
    'id',
)
RESULT_FIELDS = (
    'id',
    'setuptime',
    'connecttime',
    'releasetime',
    'ingressani',
    'ingressdnis',
    'egressani',
    'egressdnis',
    'ingressipgroup',
    'egressipgroup',
    'ingresscallid',
    'egresscallid',
    'callduration',
    'issuccess',
    *TERMINATION_FIELDS,
)


def _any_field(fields, lookup, value):
    return reduce(or_, (Q(**{f'{field}__{lookup}': value}) for field in fields))


def build_filter_q(filters):
    """Combine filters with AND; directional fields inside one filter are OR'd."""
    q = Q(setuptime__gte=filters['start']) & Q(setuptime__lt=filters['end'])
    for name, fields in MULTI_FILTERS.items():
        values = filters.get(name)
        if values:
            q &= _any_field(fields, 'in', values)
    for name, (fields, match_param) in TEXT_FILTERS.items():
        value = filters.get(name)
        if value:
            q &= _any_field(fields, filters[match_param], value)
    status_q = STATUS_Q.get(filters.get('status'))
    if status_q is not None:
        q &= status_q
    return q


def applied_filters(filters):
    summary = {
        'start': to_sydney_iso(filters['start']),
        'end': to_sydney_iso(filters['end']),
        'preset': filters.get('preset') or None,
        'status': filters.get('status', 'all'),
    }
    for name in MULTI_FILTERS:
        if filters.get(name):
            summary[name] = list(filters[name])
    for name, (_, match_param) in TEXT_FILTERS.items():
        if filters.get(name):
            summary[name] = {'value': filters[name], 'match': filters[match_param]}
    return summary


def _ordering(sort_field, direction):
    prefix = '-' if direction == 'desc' else ''
    if sort_field == 'id':
        return (f'{prefix}id',)
    return (f'{prefix}{sort_field}', f'{prefix}id')


def search_sdrs(filters, module_settings):
    page = filters['page']
    page_size = filters['page_size']
    offset = (page - 1) * page_size
    queryset = Sdr.objects.filter(build_filter_q(filters))

    with source_session(module_settings):
        total = queryset.count()
        rows = []
        if offset < total:
            ordered = queryset.order_by(*_ordering(filters['sort'], filters['direction']))
            rows = list(ordered.values(*RESULT_FIELDS)[offset:offset + page_size])

    return {
        'count': total,
        'page': page,
        'page_size': page_size,
        'total_pages': math.ceil(total / page_size) if total else 0,
        'sort': {'field': filters['sort'], 'direction': filters['direction']},
        'filters': applied_filters(filters),
        'results': [{**row, 'display': sdr_summary_display(row)} for row in rows],
    }
