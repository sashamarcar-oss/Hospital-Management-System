import logging

logger = logging.getLogger(__name__)


class AuditMiddleware:
    """Lightweight middleware for read-only audit of sensitive endpoints."""

    SENSITIVE_PATHS = [
        "/api/patients/",
        "/api/billing/",
        "/api/consultations/",
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response
