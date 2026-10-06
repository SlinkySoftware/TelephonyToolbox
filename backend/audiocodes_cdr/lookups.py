# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

"""Cached lookup values for filter controls. SDR table only; the CDR table is never scanned."""

from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from audiocodes_cdr.caching import cache_get, cache_set, make_key
from audiocodes_cdr.connection import source_session
from audiocodes_cdr.constants import TERMINATION_FIELDS
from audiocodes_cdr.exceptions import CdrSourceError
from audiocodes_cdr.source_models import Sdr

LOOKUP_LIMIT = 1000
LAST_GOOD_SECONDS = 24 * 60 * 60


def _distinct_values(field, base_q=None):
    queryset = Sdr.objects.all()
    if base_q is not None:
        queryset = queryset.filter(base_q)
    queryset = queryset.exclude(**{f'{field}__isnull': True}).exclude(**{field: ''})
    return list(queryset.order_by().values_list(field, flat=True).distinct()[:LOOKUP_LIMIT])


def _sorted_unique(values):
    return sorted({value for value in values if value.strip()}, key=lambda value: (value.casefold(), value))


def _cached_lookup(kind, module_settings, loader, extra=None):
    key = make_key(f'lookup:{kind}', module_settings.config_version)
    last_good_key = f'{key}:last-good'
    cached = cache_get(key)
    if cached is not None:
        return {**cached, 'stale': False}

    try:
        with source_session(module_settings):
            values = loader()
    except CdrSourceError as exc:
        last_good = cache_get(last_good_key)
        if last_good is None:
            raise
        return {**last_good, 'stale': True, 'detail': exc.message, 'error_code': exc.error_code}

    payload = {'results': values, 'refreshed_at': timezone.now().isoformat(), **(extra or {})}
    cache_set(key, payload, module_settings.lookup_cache_seconds)
    cache_set(last_good_key, payload, LAST_GOOD_SECONDS)
    return {**payload, 'stale': False}


def ingress_ip_groups(module_settings):
    return _cached_lookup('ingress-ip-groups', module_settings, lambda: _sorted_unique(_distinct_values('ingressipgroup')))


def egress_ip_groups(module_settings):
    return _cached_lookup('egress-ip-groups', module_settings, lambda: _sorted_unique(_distinct_values('egressipgroup')))


def termination_reasons(module_settings):
    days = module_settings.termination_lookup_days

    def load():
        window = Q(setuptime__gte=timezone.now() - timedelta(days=days))
        values = []
        for field in TERMINATION_FIELDS:
            values.extend(_distinct_values(field, window))
        return _sorted_unique(values)

    return _cached_lookup('termination-reasons', module_settings, load, extra={'window_days': days})
