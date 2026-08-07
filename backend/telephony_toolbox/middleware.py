# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

import logging
import time

from django.conf import settings
from django.db import connection


logger = logging.getLogger('telephony_toolbox.perf')


class _QueryCounter:
    """Callable execute wrapper that counts queries and their cumulative time."""

    def __init__(self):
        self.count = 0
        self.total_ms = 0.0

    def __call__(self, execute, sql, params, many, context):
        self.count += 1
        start = time.perf_counter()
        try:
            return execute(sql, params, many, context)
        finally:
            self.total_ms += (time.perf_counter() - start) * 1000


class RequestTimingMiddleware:
    """Record wall-clock time and database activity for each request.

    Every response gains ``X-Response-Time-ms`` and ``X-DB-Query-Count`` headers,
    and a structured line is written to the ``telephony_toolbox.perf`` logger.
    Requests slower than ``PERF_SLOW_REQUEST_MS`` are logged at WARNING so slow
    endpoints stand out in the perf log.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.slow_ms = getattr(settings, 'PERF_SLOW_REQUEST_MS', 500)

    def __call__(self, request):
        counter = _QueryCounter()
        start = time.perf_counter()
        with connection.execute_wrapper(counter):
            response = self.get_response(request)
        duration_ms = (time.perf_counter() - start) * 1000

        response['X-Response-Time-ms'] = f'{duration_ms:.1f}'
        response['X-DB-Query-Count'] = str(counter.count)

        emit = logger.warning if duration_ms >= self.slow_ms else logger.info
        emit(
            'method=%s path=%s status=%s duration_ms=%.1f db_queries=%d db_time_ms=%.1f',
            request.method,
            request.get_full_path(),
            response.status_code,
            duration_ms,
            counter.count,
            counter.total_ms,
        )
        return response
