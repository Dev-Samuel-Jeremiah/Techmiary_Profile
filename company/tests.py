"""Tests for solutions, industries, team, clients, resources and the FAQ."""
from django.test import TestCase
from django.urls import reverse

from core.models import SiteSettings
from projects.models import Project, ProjectCategory

from .models import (
    FAQ,
    Client,
    CompanyValue,
    FAQCategory,
    Industry,
    Milestone,
    Resource,
    ResourceCategory,
    Solution,
    SolutionCapability,
    TeamMember,
    Testimonial,
)


def make_site():
    return SiteSettings.objects.create(
        name="Samuel Jeremiah",
        brand_name="TECHMIARY",
        company_name="Techmiary Technology Concepts",
        professional_title="Software Engineering & Product Company",
        short_bio="Builds SaaS, EdTech and business information systems.",
        company_overview="A software engineering and product company.",
        website_url="https://techmiary.cloud",
    )


class SolutionModelTests(TestCase):
    def test_slug_url_and_fallbacks(self):
        solution = Solution.objects.create(
            name="School ERP Platform", tagline="SaaS / School ERP", summary="A platform."
        )
        self.assertEqual(solution.slug, "school-erp-platform")
        self.assertEqual(solution.get_absolute_url(), "/solutions/school-erp-platform/")
        self.assertEqual(solution.resolved_meta_title, "School ERP Platform — Solutions")
        self.assertEqual(solution.resolved_meta_description, "A platform.")
        self.assertEqual(solution.image_alt, "School ERP Platform interface")
        self.assertEqual(str(solution), "School ERP Platform")

    def test_active_manager_filters_inactive(self):
        Solution.objects.create(name="Live", tagline="t", summary="s")
        Solution.objects.create(name="Retired", tagline="t", summary="s", is_active=False)
        self.assertEqual(Solution.objects.active().count(), 1)


class IndustryModelTests(TestCase):
    def test_slug_and_challenge_parsing(self):
        industry = Industry.objects.create(
            name="Government & Public Sector",
            summary="Auditable records.",
            challenges="Paper records\n\nSlow reporting\n  Access control  ",
        )
        self.assertEqual(industry.slug, "government-public-sector")
        self.assertEqual(
            industry.challenge_list, ["Paper records", "Slow reporting", "Access control"]
        )


class TeamMemberModelTests(TestCase):
    def test_initials_and_alt_text(self):
        member = TeamMember.objects.create(name="Samuel Jeremiah", role="Founder")
        self.assertEqual(member.initials, "SJ")
        self.assertEqual(member.image_alt, "Portrait of Samuel Jeremiah")
        self.assertEqual(member.get_absolute_url(), "/team/samuel-jeremiah/")
        self.assertFalse(member.has_social)
        member.linkedin_url = "https://linkedin.com/in/example"
        self.assertTrue(member.has_social)


class ResourceModelTests(TestCase):
    def test_availability_depends_on_a_file_or_link(self):
        resource = Resource.objects.create(title="Procurement guide", summary="x")
        self.assertFalse(resource.is_available)
        resource.external_url = "https://example.com/guide.pdf"
        self.assertTrue(resource.is_available)
        self.assertEqual(resource.download_url, "https://example.com/guide.pdf")


class TestimonialModelTests(TestCase):
    def test_attribution_skips_blank_parts(self):
        testimonial = Testimonial.objects.create(
            quote="Good work.", author_name="A. Name", organisation="Example Ltd"
        )
        self.assertEqual(testimonial.attribution, "Example Ltd")
        testimonial.author_role = "Head of IT"
        self.assertEqual(testimonial.attribution, "Head of IT, Example Ltd")


class SolutionViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        make_site()
        cls.industry = Industry.objects.create(name="Education", summary="Schools.")
        cls.solution = Solution.objects.create(
            name="School ERP Platform",
            tagline="SaaS / School ERP",
            summary="Multi-tenant school management.",
            overview="A longer overview of the platform.",
            is_featured=True,
        )
        cls.solution.industries.add(cls.industry)
        SolutionCapability.objects.create(
            solution=cls.solution, title="Attendance", description="Daily capture."
        )
        Solution.objects.create(name="Hidden", tagline="t", summary="s", is_active=False)

    def test_list_shows_active_solutions_only(self):
        response = self.client.get(reverse("company:solution_list"))
        names = [s.name for s in response.context["solutions"]]
        self.assertIn("School ERP Platform", names)
        self.assertNotIn("Hidden", names)

    def test_detail_renders_capabilities(self):
        response = self.client.get(self.solution.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Attendance")
        self.assertContains(response, "A longer overview of the platform.")

    def test_detail_emits_product_json_ld(self):
        body = self.client.get(self.solution.get_absolute_url()).content.decode()
        self.assertIn('"@type": "Product"', body)
        self.assertNotIn("aggregateRating", body)

    def test_inactive_solution_is_404(self):
        self.assertEqual(self.client.get("/solutions/hidden/").status_code, 404)

    def test_quote_link_carries_the_solution(self):
        response = self.client.get(self.solution.get_absolute_url())
        self.assertContains(response, "/quote/?solution=school-erp-platform")


class IndustryViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        make_site()
        cls.industry = Industry.objects.create(
            name="Education", summary="Schools need joined-up records."
        )

    def test_list_and_detail(self):
        self.assertEqual(self.client.get(reverse("company:industry_list")).status_code, 200)
        response = self.client.get(self.industry.get_absolute_url())
        self.assertContains(response, "Schools need joined-up records.")

    def test_empty_list_shows_empty_state(self):
        Industry.objects.all().delete()
        response = self.client.get(reverse("company:industry_list"))
        self.assertContains(response, "No industries listed yet")


class TeamViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        make_site()
        cls.founder = TeamMember.objects.create(
            name="Samuel Jeremiah",
            role="Founder & Chief Executive",
            is_leadership=True,
            is_founder=True,
            bio="Builds software.",
        )
        TeamMember.objects.create(name="Hidden Person", role="Nobody", is_active=False)

    def test_list_separates_leadership(self):
        response = self.client.get(reverse("company:team_list"))
        self.assertIn(self.founder, response.context["leadership"])
        self.assertNotContains(response, "Hidden Person")

    def test_detail_shows_founder_career_history(self):
        import datetime

        from experience.models import Experience

        Experience.objects.create(
            organization="Techmiary", position="Engineer", start_date=datetime.date(2022, 1, 1)
        )
        response = self.client.get(self.founder.get_absolute_url())
        self.assertContains(response, "Professional background")
        self.assertContains(response, "Techmiary")

    def test_detail_emits_person_json_ld(self):
        body = self.client.get(self.founder.get_absolute_url()).content.decode()
        self.assertIn('"@type": "Person"', body)

    def test_inactive_member_is_404(self):
        self.assertEqual(self.client.get("/team/hidden-person/").status_code, 404)


class ClientViewTests(TestCase):
    def setUp(self):
        make_site()

    def test_empty_state_when_no_clients(self):
        response = self.client.get(reverse("company:client_list"))
        self.assertContains(response, "No clients listed yet")

    def test_clients_and_testimonials_render(self):
        client = Client.objects.create(
            name="Bright Future Academy", engagement="School ERP deployment", consent_on_file=True
        )
        Testimonial.objects.create(
            quote="It replaced four spreadsheets.",
            author_name="A. Name",
            organisation="Bright Future Academy",
            client=client,
            consent_on_file=True,
        )
        response = self.client.get(reverse("company:client_list"))
        self.assertContains(response, "Bright Future Academy")
        self.assertContains(response, "It replaced four spreadsheets.")

    def test_inactive_client_is_hidden(self):
        Client.objects.create(name="Former Client", is_active=False)
        response = self.client.get(reverse("company:client_list"))
        self.assertNotContains(response, "Former Client")


class ResourceViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        make_site()
        cls.category = ResourceCategory.objects.create(name="Planning")
        cls.resource = Resource.objects.create(
            title="Procurement checklist",
            summary="What to settle before you buy.",
            category=cls.category,
            external_url="https://example.com/checklist.pdf",
        )

    def test_list_and_category_filter(self):
        response = self.client.get(reverse("company:resource_list"))
        self.assertContains(response, "Procurement checklist")
        response = self.client.get(reverse("company:resource_list"), {"category": "planning"})
        self.assertEqual(list(response.context["resources"]), [self.resource])

    def test_resource_without_a_file_is_marked_on_request(self):
        Resource.objects.all().update(external_url="")
        response = self.client.get(reverse("company:resource_list"))
        self.assertContains(response, "Available on request")

    def test_empty_state(self):
        Resource.objects.all().delete()
        response = self.client.get(reverse("company:resource_list"))
        self.assertContains(response, "No resources published yet")


class FAQViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        make_site()
        category = FAQCategory.objects.create(name="Projects & pricing")
        FAQ.objects.create(
            category=category,
            question="How much does a project cost?",
            answer="It depends entirely on scope.",
        )
        FAQ.objects.create(question="Hidden question", answer="x", is_active=False)

    def test_questions_render_grouped(self):
        response = self.client.get(reverse("company:faq"))
        self.assertContains(response, "How much does a project cost?")
        self.assertContains(response, "Projects &amp; pricing")
        self.assertNotContains(response, "Hidden question")

    def test_faq_page_emits_faqpage_json_ld(self):
        body = self.client.get(reverse("company:faq")).content.decode()
        self.assertIn('"@type": "FAQPage"', body)
        self.assertIn('"@type": "Question"', body)

    def test_search_filters_questions(self):
        response = self.client.get(reverse("company:faq"), {"q": "cost"})
        self.assertContains(response, "How much does a project cost?")
        response = self.client.get(reverse("company:faq"), {"q": "kubernetes"})
        self.assertContains(response, "No matching questions")


class AboutPageTests(TestCase):
    def setUp(self):
        make_site()

    def test_about_renders_values_and_milestones(self):
        CompanyValue.objects.create(title="Build useful software", description="Yes.")
        Milestone.objects.create(year=2023, title="Company founded")
        response = self.client.get(reverse("core:about"))
        self.assertContains(response, "Build useful software")
        self.assertContains(response, "Company founded")

    def test_about_emits_organization_json_ld(self):
        body = self.client.get(reverse("core:about")).content.decode()
        self.assertIn('"@type": "Organization"', body)

    def test_at_a_glance_counts_are_real_row_counts(self):
        category = ProjectCategory.objects.create(name="SaaS")
        Project.objects.create(title="One", category=category, short_description="x")
        response = self.client.get(reverse("core:about"))
        self.assertEqual(response.context["project_count"], 1)
