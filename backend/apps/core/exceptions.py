import logging

from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response

logger = logging.getLogger(__name__)


def api_exception_handler(exc, context):
    """Translate every backend error into a friendly, consistent API error shape."""

    if isinstance(exc, exceptions.ValidationError):
        return Response(
            {
                "detail": "Please check the highlighted fields and try again.",
                "errors": exc.detail,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if isinstance(exc, exceptions.AuthenticationFailed):
        return Response(
            {"detail": "Authentication failed. Please check your credentials."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    if isinstance(exc, exceptions.NotAuthenticated):
        return Response(
            {"detail": "You must be logged in to access this resource."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    if isinstance(exc, exceptions.PermissionDenied) or isinstance(exc, PermissionDenied):
        return Response(
            {"detail": "You do not have permission to perform this action."},
            status=status.HTTP_403_FORBIDDEN,
        )

    if isinstance(exc, exceptions.NotFound) or isinstance(exc, Http404):
        return Response(
            {"detail": "The requested record could not be found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if isinstance(exc, exceptions.Throttled):
        return Response(
            {"detail": "Too many attempts. Please try again later."},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    if isinstance(exc, exceptions.MethodNotAllowed):
        return Response(
            {"detail": "This operation is not allowed on this resource."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    if isinstance(exc, exceptions.APIException):
        return Response({"detail": exc.detail}, status=exc.status_code)

    logger.exception("Unhandled API exception")
    return Response(
        {
            "detail": "An unexpected error occurred. Please try again later or contact your administrator.",
            "errors": None,
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
