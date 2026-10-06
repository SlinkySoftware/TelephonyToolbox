# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

"""SDR statistics. One SDR is one call, bucketed by ``setuptime`` (null setup times never match the range).

Aggregation runs in the database through the ORM so it works on PostgreSQL and the SQLite test
database alike. SDR ``callduration`` is text: only numeric strings are cast and averaged.
"""

from datetime import UTC

from django.db.models import Avg, BigIntegerField, Case, Count, Q, When
from django.db.models.functions import Cast, TruncDay, TruncHour
from django.utils import timezone

from audiocodes_cdr.caching import cache_get, cache_set, make_key
from audiocodes_cdr.connection import source_session
from audiocodes_cdr.constants import SYDNEY, TERMINATION_FIELDS
from audiocodes_cdr.search import applied_filters, build_filter_q
from audiocodes_cdr.source_models import Sdr
from audiocodes_cdr.timeutils import BUCKET_HOUR, bucket_key, choose_bucket, generate_buckets, to_sydney_iso

# Bounded so the cast can never overflow bigint.
VALID_DURATION_Q = Q(callduration__regex=r'^[0-9]{1,15}$')
IP_GROUP_LIMIT = 100
TOP_TERMINATION_REASONS = 10
DURATION_UNIT = 'hundredths_of_second'

EMPTY_METRICS = {
    'total': 0,
    'successful': 0,
    'unsuccessful': 0,
    'unknown': 0,
    'call_duration_samples': 0,
    'avg_call_duration': None,
    'time_to_connect_samples': 0,
    'avg_time_to_connect': None,
}


def _outcome_counts():
    return {
        'total': Count('id'),
        'successful': Count('id', filter=Q(issuccess=True)),
        'unsuccessful': Count('id', filter=Q(issuccess=False)),
        'unknown': Count('id', filter=Q(issuccess__isnull=True)),
    }


def _metrics():
    numeric_duration = Case(
        When(VALID_DURATION_Q, then=Cast('callduration', BigIntegerField())),
        default=None,
        output_field=BigIntegerField(),
    )
    return {
        **_outcome_counts(),
        'call_duration_samples': Count('id', filter=VALID_DURATION_Q),
        'avg_call_duration': Avg(numeric_duration),
        'time_to_connect_samples': Count('timetoconnect'),
        'avg_time_to_connect': Avg('timetoconnect'),
    }


def _round(value):
    return round(float(value), 2) if value is not None else None


def finalize_metrics(row):
    total = row['total']
    known = row['successful'] + row['unsuccessful']
    return {
        'total': total,
        'successful': row['successful'],
        'unsuccessful': row['unsuccessful'],
        'unknown': row['unknown'],
        # Unknown outcomes are excluded from the success-rate denominator.
        'success_rate': round(row['successful'] * 100 / known, 2) if known else None,
        'avg_call_duration': _round(row['avg_call_duration']),
        'call_duration_samples': row['call_duration_samples'],
        'call_duration_excluded': total - row['call_duration_samples'],
        'avg_time_to_connect': _round(row['avg_time_to_connect']),
        'time_to_connect_samples': row['time_to_connect_samples'],
        'time_to_connect_excluded': total - row['time_to_connect_samples'],
    }


def _base_queryset(filters):
    return Sdr.objects.filter(build_filter_q(filters))


def _cached(kind, filters, module_settings, compute):
    summary = applied_filters(filters)
    key = make_key(f'stats:{kind}', module_settings.config_version, summary)
    cached = cache_get(key)
    if cached is not None:
        return {**cached, 'cached': True}

    with source_session(module_settings):
        payload = compute()
    payload.update(filters=summary, units={'duration': DURATION_UNIT}, generated_at=timezone.now().isoformat())
    cache_set(key, payload, module_settings.statistics_cache_seconds)
    return {**payload, 'cached': False}


def summary(filters, module_settings):
    def compute():
        row = _base_queryset(filters).aggregate(**_metrics())
        return {'summary': finalize_metrics(row)}

    return _cached('summary', filters, module_settings, compute)


def timeseries(filters, module_settings):
    start, end = filters['start'], filters['end']
    bucket = choose_bucket(start, end, module_settings.hourly_bucket_max_hours)

    def compute():
        trunc = TruncHour('setuptime', tzinfo=UTC) if bucket == BUCKET_HOUR else TruncDay('setuptime', tzinfo=SYDNEY)
        rows = (
            _base_queryset(filters)
            .annotate(bucket_start=trunc)
            .values('bucket_start')
            .annotate(**_metrics())
            .order_by('bucket_start')
        )
        by_key = {bucket_key(bucket, row['bucket_start']): row for row in rows}
        points = [
            {'start': to_sydney_iso(bucket_start), 'end': to_sydney_iso(bucket_end), **finalize_metrics(by_key.get(key, EMPTY_METRICS))}
            for key, bucket_start, bucket_end in generate_buckets(start, end, bucket)
        ]
        return {'bucket': bucket, 'hourly_bucket_max_hours': module_settings.hourly_bucket_max_hours, 'points': points}

    return _cached('timeseries', filters, module_settings, compute)


def ip_groups(filters, module_settings):
    def grouped(field):
        rows = (
            _base_queryset(filters)
            .values(field)
            .annotate(**_outcome_counts())
            .order_by('-total', field)[:IP_GROUP_LIMIT]
        )
        return [
            {'ip_group': row[field], **{name: row[name] for name in ('total', 'successful', 'unsuccessful', 'unknown')}}
            for row in rows
        ]

    def compute():
        return {'ingress': grouped('ingressipgroup'), 'egress': grouped('egressipgroup'), 'limit': IP_GROUP_LIMIT}

    return _cached('ip-groups', filters, module_settings, compute)


def termination_reasons(filters, module_settings):
    def top(field):
        rows = (
            _base_queryset(filters)
            .exclude(**{f'{field}__isnull': True})
            .exclude(**{field: ''})
            .values(field)
            .annotate(total=Count('id'))
            .order_by('-total', field)[:TOP_TERMINATION_REASONS]
        )
        return [{'value': row[field], 'total': row['total']} for row in rows]

    def compute():
        return {'limit': TOP_TERMINATION_REASONS, 'fields': {field: top(field) for field in TERMINATION_FIELDS}}

    return _cached('termination-reasons', filters, module_settings, compute)
