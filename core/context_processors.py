"""Site-wide template context.

Everything here is cached and invalidated by signals, so rendering a page does
not re-read configuration and navigation rows on every request.
"""
from django.conf import settings
from django.core.cache import cache
from django.db import DatabaseError

from .models import SiteSettings, SocialLink

NAV_CACHE_KEY = "core:nav"


def _cached(key, builder, timeout):
    value = cache.get(key)
    if value is not None:
        return value
    try:
        value = builder()
    except DatabaseError:
        # Error pages must still render when the database is unreachable.
        return None
    cache.set(key, value, timeout)
    return value


def site_context(request):
    timeout = getattr(settings, "SITE_CONTEXT_CACHE_SECONDS", 300)

    site = cache.get(SiteSettings.SINGLETON_CACHE_KEY)
    if site is None:
        try:
            site = SiteSettings.load()
        except DatabaseError:
            site = None
        if site is not None:
            cache.set(SiteSettings.SINGLETON_CACHE_KEY, site, timeout)

    social_links = _cached(
        "core:social-links",
        lambda: list(SocialLink.objects.filter(is_active=True).exclude(url="")),
        timeout,
    )

    def build_nav():
        from careers.models import JobOpening
        from company.models import Industry, Solution

        return {
            "solutions": list(Solution.objects.active()[:6]),
            "industries": list(Industry.objects.active()[:6]),
            "open_roles": JobOpening.open_roles.count(),
        }

    nav = _cached(NAV_CACHE_KEY, build_nav, timeout) or {}

    return {
        "site": site,
        "social_links": social_links or [],
        "nav_solutions": nav.get("solutions", []),
        "nav_industries": nav.get("industries", []),
        "open_role_count": nav.get("open_roles", 0),
        "site_url": settings.SITE_URL,
    }
