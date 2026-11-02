"""One error shape for the whole API: {"errors": {"field": ["message", ...]}}.

Bad input is always HTTP 400 with a readable message per field, never a stack trace
(check 12). Nested fields are flattened: benefits.1.amount.
"""
from __future__ import annotations

from rest_framework import status
from rest_framework.exceptions import ParseError, UnsupportedMediaType, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


def flatten(detail, prefix: str = "") -> dict[str, list[str]]:
    """Turn DRF's nested error detail into {"a.b.0.c": ["message"]}."""
    out: dict[str, list[str]] = {}
    if isinstance(detail, dict):
        for key, value in detail.items():
            name = "input" if key == "non_field_errors" else str(key)
            for k, v in flatten(value, f"{prefix}.{name}" if prefix else name).items():
                out.setdefault(k, []).extend(v)
    elif isinstance(detail, list):
        if all(not isinstance(d, (dict, list)) for d in detail):
            out[prefix or "input"] = [str(d) for d in detail]
        else:
            for i, value in enumerate(detail):
                if value:
                    for k, v in flatten(value, f"{prefix}.{i}" if prefix else str(i)).items():
                        out.setdefault(k, []).extend(v)
    else:
        out[prefix or "input"] = [str(detail)]
    return out


def error_response(errors: dict[str, list[str]], code: int = status.HTTP_400_BAD_REQUEST) -> Response:
    return Response({"errors": errors}, status=code)


def exception_handler(exc, context):
    if isinstance(exc, ValidationError):
        return error_response(flatten(exc.detail))
    if isinstance(exc, ParseError):
        return error_response({"request": ["The request body is not valid JSON."]})
    if isinstance(exc, UnsupportedMediaType):
        return error_response({"request": ["Send the request as JSON (Content-Type: application/json)."]},
                              status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)
    response = drf_exception_handler(exc, context)
    if response is not None:
        message = response.data.get("detail", "The request could not be handled.") \
            if isinstance(response.data, dict) else "The request could not be handled."
        response.data = {"errors": {"request": [str(message)]}}
    return response
