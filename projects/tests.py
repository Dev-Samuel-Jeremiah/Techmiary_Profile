from django.test import TestCase
from django.urls import reverse

from core.models import SiteSettings

from .models import Project, ProjectCategory, ProjectFeature, Technology


class ProjectModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = ProjectCategory.objects.create(name="SaaS / School ERP")

    def test_slug_is_generated_from_the_title(self):
        project = Project.objects.create(
            title="Techmiary Cloud",
            category=self.category,
            short_description="Platform.",
        )
        self.assertEqual(project.slug, "techmiary-cloud")
        self.assertEqual(project.get_absolute_url(), "/projects/techmiary-cloud/")

    def test_str_and_meta_fallbacks(self):
        project = Project.objects.create(
            title="WDA SMS", category=self.category, short_description="School platform."
        )
        self.assertEqual(str(project), "WDA SMS")
        self.assertEqual(project.resolved_meta_title, "WDA SMS — Case Study")
        self.assertEqual(project.resolved_meta_description, "School platform.")

    def test_cover_alt_text_falls_back_to_a_description(self):
        project = Project.objects.create(
            title="Diction Masters", category=self.category, short_description="EdTech."
        )
        self.assertEqual(project.cover_alt_text, "Diction Masters interface screenshot")

    def test_status_defaults_to_development_not_live(self):
        project = Project.objects.create(
            title="New System", category=self.category, short_description="x"
        )
        self.assertEqual(project.status, Project.STATUS_DEVELOPMENT)

    def test_published_manager_excludes_unpublished(self):
        Project.objects.create(
            title="Live One", category=self.category, short_description="x"
        )
        Project.objects.create(
            title="Draft One", category=self.category, short_description="x", is_published=False
        )
        self.assertEqual(Project.published.count(), 1)

    def test_technology_slug_is_generated(self):
        technology = Technology.objects.create(name="Django REST Framework")
        self.assertEqual(technology.slug, "django-rest-framework")


class ProjectListViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        SiteSettings.objects.create(
            name="Samuel Jeremiah",
            brand_name="TECHMIARY",
            professional_title="Software Engineer & Product Builder",
            short_bio="Builds software.",
        )
        cls.saas = ProjectCategory.objects.create(name="SaaS / School ERP")
        cls.edtech = ProjectCategory.objects.create(name="EdTech / Language Learning")
        cls.featured = Project.objects.create(
            title="Techmiary Cloud",
            category=cls.saas,
            short_description="Multi-tenant school platform.",
            featured=True,
        )
        Project.objects.create(
            title="Diction Masters",
            category=cls.edtech,
            short_description="Pronunciation and vocabulary platform.",
        )
        Project.objects.create(
            title="Hidden Project",
            category=cls.saas,
            short_description="Not ready.",
            is_published=False,
        )

    def test_list_shows_published_projects_only(self):
        response = self.client.get(reverse("projects:list"))
        titles = [project.title for project in response.context["projects"]]
        self.assertIn("Techmiary Cloud", titles)
        self.assertIn("Diction Masters", titles)
        self.assertNotIn("Hidden Project", titles)

    def test_category_filter(self):
        response = self.client.get(reverse("projects:list"), {"category": self.edtech.slug})
        titles = [project.title for project in response.context["projects"]]
        self.assertEqual(titles, ["Diction Masters"])

    def test_unknown_category_falls_back_to_everything(self):
        response = self.client.get(reverse("projects:list"), {"category": "nope"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Techmiary Cloud")

    def test_homepage_shows_featured_projects(self):
        response = self.client.get(reverse("core:home"))
        titles = [p.title for p in response.context["featured_projects"]]
        self.assertEqual(titles, ["Techmiary Cloud"])


class ProjectDetailViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        category = ProjectCategory.objects.create(name="SaaS / School ERP")
        cls.project = Project.objects.create(
            title="Techmiary Cloud",
            category=category,
            short_description="Multi-tenant school platform.",
            description="An overview of the platform.",
            problem="Schools track operations across disconnected tools.",
            solution="A single multi-tenant Django application.",
            architecture_description="Browser\nNginx\nGunicorn\nDjango\nPostgreSQL",
            website_url="https://techmiary.cloud",
            year=2024,
        )
        ProjectFeature.objects.create(
            project=cls.project, title="Attendance", description="Daily attendance capture."
        )
        cls.project.technologies.add(Technology.objects.create(name="Django"))
        cls.unpublished = Project.objects.create(
            title="Draft", category=category, short_description="x", is_published=False
        )

    def test_detail_renders_the_case_study_sections(self):
        response = self.client.get(self.project.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Overview")
        self.assertContains(response, "The problem")
        self.assertContains(response, "What we built")
        self.assertContains(response, "Key features")
        self.assertContains(response, "Attendance")
        self.assertContains(response, "Architecture")

    def test_detail_links_to_the_live_website(self):
        response = self.client.get(self.project.get_absolute_url())
        self.assertContains(response, "https://techmiary.cloud")

    def test_detail_emits_software_application_json_ld_without_ratings(self):
        body = self.client.get(self.project.get_absolute_url()).content.decode()
        self.assertIn('"@type": "SoftwareApplication"', body)
        self.assertNotIn("aggregateRating", body)
        self.assertNotIn("reviewCount", body)

    def test_unpublished_project_returns_404(self):
        response = self.client.get(self.unpublished.get_absolute_url())
        self.assertEqual(response.status_code, 404)

    def test_unknown_slug_returns_404(self):
        self.assertEqual(self.client.get("/projects/not-a-project/").status_code, 404)

    def test_detail_sets_its_own_title_and_canonical(self):
        response = self.client.get(self.project.get_absolute_url())
        self.assertEqual(response.context["meta_title"], "Techmiary Cloud — Case Study")
        self.assertTrue(response.context["canonical_url"].endswith("/projects/techmiary-cloud/"))
