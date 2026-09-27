"""Small security-header middleware.

Django ships most of these as settings; Content-Security-Policy and
Permissions-Policy are not covered, so they are added here rather than pulling
in another dependency.
"""
from django.conf import settings

DEFAULT_CSP = (
    "default-src 'self'; "
    "base-uri 'self'; "
    "frame-ancestors 'none'; "
    "object-src 'none'; "
    "img-src 'self' data: https:; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; "
    "font-src 'self' https://fonts.gstatic.com data:; "
    "script-src 'self' https://cdn.jsdelivr.net; "
    "connect-src 'self'; "
    "form-action 'self'; "
    "upgrade-insecure-requests"
)

DEFAULT_PERMISSIONS_POLICY = "camera=(), microphone=(), geolocation=(), interest-cohort=()"


class SecurityHeadersMiddleware:
    """Adds CSP and Permissions-Policy to every response."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.csp = getattr(settings, "CONTENT_SECURITY_POLICY", DEFAULT_CSP)
        self.permissions_policy = getattr(
            settings, "PERMISSIONS_POLICY", DEFAULT_PERMISSIONS_POLICY
        )
        # ADMIN_URL is configurable so the admin can be moved off a guessable
        # path. The exemption below has to follow it, or moving the admin
        # silently applies the site CSP to it and breaks its inline scripts.
        admin_url = getattr(settings, "ADMIN_URL", "admin/")
        self.admin_prefix = "/" + admin_url.strip("/") + "/"

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith(self.admin_prefix):
            # The admin relies on inline scripts; leave its own headers alone.
            response.setdefault("Permissions-Policy", self.permissions_policy)
            return response
        response.setdefault("Content-Security-Policy", self.csp)
        response.setdefault("Permissions-Policy", self.permissions_policy)
        return response
