# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

"""Query-string redaction for request logs on paths that carry call data (ANI/DNIS) in GET parameters."""

from urllib.parse import urlsplit, urlunsplit

QUERY_REDACTED_PATH_PREFIXES = ('/api/admin/cdr/', '/admin/cdr')


def is_query_redacted_path(path):
    return bool(path) and path.startswith(QUERY_REDACTED_PATH_PREFIXES)


def redact_url(url):
    """Drop the query string and fragment from a path or absolute URL when its path is redacted."""
    if not url or url == '-':
        return url
    parts = urlsplit(url)
    if not is_query_redacted_path(parts.path):
        return url
    return urlunsplit((parts.scheme, parts.netloc, parts.path, '', ''))
