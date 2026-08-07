# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

import pytest

from diversions import services


class CountingCucmClient:
    def __init__(self):
        self.calls = 0

    def health_check(self):
        self.calls += 1
        return type('Health', (), {'available': True, 'status': 'ok'})()


def test_status_is_cached_within_ttl(monkeypatch, settings):
    settings.CUCM_STATUS_CACHE_SECONDS = 60
    client = CountingCucmClient()
    monkeypatch.setattr('diversions.services.get_cucm_client', lambda: client)

    assert services.cucm_status_value() == 'available'
    assert services.cucm_status_value() == 'available'

    assert client.calls == 1


def test_reset_forces_fresh_probe(monkeypatch, settings):
    settings.CUCM_STATUS_CACHE_SECONDS = 60
    client = CountingCucmClient()
    monkeypatch.setattr('diversions.services.get_cucm_client', lambda: client)

    services.cucm_status_value()
    services.reset_cucm_status_cache()
    services.cucm_status_value()

    assert client.calls == 2


def test_ttl_zero_probes_every_call(monkeypatch, settings):
    settings.CUCM_STATUS_CACHE_SECONDS = 0
    client = CountingCucmClient()
    monkeypatch.setattr('diversions.services.get_cucm_client', lambda: client)

    services.cucm_status_value()
    services.cucm_status_value()

    assert client.calls == 2
