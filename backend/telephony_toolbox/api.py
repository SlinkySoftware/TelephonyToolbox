from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return response

    detail = response.data.get('detail') if isinstance(response.data, dict) else None
    code = getattr(detail, 'code', None)
    if response.status_code == 403 and code == 'not_authenticated':
        response.status_code = 401
    return response