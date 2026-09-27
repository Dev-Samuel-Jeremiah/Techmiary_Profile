from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from core.views import robots_txt

from .sitemaps import SITEMAPS

admin.site.site_header = "Techmiary Technology Concepts — Administration"
admin.site.site_title = "Techmiary Admin"
admin.site.index_title = "Website content & configuration"

urlpatterns = [
    # Must precede admin.site.urls: the admin mounts a catch-all under its own
    # prefix, which would otherwise swallow these URLs and return its 404.
    # Staff-only, and under the admin prefix so it stays off the public map.
    path(settings.ADMIN_URL, include("proposals.urls")),
    # The staff control panel. Its own branded login lives here.
    path("dashboard/", include("dashboard.urls")),
    path(settings.ADMIN_URL, admin.site.urls),
    path("", include("core.urls")),
    path("", include("company.urls")),
    path("", include("contact.urls")),
    path("careers/", include("careers.urls")),
    path("projects/", include("projects.urls")),
    path("experience/", include("experience.urls")),
    path("services/", include("services.urls")),
    path("blog/", include("blog.urls")),
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": SITEMAPS},
        name="django.contrib.sitemaps.views.sitemap",
    ),
    path("robots.txt", robots_txt, name="robots"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.BASE_DIR / "static")

handler404 = "core.errors.page_not_found"
handler403 = "core.errors.permission_denied"
handler500 = "core.errors.server_error"
