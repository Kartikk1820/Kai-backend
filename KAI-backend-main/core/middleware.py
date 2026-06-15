import uuid
import structlog
from django.conf import settings

logger = structlog.get_logger(__name__)


class RequestIDMiddleware:
    """Attach a request_id to every request and bind it to the structlog context."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
        request.request_id = request_id
        structlog.contextvars.bind_contextvars(request_id=request_id)
        response = self.get_response(request)
        response['X-Request-ID'] = request_id
        return response


class SimpleCorsMiddleware:
    """
    Minimal CORS handling without an external dependency.
    Echoes allowed origins from settings.CORS_ALLOWED_ORIGINS and handles preflight.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.allowed = set(getattr(settings, 'CORS_ALLOWED_ORIGINS', []))

    def __call__(self, request):
        origin = request.headers.get('Origin')

        if request.method == 'OPTIONS' and origin:
            from django.http import HttpResponse
            response = HttpResponse(status=204)
        else:
            response = self.get_response(request)

        if origin and origin in self.allowed:
            response['Access-Control-Allow-Origin'] = origin
            response['Access-Control-Allow-Credentials'] = 'true'
            response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
            response['Access-Control-Allow-Headers'] = (
                'Authorization, Content-Type, X-Request-ID, X-Requested-With'
            )
            response['Access-Control-Max-Age'] = '86400'
        return response
