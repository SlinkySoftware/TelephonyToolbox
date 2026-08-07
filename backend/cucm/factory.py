# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

import threading

from django.conf import settings

from cucm.client_105 import Cucm105Client
from cucm.client_14 import Cucm14Client


# Building a client parses the (large) AXL WSDL with zeep, which costs ~1.5s.
# The CUCM version and connection details cannot change while the process is
# running, so the client is built once per worker and reused. The cache is
# keyed on the connection signature so a settings change (e.g. in tests) forces
# a rebuild rather than handing back a stale client.
_client_lock = threading.Lock()
_cached_client = None
_cached_signature = None


def _client_signature():
    return (
        settings.CUCM_AXL_VERSION,
        settings.CUCM_AXL_HOST,
        settings.CUCM_AXL_USERNAME,
        settings.CUCM_AXL_PASSWORD,
    )


def _build_client():
    version = settings.CUCM_AXL_VERSION
    if version == '10.5':
        return Cucm105Client()
    if version == '14':
        return Cucm14Client()
    raise ValueError(f'Unsupported CUCM AXL version: {version}')


def get_cucm_client():
    global _cached_client, _cached_signature
    signature = _client_signature()
    with _client_lock:
        if _cached_client is None or _cached_signature != signature:
            _cached_client = _build_client()
            _cached_signature = signature
        return _cached_client


def reset_cucm_client():
    """Discard the cached client so the next call rebuilds it."""
    global _cached_client, _cached_signature
    with _client_lock:
        _cached_client = None
        _cached_signature = None