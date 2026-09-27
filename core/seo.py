"""Helpers for per-page SEO metadata and JSON-LD."""
import json

from django.conf import settings
from django.utils.safestring import mark_safe


def absolute(path):
    """Turn a root-relative path into an absolute URL using SITE_URL."""
    if not path:
        return settings.SITE_URL
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return f"{settings.SITE_URL}{path}"


def json_ld(data):
    """Serialise a dict to a JSON-LD string safe for a <script> block."""
    return mark_safe(
        json.dumps(data, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e")
    )


class SEOMixin:
    """
    Adds ``meta_title``, ``meta_description``, ``canonical_url`` and
    ``structured_data`` to a view's context.

    Subclasses override ``get_meta_title`` / ``get_meta_description`` /
    ``get_structured_data`` where a page needs something more specific.
    """

    meta_title = ""
    meta_description = ""

    def get_site(self):
        """The SiteSettings singleton, resolved once per request."""
        if not hasattr(self, "_site"):
            from django.core.cache import cache

            from core.models import SiteSettings

            site = cache.get(SiteSettings.SINGLETON_CACHE_KEY)
            if site is None:
                site = SiteSettings.load()
                if site is not None:
                    cache.set(
                        SiteSettings.SINGLETON_CACHE_KEY,
                        site,
                        settings.SITE_CONTEXT_CACHE_SECONDS,
                    )
            self._site = site
        return self._site

    def get_meta_title(self, context):
        return self.meta_title

    def get_meta_description(self, context):
        return self.meta_description

    def get_structured_data(self, context):
        return None

    def get_canonical_url(self):
        return absolute(self.request.path)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("site", self.get_site())
        context["meta_title"] = self.get_meta_title(context)
        context["meta_description"] = self.get_meta_description(context)
        context["canonical_url"] = self.get_canonical_url()
        data = self.get_structured_data(context)
        if data:
            context["structured_data"] = json_ld(data)
        return context


def person_schema(site, projects=None):
    """Person schema for the site owner. Only includes fields that are set."""
    if site is None:
        return None
    # The founder's own role comes from their team record when one exists;
    # the site's positioning line describes the company, not a person.
    job_title = site.professional_title
    try:
        from company.models import TeamMember

        founder = TeamMember.objects.filter(is_founder=True, is_active=True).first()
        if founder:
            job_title = founder.role
    except Exception:  # pragma: no cover - schema must never break a page
        founder = None

    data = {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": site.name,
        "url": settings.SITE_URL,
        "jobTitle": job_title,
    }
    if site.company_name:
        data["worksFor"] = {"@type": "Organization", "name": site.company_name}
    if site.short_bio:
        data["description"] = site.short_bio
    if site.location:
        data["address"] = {"@type": "PostalAddress", "addressLocality": site.location}
    if site.company_name:
        data["worksFor"] = {
            "@type": "Organization",
            "name": site.company_name,
            **({"url": site.website_url} if site.website_url else {}),
        }
    same_as = [u for u in (site.github_url, site.linkedin_url, site.twitter_url, site.website_url) if u]
    if same_as:
        data["sameAs"] = same_as
    if site.profile_image:
        data["image"] = absolute(site.profile_image.url)
    if projects:
        data["knowsAbout"] = sorted({t.name for p in projects for t in p.technologies.all()})
    return data


def organization_schema(site):
    """Organization schema for the company. Only fields that are set appear."""
    if site is None:
        return None
    name = site.company_name or site.legal_name or site.brand_name
    if not name:
        return None
    data = {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": name,
        "url": settings.SITE_URL,
    }
    if site.legal_name and site.legal_name != name:
        data["legalName"] = site.legal_name
    if site.company_overview or site.short_bio:
        data["description"] = (site.company_overview or site.short_bio)[:300]
    if site.logo:
        data["logo"] = absolute(site.logo.url)
    if site.founded_year:
        data["foundingDate"] = str(site.founded_year)
    if site.name:
        data["founder"] = {"@type": "Person", "name": site.name}
    address = {}
    if site.address:
        address["streetAddress"] = site.address.replace("\n", ", ")
    if site.location:
        address["addressLocality"] = site.location
    if address:
        address["@type"] = "PostalAddress"
        data["address"] = address
    contact_points = []
    if site.sales_email or site.email:
        contact_points.append({
            "@type": "ContactPoint",
            "contactType": "sales",
            "email": site.sales_email or site.email,
            **({"telephone": site.phone} if site.phone else {}),
        })
    if site.support_email:
        contact_points.append({
            "@type": "ContactPoint",
            "contactType": "customer support",
            "email": site.support_email,
        })
    if contact_points:
        data["contactPoint"] = contact_points
    same_as = [
        u
        for u in (site.website_url, site.linkedin_url, site.twitter_url, site.github_url)
        if u and u != settings.SITE_URL
    ]
    if same_as:
        data["sameAs"] = same_as
    return data


def project_schema(project):
    """
    SoftwareApplication schema for a project.

    No ratings or review counts are emitted — there are none to report.
    """
    data = {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": project.title,
        "applicationCategory": "BusinessApplication",
        "description": project.short_description,
        "url": project.website_url or absolute(project.get_absolute_url()),
        "operatingSystem": "Web",
    }
    if project.cover_image:
        data["image"] = absolute(project.cover_image.url)
    technologies = [t.name for t in project.technologies.all()]
    if technologies:
        data["keywords"] = ", ".join(technologies)
    return data


def breadcrumb_schema(items):
    """items: list of (name, path) tuples."""
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": index,
                "name": name,
                "item": absolute(path),
            }
            for index, (name, path) in enumerate(items, start=1)
        ],
    }
