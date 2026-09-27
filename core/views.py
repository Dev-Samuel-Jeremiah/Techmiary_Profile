"""Homepage, About, Technology and the small text pages."""
from django.conf import settings
from django.http import HttpResponse
from django.views.generic import TemplateView

from blog.models import BlogPost
from careers.models import JobOpening
from company.models import (
    Client,
    CompanyValue,
    Industry,
    Milestone,
    Solution,
    TeamMember,
    Testimonial,
)
from projects.models import Project
from services.models import Service

from .models import Partner, Skill, SkillCategory
from .seo import SEOMixin, breadcrumb_schema, organization_schema, person_schema


# Figures as stated in the founder's GitHub profile README. Change them here
# only when there is a source for the new number.
IMPACT = [
    {"value": 10, "suffix": "", "label": "Client platforms developed and maintained", "prefix": "~"},
    {"value": 15, "suffix": "", "label": "Websites and web applications delivered", "prefix": "~"},
    {"value": 20, "suffix": "+", "label": "Final-year software projects supported", "prefix": ""},
]


# The kinds of software we ship. Each names a real project as its example, so
# a claim here always points at the work behind it.
PLATFORMS = [
    {"key": "web", "icon": "globe", "title": "Web platforms",
     "text": "Multi-tenant SaaS, school ERPs and information systems, hosted and maintained on our servers.",
     "example": "techmiary-cloud"},
    {"key": "desktop", "icon": "monitor", "title": "Desktop software",
     "text": "Programs that install on your own Windows or Linux computers, with local data and backups.",
     "example": "school-result-manager"},
    {"key": "mobile", "icon": "smartphone", "title": "Android & iOS apps",
     "text": "Phone apps built on your platform, so every update you deploy reaches users without a new release.",
     "example": "diction-masters"},
    {"key": "offline", "icon": "wifi-off", "title": "Online or offline",
     "text": "Software that keeps working without the internet — scores entered and results printed on site.",
     "example": "school-result-manager"},
]


def platforms_with_examples():
    slugs = {p["example"] for p in PLATFORMS}
    projects = {p.slug: p for p in Project.published.filter(slug__in=slugs)}
    return [dict(p, project=projects.get(p["example"])) for p in PLATFORMS]


class HomeView(SEOMixin, TemplateView):
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["solutions"] = list(
            Solution.objects.active().filter(is_featured=True).prefetch_related("industries")[:4]
        ) or list(Solution.objects.active().prefetch_related("industries")[:4])
        context["industries"] = list(Industry.objects.active()[:6])
        context["services"] = list(
            Service.objects.filter(is_active=True, is_featured=True)[:6]
        ) or list(Service.objects.filter(is_active=True)[:6])

        featured = list(Project.published.with_related().prefetch_related("features").filter(featured=True)[:4])
        if not featured:
            featured = list(Project.published.with_related().prefetch_related("features")[:4])
        context["featured_projects"] = featured

        context["leadership"] = list(TeamMember.objects.active().filter(is_leadership=True)[:4])
        context["testimonials"] = list(
            Testimonial.objects.active().select_related("client")[:3]
        )
        context["clients"] = list(Client.objects.active()[:12])
        context["latest_posts"] = list(BlogPost.live.all()[:3])
        context["open_roles"] = list(JobOpening.open_roles.all()[:3])
        context["values"] = list(CompanyValue.objects.active()[:4])

        partners = list(
            Partner.objects.filter(is_active=True).order_by("display_order", "name")
        )
        context["partners"] = [p for p in partners if p.kind == Partner.KIND_PARTNER]
        context["trusted_by"] = [p for p in partners if p.kind == Partner.KIND_TRUSTED]

        context["stack"] = list(
            Skill.objects.filter(is_active=True)
            .order_by("category__display_order", "display_order")
            .values_list("name", flat=True)[:28]
        )
        context["impact"] = IMPACT
        context["platforms"] = platforms_with_examples()
        return context

    def get_meta_title(self, context):
        site = context.get("site")
        if not site:
            return "Techmiary Technology Concepts"
        return f"{site.display_company} — {site.professional_title}"

    def get_meta_description(self, context):
        site = context.get("site")
        return site.resolved_meta_description if site else ""

    def get_structured_data(self, context):
        site = context.get("site")
        graph = [s for s in (organization_schema(site), person_schema(site)) if s]
        if not graph:
            return None
        return {
            "@context": "https://schema.org",
            "@graph": [
                {k: v for k, v in item.items() if k != "@context"} for item in graph
            ],
        }


class AboutView(SEOMixin, TemplateView):
    template_name = "about.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["values"] = list(CompanyValue.objects.active())
        context["milestones"] = list(Milestone.objects.active())
        context["leadership"] = list(TeamMember.objects.active().filter(is_leadership=True))
        context["solution_count"] = Solution.objects.active().count()
        context["project_count"] = Project.published.count()
        context["industry_count"] = Industry.objects.active().count()
        context["service_count"] = Service.objects.filter(is_active=True).count()
        context["clients"] = list(Client.objects.active()[:12])
        context["impact"] = IMPACT
        return context

    def get_meta_title(self, context):
        site = context.get("site")
        return f"About {site.display_company}" if site else "About us"

    def get_meta_description(self, context):
        site = context.get("site")
        if not site:
            return ""
        return (site.company_overview or site.long_bio or site.short_bio)[:180]

    def get_structured_data(self, context):
        site = context.get("site")
        organisation = organization_schema(site)
        crumbs = breadcrumb_schema([("Home", "/"), ("About", "/about/")])
        graph = [s for s in (organisation, crumbs) if s]
        return {
            "@context": "https://schema.org",
            "@graph": [{k: v for k, v in item.items() if k != "@context"} for item in graph],
        }


class TechnologyView(SEOMixin, TemplateView):
    """The stack the company builds and runs systems on."""

    template_name = "technology.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = [
            category
            for category in SkillCategory.objects.prefetch_related("skills")
            if any(skill.is_active for skill in category.skills.all())
        ]
        return context

    def get_meta_title(self, context):
        site = context.get("site")
        return f"Technology Stack — {site.display_company}" if site else "Technology"

    def get_meta_description(self, context):
        return (
            "The backend, frontend, infrastructure, cloud and integration technologies "
            "the company uses to build and operate production systems."
        )

    def get_structured_data(self, context):
        return breadcrumb_schema([("Home", "/"), ("Technology", "/technology/")])


class LegalPageView(SEOMixin, TemplateView):
    page_title = ""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = self.page_title
        return context

    def get_meta_title(self, context):
        site = context.get("site")
        return f"{self.page_title} — {site.display_company}" if site else self.page_title

    def get_meta_description(self, context):
        return f"{self.page_title} for this website."


class PrivacyView(LegalPageView):
    template_name = "privacy.html"
    page_title = "Privacy Policy"


class TermsView(LegalPageView):
    template_name = "terms.html"
    page_title = "Terms of Use"


def robots_txt(request):
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /accounts/",
        # The staff control panel. Unlike ADMIN_URL this path is not secret,
        # so naming it here costs nothing and keeps it out of indexes.
        "Disallow: /dashboard/",
        "Allow: /",
        "",
        f"Sitemap: {settings.SITE_URL}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")
