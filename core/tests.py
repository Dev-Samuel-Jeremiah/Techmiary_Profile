"""Tests for site settings, skills, SEO metadata, error handling and the seeder."""
from django.core.management import call_command
from django.http import HttpResponse
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from core.models import SiteSettings, Skill, SkillCategory, SocialLink
from projects.models import Project, ProjectCategory


class SiteSettingsModelTests(TestCase):
    def test_str_and_meta_fallbacks(self):
        site = SiteSettings.objects.create(
            name="Samuel Jeremiah",
            brand_name="TECHMIARY",
            professional_title="Software Engineer & Product Builder",
            short_bio="Builds practical software systems.",
        )
        self.assertEqual(str(site), "Site settings (TECHMIARY)")
        self.assertEqual(
            site.resolved_meta_title,
            "Samuel Jeremiah — Software Engineer & Product Builder",
        )
        self.assertEqual(site.resolved_meta_description, "Builds practical software systems.")

    def test_second_record_is_rejected_by_validation(self):
        SiteSettings.objects.create(
            name="A", brand_name="B", professional_title="C", short_bio="D"
        )
        from django.core.exceptions import ValidationError

        duplicate = SiteSettings(name="X", brand_name="Y", professional_title="Z", short_bio="W")
        with self.assertRaises(ValidationError):
            duplicate.full_clean()


class SkillModelTests(TestCase):
    def test_category_slug_is_generated(self):
        category = SkillCategory.objects.create(name="Cloud & Storage")
        self.assertEqual(category.slug, "cloud-storage")

    def test_skill_str(self):
        category = SkillCategory.objects.create(name="Backend")
        skill = Skill.objects.create(category=category, name="Django")
        self.assertEqual(str(skill), "Django (Backend)")


class SocialLinkTests(TestCase):
    def test_only_active_links_reach_the_template_context(self):
        SocialLink.objects.create(name="GitHub", url="https://github.com/example", icon="github")
        SocialLink.objects.create(
            name="Hidden", url="https://example.com", icon="link", is_active=False
        )
        response = self.client.get(reverse("core:home"))
        names = [link.name for link in response.context["social_links"]]
        self.assertIn("GitHub", names)
        self.assertNotIn("Hidden", names)


class PublicPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.site = SiteSettings.objects.create(
            name="Samuel Jeremiah",
            brand_name="TECHMIARY",
            company_name="Techmiary Technology Concepts",
            professional_title="Software Engineer & Product Builder",
            short_bio="Builds SaaS, EdTech and business information systems.",
            website_url="https://techmiary.cloud",
        )
        category = ProjectCategory.objects.create(name="SaaS / School ERP")
        Project.objects.create(
            title="Techmiary Cloud",
            slug="techmiary-cloud",
            category=category,
            short_description="A multi-tenant school management platform.",
            featured=True,
        )

    def test_every_public_page_returns_200(self):
        for name in [
            "core:home",
            "core:about",
            "core:skills",
            "core:privacy",
            "core:terms",
            "projects:list",
            "experience:list",
            "services:list",
            "blog:list",
            "contact:contact",
        ]:
            with self.subTest(url=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_homepage_shows_the_owner_and_brand(self):
        response = self.client.get(reverse("core:home"))
        self.assertContains(response, "Samuel Jeremiah")
        self.assertContains(response, "TECHMIARY")
        self.assertContains(response, "Software Engineer &amp; Product Builder")

    def test_homepage_has_unique_title_canonical_and_open_graph(self):
        response = self.client.get(reverse("core:home"))
        self.assertContains(
            response,
            "<title>Techmiary Technology Concepts — Software Engineer &amp; Product Builder</title>",
            html=False,
        )
        self.assertContains(response, 'rel="canonical"')
        self.assertContains(response, 'property="og:title"')
        self.assertContains(response, 'name="twitter:card"')
        self.assertContains(response, 'name="description"')

    def test_homepage_emits_person_and_organization_json_ld(self):
        response = self.client.get(reverse("core:home"))
        body = response.content.decode()
        self.assertIn('application/ld+json', body)
        self.assertIn('"@type": "Person"', body)
        self.assertIn('"@type": "Organization"', body)

    def test_titles_differ_between_pages(self):
        home = self.client.get(reverse("core:home")).context["meta_title"]
        about = self.client.get(reverse("core:about")).context["meta_title"]
        projects = self.client.get(reverse("projects:list")).context["meta_title"]
        self.assertEqual(len({home, about, projects}), 3)

    def test_skills_page_lists_active_skills_only(self):
        category = SkillCategory.objects.create(name="Backend")
        Skill.objects.create(category=category, name="Django")
        Skill.objects.create(category=category, name="Retired Tool", is_active=False)
        response = self.client.get(reverse("core:skills"))
        self.assertContains(response, "Django")
        self.assertNotContains(response, "Retired Tool")


class EmptyStateTests(TestCase):
    """With no content at all, pages must still render rather than break."""

    def test_pages_render_without_any_records(self):
        for name in ["core:home", "projects:list", "blog:list", "services:list", "experience:list", "core:skills"]:
            with self.subTest(url=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)

    def test_empty_project_list_shows_an_empty_state(self):
        response = self.client.get(reverse("projects:list"))
        self.assertContains(response, "No case studies published yet")


class ErrorHandlingTests(TestCase):
    def test_unknown_url_returns_404(self):
        response = self.client.get("/this-page-does-not-exist/")
        self.assertEqual(response.status_code, 404)

    def test_404_uses_the_site_template(self):
        response = self.client.get("/nope/")
        self.assertContains(response, "This page doesn", status_code=404)


class RobotsAndSitemapTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        category = ProjectCategory.objects.create(name="SaaS")
        Project.objects.create(
            title="Techmiary Cloud",
            slug="techmiary-cloud",
            category=category,
            short_description="Platform.",
        )

    def test_robots_txt(self):
        response = self.client.get("/robots.txt")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/plain")
        self.assertContains(response, "Disallow: /admin/")
        self.assertContains(response, "Sitemap:")

    def test_sitemap_lists_static_pages_and_projects(self):
        response = self.client.get("/sitemap.xml")
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("/projects/techmiary-cloud/", body)
        self.assertIn("/about/", body)


class SecurityHeaderTests(TestCase):
    def test_public_pages_carry_csp_and_permissions_policy(self):
        response = self.client.get(reverse("core:home"))
        self.assertIn("Content-Security-Policy", response)
        self.assertIn("Permissions-Policy", response)
        self.assertEqual(response["X-Frame-Options"], "DENY")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")


class SeedCommandTests(TestCase):
    def test_seed_is_idempotent(self):
        call_command("seed_portfolio", verbosity=0)
        counts = (
            SiteSettings.objects.count(),
            Project.objects.count(),
            Skill.objects.count(),
            SkillCategory.objects.count(),
        )
        call_command("seed_portfolio", verbosity=0)
        self.assertEqual(
            counts,
            (
                SiteSettings.objects.count(),
                Project.objects.count(),
                Skill.objects.count(),
                SkillCategory.objects.count(),
            ),
        )

    def test_seed_does_not_mark_projects_live_or_invent_clients(self):
        call_command("seed_portfolio", verbosity=0)
        for project in Project.objects.all():
            self.assertNotEqual(project.status, Project.STATUS_LIVE)
            self.assertEqual(project.client, "")

    def test_seed_creates_no_social_links(self):
        call_command("seed_portfolio", verbosity=0)
        self.assertEqual(SocialLink.objects.count(), 0)


class AdminRegistrationTests(TestCase):
    def test_every_content_model_is_registered(self):
        from django.contrib import admin

        from blog.models import BlogCategory, BlogPost
        from contact.models import ContactMessage
        from experience.models import Experience
        from projects.models import ProjectFeature, Technology
        from services.models import Service

        for model in [
            SiteSettings,
            SocialLink,
            SkillCategory,
            Skill,
            Project,
            ProjectCategory,
            ProjectFeature,
            Technology,
            Experience,
            Service,
            BlogCategory,
            BlogPost,
            ContactMessage,
        ]:
            with self.subTest(model=model.__name__):
                self.assertIn(model, admin.site._registry)


@override_settings(SITE_URL="https://example.test")
class CanonicalUrlTests(TestCase):
    def test_canonical_uses_site_url(self):
        response = self.client.get(reverse("core:about"))
        self.assertEqual(response.context["canonical_url"], "https://example.test/about/")


class SecurityHeaderTests(TestCase):
    """The CSP exemption has to follow ADMIN_URL, not a hard-coded path."""

    def test_site_pages_receive_csp(self):
        response = self.client.get("/")
        self.assertIn("Content-Security-Policy", response)
        self.assertIn("Permissions-Policy", response)

    @override_settings(ADMIN_URL="admin/")
    def test_admin_is_exempt_from_site_csp(self):
        response = self.client.get("/admin/", follow=False)
        self.assertNotIn("Content-Security-Policy", response)
        self.assertIn("Permissions-Policy", response)

    def test_exemption_follows_a_relocated_admin(self):
        """
        Moving the admin off /admin/ must not start applying the site CSP to
        it — the admin needs its own inline scripts.
        """
        from core.middleware import SecurityHeadersMiddleware

        with override_settings(ADMIN_URL="secret-panel/"):
            middleware = SecurityHeadersMiddleware(lambda r: HttpResponse("ok"))
            request = RequestFactory().get("/secret-panel/")
            response = middleware(request)
            self.assertNotIn("Content-Security-Policy", response)

            request = RequestFactory().get("/projects/")
            response = middleware(request)
            self.assertIn("Content-Security-Policy", response)


class AdminQueryCountTests(TestCase):
    """
    Admin list columns that show a related count must be annotated onto the
    row query. Calling ``obj.related.count()`` per row issues one COUNT per
    row, which degrades badly as content grows.
    """

    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth import get_user_model
        from blog.models import BlogCategory
        from projects.models import ProjectCategory, Technology

        cls.user = get_user_model().objects.create_superuser(
            "counter", "counter@example.com", "pw-for-tests-only"
        )
        for i in range(20):
            ProjectCategory.objects.create(name=f"Cat {i}", display_order=i)
            Technology.objects.create(name=f"Tech {i}")
            BlogCategory.objects.create(name=f"Blog cat {i}")

    def setUp(self):
        self.client.force_login(self.user)

    def assert_no_count_per_row(self, url):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        counts = [q for q in ctx.captured_queries if "COUNT(" in q["sql"].upper()]
        # Django itself runs a couple of COUNTs for pagination; one per row
        # would be 20+.
        self.assertLess(
            len(counts), 6, f"{url} ran {len(counts)} COUNT queries — likely one per row"
        )

    def test_project_category_list(self):
        self.assert_no_count_per_row("/admin/projects/projectcategory/")

    def test_technology_list(self):
        self.assert_no_count_per_row("/admin/projects/technology/")

    def test_blog_category_list(self):
        self.assert_no_count_per_row("/admin/blog/blogcategory/")

    def test_skill_category_list(self):
        self.assert_no_count_per_row("/admin/core/skillcategory/")


class TemplateHygieneTests(TestCase):
    """
    Guards against template mistakes that render as visible text rather than
    raising, so they reach production looking like content.
    """

    def _templates(self):
        import pathlib

        from django.conf import settings

        for directory in settings.TEMPLATES[0]["DIRS"]:
            yield from pathlib.Path(directory).rglob("*.html")

    def test_no_multiline_django_comments(self):
        """
        ``{# ... #}`` must open and close on one line. Django does not treat a
        multi-line version as a comment — it prints it on the page.
        """
        offenders = []
        for path in self._templates():
            source = path.read_text()
            cursor = 0
            while True:
                start = source.find("{#", cursor)
                if start == -1:
                    break
                end = source.find("#}", start)
                if end == -1 or "\n" in source[start:end]:
                    offenders.append(f"{path.name}:{source[:start].count(chr(10)) + 1}")
                cursor = start + 2

        self.assertEqual(
            offenders,
            [],
            "Multi-line {# #} comments render as visible text; use "
            "{% comment %} or keep them on one line: " + ", ".join(offenders),
        )

    def test_no_unrendered_template_syntax_on_the_homepage(self):
        """A rendered page should never contain raw tag or comment delimiters."""
        call_command("seed_portfolio", verbosity=0)
        html = self.client.get(reverse("core:home")).content.decode()
        # `{{`/`}}` are excluded: nested JSON-LD objects legitimately end in `}}`.
        for token in ("{#", "#}", "{%", "%}"):
            self.assertNotIn(token, html, f"Unrendered {token!r} found in the homepage HTML")


class PartnerTests(TestCase):
    """Partners and trusted-by entries on the landing page."""

    def setUp(self):
        from core.models import Partner

        self.Partner = Partner
        call_command("seed_portfolio", verbosity=0)

    def test_section_is_absent_when_nothing_is_published(self):
        """An empty roster must not leave an empty heading on the page."""
        response = self.client.get(reverse("core:home"))
        self.assertNotContains(response, "Partners and trusted by")

    def test_partners_and_trusted_render_in_their_own_groups(self):
        self.Partner.objects.create(
            name="Northwind Cloud",
            kind=self.Partner.KIND_PARTNER,
            relationship="Infrastructure partner",
        )
        self.Partner.objects.create(
            name="Bright Future Academy", kind=self.Partner.KIND_TRUSTED
        )
        response = self.client.get(reverse("core:home"))
        self.assertContains(response, "Partners and trusted by")
        self.assertContains(response, "Northwind Cloud")
        self.assertContains(response, "Infrastructure partner")
        self.assertContains(response, "Bright Future Academy")
        self.assertContains(response, "Trusted by")
        self.assertEqual(len(response.context["partners"]), 1)
        self.assertEqual(len(response.context["trusted_by"]), 1)

    def test_only_the_populated_group_gets_a_heading(self):
        self.Partner.objects.create(name="Solo Partner", kind=self.Partner.KIND_PARTNER)
        response = self.client.get(reverse("core:home"))
        self.assertContains(response, "Solo Partner")
        self.assertNotContains(response, "Trusted by")

    def test_inactive_entries_are_hidden(self):
        self.Partner.objects.create(
            name="Former Partner", kind=self.Partner.KIND_PARTNER, is_active=False
        )
        response = self.client.get(reverse("core:home"))
        self.assertNotContains(response, "Former Partner")

    def test_entries_without_a_logo_fall_back_to_a_wordmark(self):
        self.Partner.objects.create(name="No Logo Ltd", kind=self.Partner.KIND_PARTNER)
        response = self.client.get(reverse("core:home"))
        self.assertContains(response, "logo-cell__word")
        self.assertContains(response, "No Logo Ltd")

    def test_display_order_is_respected(self):
        self.Partner.objects.create(
            name="Second", kind=self.Partner.KIND_PARTNER, display_order=2
        )
        self.Partner.objects.create(
            name="First", kind=self.Partner.KIND_PARTNER, display_order=1
        )
        response = self.client.get(reverse("core:home"))
        names = [p.name for p in response.context["partners"]]
        self.assertEqual(names, ["First", "Second"])

    def test_the_same_name_can_exist_in_both_groups_but_not_twice_in_one(self):
        from django.db import IntegrityError, transaction

        self.Partner.objects.create(name="Acme", kind=self.Partner.KIND_PARTNER)
        # Same organisation may legitimately be both a partner and a client.
        self.Partner.objects.create(name="Acme", kind=self.Partner.KIND_TRUSTED)
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.Partner.objects.create(name="Acme", kind=self.Partner.KIND_PARTNER)

    def test_one_query_covers_both_groups(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        for i in range(8):
            self.Partner.objects.create(name=f"P{i}", kind=self.Partner.KIND_PARTNER)
            self.Partner.objects.create(name=f"T{i}", kind=self.Partner.KIND_TRUSTED)
        with CaptureQueriesContext(connection) as ctx:
            self.client.get(reverse("core:home"))
        partner_queries = [
            q for q in ctx.captured_queries if "core_partner" in q["sql"]
        ]
        self.assertEqual(len(partner_queries), 1, "partners should load in one query")


class CompanyNavigationTests(TestCase):
    """The corporate navigation and footer must reach every public section."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_portfolio", verbosity=0)

    def test_navigation_links_to_every_main_section(self):
        response = self.client.get(reverse("core:home"))
        for path in [
            "/solutions/",
            "/industries/",
            "/services/",
            "/projects/",
            "/about/",
            "/team/",
            "/clients/",
            "/careers/",
            "/technology/",
            "/blog/",
            "/resources/",
            "/faq/",
            "/contact/",
            "/quote/",
        ]:
            with self.subTest(path=path):
                self.assertContains(response, f'href="{path}"')

    def test_seeded_solutions_appear_in_the_menu(self):
        response = self.client.get(reverse("core:home"))
        self.assertTrue(len(response.context["nav_solutions"]) > 0)
        self.assertTrue(len(response.context["nav_industries"]) > 0)

    def test_old_skills_url_redirects_to_technology(self):
        response = self.client.get("/skills/")
        self.assertRedirects(response, "/technology/", status_code=301)

    def test_every_company_page_returns_200(self):
        for name in [
            "company:solution_list",
            "company:industry_list",
            "company:team_list",
            "company:client_list",
            "company:resource_list",
            "company:faq",
            "careers:list",
            "contact:quote",
            "core:skills",
        ]:
            with self.subTest(url=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_sitemap_covers_the_new_sections(self):
        body = self.client.get("/sitemap.xml").content.decode()
        for path in ["/solutions/", "/industries/", "/team/", "/careers/", "/faq/", "/quote/"]:
            with self.subTest(path=path):
                self.assertIn(path, body)


class SeededCredibilityTests(TestCase):
    """The seeder must not invent clients, quotes, vacancies or statistics."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_portfolio", verbosity=0)

    def test_no_clients_testimonials_or_vacancies_are_invented(self):
        from careers.models import JobOpening
        from company.models import Client, Milestone, Resource, Testimonial

        self.assertEqual(Client.objects.count(), 0)
        self.assertEqual(Testimonial.objects.count(), 0)
        self.assertEqual(JobOpening.objects.count(), 0)
        self.assertEqual(Resource.objects.count(), 0)
        self.assertEqual(Milestone.objects.count(), 0)

    def test_seeded_solutions_link_to_their_case_studies(self):
        from company.models import Solution

        linked = Solution.objects.exclude(related_project=None)
        self.assertEqual(linked.count(), 4)

    def test_seed_is_idempotent_for_company_content(self):
        from company.models import FAQ, Industry, Solution

        before = (Solution.objects.count(), Industry.objects.count(), FAQ.objects.count())
        call_command("seed_portfolio", verbosity=0)
        after = (Solution.objects.count(), Industry.objects.count(), FAQ.objects.count())
        self.assertEqual(before, after)
