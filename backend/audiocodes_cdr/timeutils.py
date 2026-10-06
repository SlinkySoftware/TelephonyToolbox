# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

"""Australia/Sydney time handling for CDR searches and statistics.

Database predicates always use timezone-aware instants; local wall-clock values are only used
to derive boundaries (midnights, calendar months) in Australia/Sydney.
"""

import calendar
from datetime import UTC, datetime, time, timedelta

from django.utils import timezone

from audiocodes_cdr.constants import MAX_RANGE_MONTHS, SYDNEY

PRESETS = ('today', 'last_24h', 'last_48h', 'last_7d', 'last_month')
BUCKET_HOUR = 'hour'
BUCKET_DAY = 'day'


class NonexistentLocalTime(ValueError):
    pass


def parse_datetime_value(value):
    """Parse ISO 8601. Values without an offset are Australia/Sydney wall-clock time.

    Ambiguous wall-clock times (DST end) resolve to the first occurrence; non-existent times
    (DST start gap) are rejected. Clients should send explicit offsets to avoid both cases.
    """
    parsed = datetime.fromisoformat(value.strip())
    if parsed.tzinfo is not None:
        return parsed.astimezone(UTC)

    local = parsed.replace(tzinfo=SYDNEY, fold=0)
    if local.astimezone(UTC).astimezone(SYDNEY).replace(tzinfo=None) != parsed:
        raise NonexistentLocalTime('This local time does not exist in Australia/Sydney.')
    return local.astimezone(UTC)


def to_sydney(value):
    return value.astimezone(SYDNEY) if value is not None else None


def to_sydney_iso(value):
    return value.astimezone(SYDNEY).isoformat() if value is not None else None


def sydney_midnight(day):
    return datetime.combine(day, time.min, tzinfo=SYDNEY)


def add_months(value, months):
    """Add calendar months in Australia/Sydney, clamping the day to the end of the month."""
    local = value.astimezone(SYDNEY)
    month_index = local.month - 1 + months
    year = local.year + month_index // 12
    month = month_index % 12 + 1
    day = min(local.day, calendar.monthrange(year, month)[1])
    return datetime(year, month, day, local.hour, local.minute, local.second, local.microsecond, tzinfo=SYDNEY)


def range_exceeds_limit(start, end, months=MAX_RANGE_MONTHS):
    return end > add_months(start, months)


def _preset_end(now):
    # Rounded up to the next minute so repeated preset requests share a statistics cache entry.
    return now.replace(second=0, microsecond=0) + timedelta(minutes=1)


def resolve_preset(name, now=None):
    now = now or timezone.now()
    end = _preset_end(now)
    local_today = now.astimezone(SYDNEY).date()
    if name == 'today':
        return sydney_midnight(local_today).astimezone(UTC), end
    if name == 'last_24h':
        return end - timedelta(hours=24), end
    if name == 'last_48h':
        return end - timedelta(hours=48), end
    if name == 'last_7d':
        return end - timedelta(days=7), end
    if name == 'last_month':
        this_month = local_today.replace(day=1)
        previous_month = (this_month - timedelta(days=1)).replace(day=1)
        return sydney_midnight(previous_month).astimezone(UTC), sydney_midnight(this_month).astimezone(UTC)
    raise ValueError(f'Unknown preset: {name}')


def choose_bucket(start, end, hourly_max_hours):
    return BUCKET_HOUR if end - start <= timedelta(hours=hourly_max_hours) else BUCKET_DAY


def bucket_key(bucket, value):
    """Normalise a bucket start (generated or returned by the database) to a comparable key."""
    if bucket == BUCKET_HOUR:
        return value.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
    return value.astimezone(SYDNEY).date()


def generate_buckets(start, end, bucket):
    """Yield ``(key, bucket_start, bucket_end)`` covering ``[start, end)`` with clamped edges.

    Hourly buckets are aligned in UTC (Sydney offsets are whole hours, so they align locally and
    the repeated 02:00 hour at DST end stays as two buckets). Daily buckets use Sydney midnights.
    """
    buckets = []
    if bucket == BUCKET_HOUR:
        cursor = start.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
        while cursor < end:
            following = cursor + timedelta(hours=1)
            buckets.append((cursor, max(cursor, start), min(following, end)))
            cursor = following
        return buckets

    day = start.astimezone(SYDNEY).date()
    while True:
        bucket_start = sydney_midnight(day)
        if bucket_start >= end:
            break
        day = day + timedelta(days=1)
        bucket_end = sydney_midnight(day)
        buckets.append((bucket_start.date(), max(bucket_start, start), min(bucket_end, end)))
    return buckets
