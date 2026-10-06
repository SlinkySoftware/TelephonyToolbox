# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

import logging

from django.db import DatabaseError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


logger = logging.getLogger('telephony_toolbox.api')

CDR_API_PREFIX = '/api/admin/cdr/'


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    request = context.get('request') if context else None
    view = context.get('view') if context else None
    request_method = getattr(request, 'method', None)
    request_path = getattr(request, 'path', None)
    view_name = view.__class__.__name__ if view else None

    if response is None and isinstance(exc, DatabaseError) and (request_path or '').startswith(CDR_API_PREFIX):
        # Safety net: never surface raw database errors (hosts, SQL) from the CDR module.
        logger.error(
            'Unhandled database error method=%s path=%s view=%s error=%s',
            request_method,
            request_path,
            view_name,
            type(exc).__name__,
        )
        return Response(
            {
                'detail': 'The AudioCodes CDR source database is currently unavailable.',
                'error_code': 'source_unavailable',
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    if response is None:
        logger.exception(
            'Unhandled API exception method=%s path=%s view=%s',
            request_method,
            request_path,
            view_name,
        )
        return response

    logger.warning(
        'Handled API exception status=%s method=%s path=%s view=%s detail=%s',
        response.status_code,
        request_method,
        request_path,
        view_name,
        response.data,
    )

    detail = response.data.get('detail') if isinstance(response.data, dict) else None
    code = getattr(detail, 'code', None)
    if response.status_code == 403 and code == 'not_authenticated':
        response.status_code = 401
    return response