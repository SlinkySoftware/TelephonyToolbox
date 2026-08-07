# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

import logging

from django.http import HttpResponse

from telephony_toolbox.middleware import RequestTimingMiddleware


class _FakeRequest:
    method = 'GET'

    def get_full_path(self):
        return '/api/example?page=1'


def test_middleware_adds_timing_headers():
    middleware = RequestTimingMiddleware(lambda request: HttpResponse('ok'))

    response = middleware(_FakeRequest())

    assert 'X-Response-Time-ms' in response
    assert float(response['X-Response-Time-ms']) >= 0
    assert 'X-DB-Query-Count' in response
    assert int(response['X-DB-Query-Count']) >= 0


def test_middleware_counts_database_queries(db):
    from accounts.models import User

    def view(request):
        list(User.objects.all())
        return HttpResponse('ok')

    middleware = RequestTimingMiddleware(view)

    response = middleware(_FakeRequest())

    assert int(response['X-DB-Query-Count']) >= 1


def test_slow_request_logged_at_warning(caplog):
    middleware = RequestTimingMiddleware(lambda request: HttpResponse('ok'))
    middleware.slow_ms = 0  # force the slow path

    with caplog.at_level(logging.WARNING, logger='telephony_toolbox.perf'):
        middleware(_FakeRequest())

    assert any(record.levelno == logging.WARNING for record in caplog.records)
    assert any('duration_ms=' in record.getMessage() for record in caplog.records)
