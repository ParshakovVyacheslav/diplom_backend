from rest_framework.views import exception_handler as drf_exception_handler


def custom_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return response

    payload = {
        "error": response.status_code,
    }

    if response.data:
        payload["detail"] = response.data

    response.data = payload
    return response
