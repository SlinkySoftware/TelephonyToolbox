# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

"""Shared-cache helpers. Keys embed ``config_version`` so a settings change invalidates everything.

Cache failures (for example a missing cache table) degrade to uncached behaviour rather than
failing the request.
"""

import hashlib
import json
import logging

from django.core.cache import cache
from django.db import DatabaseError

logger = logging.getLogger(__name__)

KEY_PREFIX = 'audiocodes_cdr'


def make_key(kind, config_version, params=None):
    key = f'{KEY_PREFIX}:{kind}:v{config_version}'
    if params is not None:
        digest = hashlib.sha256(json.dumps(params, sort_keys=True, default=str).encode('utf-8')).hexdigest()
        key = f'{key}:{digest}'
    return key


def cache_get(key):
    try:
        return cache.get(key)
    except DatabaseError:
        logger.warning('CDR cache read failed; continuing without cache.')
        return None


def cache_set(key, value, timeout):
    if timeout <= 0:
        return
    try:
        cache.set(key, value, timeout)
    except DatabaseError:
        logger.warning('CDR cache write failed; continuing without cache.')
