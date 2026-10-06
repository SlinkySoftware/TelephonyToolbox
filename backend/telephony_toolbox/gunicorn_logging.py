# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

"""Gunicorn access logger that keeps ANI/DNIS search parameters out of the access log.

Enable with ``--logger-class telephony_toolbox.gunicorn_logging.RedactingLogger``.
"""

from gunicorn.glogging import Logger

from telephony_toolbox.log_redaction import is_query_redacted_path, redact_url


class RedactingLogger(Logger):
    def atoms(self, resp, req, environ, request_time):
        atoms = super().atoms(resp, req, environ, request_time)
        path = environ.get('PATH_INFO', '')
        if is_query_redacted_path(path):
            atoms['r'] = f"{environ.get('REQUEST_METHOD')} {path} {environ.get('SERVER_PROTOCOL')}"
            atoms['q'] = ''
            for key in ('{raw_uri}e', '{request_uri}e'):
                if key in atoms:
                    atoms[key] = path
            atoms['{query_string}e'] = ''

        referer = redact_url(atoms.get('f'))
        atoms['f'] = referer
        if '{referer}i' in atoms:
            atoms['{referer}i'] = referer
        if '{http_referer}e' in atoms:
            atoms['{http_referer}e'] = referer
        return atoms
