# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

import logging
from datetime import timedelta
from types import SimpleNamespace

import pytest
from django.http import HttpResponse
from gunicorn.config import Config

from telephony_toolbox.gunicorn_logging import RedactingLogger
from telephony_toolbox.log_redaction import redact_url
from telephony_toolbox.middleware import RequestTimingMiddleware


@pytest.mark.parametrize(
    'url, expected',
    [
        ('/api/admin/cdr/sdr/?ani=0299990000', '/api/admin/cdr/sdr/'),
        ('https://toolbox.example/admin/cdr?dnis=1300', 'https://toolbox.example/admin/cdr'),
        ('/api/admin/diversions/?page=2', '/api/admin/diversions/?page=2'),
        ('-', '-'),
        (None, None),
    ],
)
def test_redact_url(url, expected):
    assert redact_url(url) == expected


def _environ(path, query, referer='-'):
    return {
        'REQUEST_METHOD': 'GET',
        'RAW_URI': f'{path}?{query}',
        'PATH_INFO': path,
        'QUERY_STRING': query,
        'SERVER_PROTOCOL': 'HTTP/1.1',
        'REMOTE_ADDR': '127.0.0.1',
        'HTTP_REFERER': referer,
    }


def _atoms(environ):
    response = SimpleNamespace(status='200 OK', sent=10, headers=[])
    request = SimpleNamespace(headers=[('REFERER', environ['HTTP_REFERER'])])
    return RedactingLogger(Config()).atoms(response, request, environ, timedelta(milliseconds=5))


def test_gunicorn_access_log_drops_cdr_query_strings():
    atoms = _atoms(_environ('/api/admin/cdr/sdr/', 'ani=0299990000', 'https://toolbox.example/admin/cdr?ani=0299990000'))
    rendered = ' '.join(str(value) for value in atoms.values())

    assert '0299990000' not in rendered
    assert atoms['r'] == 'GET /api/admin/cdr/sdr/ HTTP/1.1'
    assert atoms['f'] == 'https://toolbox.example/admin/cdr'


def test_gunicorn_access_log_keeps_other_query_strings():
    atoms = _atoms(_environ('/api/admin/audit/', 'page=2'))

    assert atoms['r'] == 'GET /api/admin/audit/?page=2 HTTP/1.1'


def test_perf_log_drops_cdr_query_strings(caplog):
    class Request:
        method = 'GET'

        def get_full_path(self):
            return '/api/admin/cdr/sdr/?ani=0299990000'

    middleware = RequestTimingMiddleware(lambda request: HttpResponse('ok'))
    with caplog.at_level(logging.INFO, logger='telephony_toolbox.perf'):
        middleware(Request())

    messages = ' '.join(record.getMessage() for record in caplog.records)
    assert 'path=/api/admin/cdr/sdr/ ' in messages
    assert '0299990000' not in messages
