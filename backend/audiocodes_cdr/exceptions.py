# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

from rest_framework import status
from rest_framework.exceptions import APIException


class SourceWriteForbidden(RuntimeError):
    """Raised on any attempt to write to the read-only AudioCodes source."""


class CdrApiError(APIException):
    """API error with a stable ``error_code`` and a message that is safe to show to users."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = 'The AudioCodes CDR module is unavailable.'
    default_code = 'cdr_error'

    def __init__(self, detail=None, code=None, extra=None):
        self.message = str(detail or self.default_detail)
        self.error_code = code or self.default_code
        payload = {'detail': self.message, 'error_code': self.error_code}
        if extra:
            payload.update(extra)
        super().__init__(payload, self.error_code)


class CdrSourceError(CdrApiError):
    default_detail = 'The AudioCodes CDR source database is unavailable.'
    default_code = 'source_error'


class SourceNotConfigured(CdrSourceError):
    default_detail = 'The AudioCodes CDR source database is not configured.'
    default_code = 'source_not_configured'


class SourceUnavailable(CdrSourceError):
    default_detail = 'The AudioCodes CDR source database is currently unavailable.'
    default_code = 'source_unavailable'


class SourceConfigurationError(CdrSourceError):
    default_detail = 'The AudioCodes CDR module is not configured correctly. Contact an administrator.'
    default_code = 'source_configuration_error'


class SourceTimeout(CdrSourceError):
    status_code = status.HTTP_504_GATEWAY_TIMEOUT
    default_detail = (
        'The query exceeded the 60-second time limit. Narrow the date range or use exact or '
        'starts-with matching and try again.'
    )
    default_code = 'source_timeout'


class SourceQueryCancelled(SourceTimeout):
    default_detail = 'The query was cancelled by the read replica while it applied updates. Please retry.'
    default_code = 'source_query_cancelled'


class SdrNotFound(CdrApiError):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = 'SDR not found.'
    default_code = 'sdr_not_found'


class InvalidFilters(CdrApiError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'The search filters are invalid.'
    default_code = 'invalid_filters'

    def __init__(self, errors):
        code = 'range_too_large' if _has_code(errors, 'range_too_large') else self.default_code
        detail = 'The search range cannot exceed 12 months.' if code == 'range_too_large' else None
        super().__init__(detail, code, extra={'errors': errors})


def _has_code(errors, code):
    if isinstance(errors, dict):
        return any(_has_code(value, code) for value in errors.values())
    if isinstance(errors, list):
        return any(_has_code(value, code) for value in errors)
    return getattr(errors, 'code', None) == code
