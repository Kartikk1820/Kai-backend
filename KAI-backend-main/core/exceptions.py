from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status as http_status
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
import structlog

logger = structlog.get_logger(__name__)


def standardized_exception_handler(exc, context):
    """
    Ensure every error flows through DRF so the StandardizedJSONRenderer can
    wrap it in the { meta, data, errors } envelope. Translates a few native
    Django exceptions that DRF would otherwise let escape as HTML 500s.
    """
    if isinstance(exc, Http404):
        return Response({'detail': 'Not found.'}, status=http_status.HTTP_404_NOT_FOUND)
    if isinstance(exc, DjangoPermissionDenied):
        return Response({'detail': str(exc) or 'Permission denied.'},
                        status=http_status.HTTP_403_FORBIDDEN)
    if isinstance(exc, PermissionError):
        return Response({'detail': str(exc) or 'Permission denied.'},
                        status=http_status.HTTP_403_FORBIDDEN)

    response = exception_handler(exc, context)
    if response is None:
        logger.exception('unhandled_exception', exc_type=type(exc).__name__)
        return Response({'detail': 'Internal server error.'},
                        status=http_status.HTTP_500_INTERNAL_SERVER_ERROR)
    return response
