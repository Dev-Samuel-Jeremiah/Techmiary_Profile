"""Sitemap definitions for the company website."""
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from blog.models import BlogPost
from careers.models import JobOpening
from company.models import Industry, Resource, Solution, TeamMember
from projects.models import Project


class StaticViewSitemap(Sitemap):
    changefreq = "monthly"

    def items(self):
        return [
            "core:home",
            "core:about",
            "core:skills",
            "company:solution_list",
            "company:industry_list",
            "company:team_list",
            "company:client_list",
            "company:resource_list",
            "company:faq",
            "services:list",
            "projects:list",
            "careers:list",
            "blog:list",
            "contact:contact",
            "contact:quote",
            "core:privacy",
            "core:terms",
        ]

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        if item == "core:home":
            return 1.0
        if item in {"company:solution_list", "contact:quote", "services:list"}:
            return 0.9
        if item in {"core:privacy", "core:terms"}:
            return 0.3
        return 0.7


class SolutionSitemap(Sitemap):
    priority = 0.9
    changefreq = "monthly"

    def items(self):
        return Solution.objects.active()

    def lastmod(self, obj):
        return obj.updated_at


class IndustrySitemap(Sitemap):
    priority = 0.7
    changefreq = "monthly"

    def items(self):
        return Industry.objects.active()


class ProjectSitemap(Sitemap):
    priority = 0.8
    changefreq = "monthly"

    def items(self):
        return Project.published.all()

    def lastmod(self, obj):
        return obj.updated_at


class TeamSitemap(Sitemap):
    priority = 0.5
    changefreq = "yearly"

    def items(self):
        return TeamMember.objects.active()


class JobSitemap(Sitemap):
    priority = 0.7
    changefreq = "weekly"

    def items(self):
        return JobOpening.open_roles.all()

    def lastmod(self, obj):
        return obj.updated_at


class ResourceSitemap(Sitemap):
    priority = 0.5
    changefreq = "monthly"

    def items(self):
        return Resource.objects.active()

    def location(self, obj):
        return f"{reverse('company:resource_list')}#{obj.slug}"


class BlogSitemap(Sitemap):
    priority = 0.6
    changefreq = "weekly"

    def items(self):
        return BlogPost.live.all()

    def lastmod(self, obj):
        return obj.updated_at


SITEMAPS = {
    "static": StaticViewSitemap,
    "solutions": SolutionSitemap,
    "industries": IndustrySitemap,
    "projects": ProjectSitemap,
    "team": TeamSitemap,
    "jobs": JobSitemap,
    "resources": ResourceSitemap,
    "blog": BlogSitemap,
}
