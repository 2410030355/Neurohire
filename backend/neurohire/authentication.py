"""
Session authentication for the cross-site React frontend.

The frontend (Vercel) and backend (Render) live on different sites, so the
browser JavaScript cannot read the backend's ``csrftoken`` cookie and therefore
cannot send DRF's ``X-CSRFToken`` header. Plain ``SessionAuthentication`` would
reject every state-changing request from the real frontend.

Instead of the token check, this class verifies that state-changing requests
come from an allow-listed browser origin (the same origins already trusted for
CORS). Combined with JSON-only parsers on the protected views — which forces a
CORS preflight that untrusted origins fail — this blocks cross-site request
forgery without breaking the existing frontend.
"""
from urllib.parse import urlsplit

from django.conf import settings
from rest_framework import exceptions
from rest_framework.authentication import SessionAuthentication

SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS', 'TRACE')


def _origin_of(url):
    """Return 'scheme://host[:port]' for a URL, or None if it cannot be parsed."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return None
    if not parts.scheme or not parts.netloc:
        return None
    return f'{parts.scheme}://{parts.netloc}'.lower()


def trusted_origins():
    """Origins allowed to make state-changing, cookie-authenticated requests.

    Mirrors the origins django-cors-headers actually allows (it reads
    CORS_ALLOWED_ORIGINS, falling back to CORS_ORIGIN_WHITELIST only when the
    former is unset), plus any explicit CSRF_TRUSTED_ORIGINS.
    """
    from corsheaders.conf import conf as cors_conf

    configured = (
        list(cors_conf.CORS_ALLOWED_ORIGINS or [])
        + list(getattr(settings, 'CSRF_TRUSTED_ORIGINS', []) or [])
    )
    return {o.strip().rstrip('/').lower() for o in configured if o and o.strip()}


class OriginCheckedSessionAuthentication(SessionAuthentication):
    """SessionAuthentication with an Origin/Referer allow-list instead of a CSRF token."""

    def enforce_csrf(self, request):
        if request.method in SAFE_METHODS:
            return

        origin_header = request.META.get('HTTP_ORIGIN')
        if origin_header is not None:
            origin = _origin_of(origin_header)  # 'null' and malformed values -> None
        else:
            referer = request.META.get('HTTP_REFERER')
            if referer is None:
                # No browser origin information at all: not a browser-initiated
                # cross-site request (browsers always send Origin on cross-origin
                # POST/PUT/PATCH/DELETE), so there is no CSRF vector to block.
                return
            origin = _origin_of(referer)

        same_origin = _origin_of(request.build_absolute_uri('/'))
        if origin and (origin == same_origin or origin in trusted_origins()):
            return

        raise exceptions.PermissionDenied('CSRF Failed: request origin is not trusted.')
