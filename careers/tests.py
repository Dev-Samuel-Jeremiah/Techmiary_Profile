"""Tests for job listings and applications."""
import datetime
import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from core.models import SiteSettings

from .models import Department, JobApplication, JobOpening

MEDIA = None


def make_cv(name="cv.pdf", size=1024):
    return SimpleUploadedFile(name, b"%PDF-1.4\n" + b"x" * size, content_type="application/pdf")


def base_payload():
    return {
        "full_name": "Ada Nwosu",
        "email": "ada@example.com",
        "phone": "+2348000000000",
        "location": "Jos, Nigeria",
        "cover_letter": "I have built Django systems for schools and want to do more of it.",
        "portfolio_url": "",
        "linkedin_url": "",
        "consent": "on",
        "website": "",
    }


class JobOpeningModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department = Department.objects.create(name="Engineering")

    def test_slug_and_posted_date_on_publish(self):
        job = JobOpening.objects.create(
            title="Backend Engineer",
            department=self.department,
            summary="Build Django services.",
            description="Full description.",
            status=JobOpening.STATUS_OPEN,
            is_published=True,
        )
        self.assertEqual(job.slug, "backend-engineer")
        self.assertIsNotNone(job.posted_at)
        self.assertEqual(job.get_absolute_url(), "/careers/backend-engineer/")
        self.assertEqual(str(job), "Backend Engineer")

    def test_line_fields_are_parsed_into_lists(self):
        job = JobOpening.objects.create(
            title="Role",
            department=self.department,
            summary="x",
            description="y",
            responsibilities="Ship features\n\nReview code",
            requirements="  Python  \nDjango",
        )
        self.assertEqual(job.responsibility_list, ["Ship features", "Review code"])
        self.assertEqual(job.requirement_list, ["Python", "Django"])

    def test_draft_and_closed_roles_are_not_open(self):
        draft = JobOpening.objects.create(
            title="Draft Role", department=self.department, summary="x", description="y"
        )
        self.assertFalse(draft.is_accepting_applications)
        self.assertEqual(JobOpening.open_roles.count(), 0)

    def test_a_role_past_its_closing_date_stops_accepting(self):
        job = JobOpening.objects.create(
            title="Expired Role",
            department=self.department,
            summary="x",
            description="y",
            status=JobOpening.STATUS_OPEN,
            is_published=True,
            closes_at=datetime.date(2020, 1, 1),
        )
        self.assertFalse(job.is_accepting_applications)


class JobListViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        SiteSettings.objects.create(
            name="Samuel Jeremiah",
            brand_name="TECHMIARY",
            company_name="Techmiary Technology Concepts",
            professional_title="Software Engineering & Product Company",
            short_bio="x",
        )
        cls.engineering = Department.objects.create(name="Engineering")
        cls.support = Department.objects.create(name="Delivery & Support")
        cls.open_job = JobOpening.objects.create(
            title="Backend Engineer",
            department=cls.engineering,
            summary="Build Django services.",
            description="Full description.",
            status=JobOpening.STATUS_OPEN,
            is_published=True,
        )
        JobOpening.objects.create(
            title="Unpublished Role",
            department=cls.support,
            summary="x",
            description="y",
        )

    def test_only_open_published_roles_are_listed(self):
        response = self.client.get(reverse("careers:list"))
        titles = [j.title for j in response.context["jobs"]]
        self.assertEqual(titles, ["Backend Engineer"])
        self.assertNotContains(response, "Unpublished Role")

    def test_department_filter(self):
        response = self.client.get(reverse("careers:list"), {"department": "engineering"})
        self.assertEqual([j.title for j in response.context["jobs"]], ["Backend Engineer"])

    def test_empty_state_when_nothing_is_open(self):
        JobOpening.objects.all().update(status=JobOpening.STATUS_CLOSED)
        response = self.client.get(reverse("careers:list"))
        self.assertContains(response, "No open roles right now")

    def test_detail_emits_jobposting_json_ld(self):
        body = self.client.get(self.open_job.get_absolute_url()).content.decode()
        self.assertIn('"@type": "JobPosting"', body)

    def test_unknown_role_is_404(self):
        self.assertEqual(self.client.get("/careers/no-such-role/").status_code, 404)


@override_settings(MEDIA_ROOT="/tmp/techmiary-test-media")
class JobApplicationTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(name="Engineering")
        self.job = JobOpening.objects.create(
            title="Backend Engineer",
            department=self.department,
            summary="Build Django services.",
            description="Full description.",
            status=JobOpening.STATUS_OPEN,
            is_published=True,
        )

    def test_valid_application_is_stored(self):
        response = self.client.post(
            reverse("careers:apply", args=[self.job.slug]),
            {**base_payload(), "cv": make_cv()},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(JobApplication.objects.count(), 1)
        application = JobApplication.objects.get()
        self.assertEqual(application.job, self.job)
        self.assertEqual(application.status, JobApplication.STATUS_NEW)
        self.assertIsNotNone(application.ip_address)
        self.assertContains(response, "your application has been received")

    def test_cv_is_required(self):
        payload = base_payload()
        response = self.client.post(reverse("careers:apply", args=[self.job.slug]), payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(JobApplication.objects.count(), 0)

    def test_consent_is_required(self):
        payload = base_payload()
        payload.pop("consent")
        self.client.post(
            reverse("careers:apply", args=[self.job.slug]), {**payload, "cv": make_cv()}
        )
        self.assertEqual(JobApplication.objects.count(), 0)

    def test_disallowed_file_type_is_rejected(self):
        bad = SimpleUploadedFile("cv.exe", b"MZ", content_type="application/octet-stream")
        self.client.post(
            reverse("careers:apply", args=[self.job.slug]), {**base_payload(), "cv": bad}
        )
        self.assertEqual(JobApplication.objects.count(), 0)

    def test_oversized_cv_is_rejected(self):
        big = SimpleUploadedFile("cv.pdf", b"x" * (6 * 1024 * 1024), content_type="application/pdf")
        self.client.post(
            reverse("careers:apply", args=[self.job.slug]), {**base_payload(), "cv": big}
        )
        self.assertEqual(JobApplication.objects.count(), 0)

    def test_honeypot_blocks_bots(self):
        payload = {**base_payload(), "website": "http://spam.example", "cv": make_cv()}
        self.client.post(reverse("careers:apply", args=[self.job.slug]), payload)
        self.assertEqual(JobApplication.objects.count(), 0)

    def test_closed_role_refuses_applications(self):
        self.job.status = JobOpening.STATUS_CLOSED
        self.job.save()
        response = self.client.post(
            reverse("careers:apply", args=[self.job.slug]),
            {**base_payload(), "cv": make_cv()},
            follow=True,
        )
        self.assertEqual(JobApplication.objects.count(), 0)
        self.assertContains(response, "no longer accepting applications")

    def test_get_on_apply_redirects_to_the_role(self):
        response = self.client.get(reverse("careers:apply", args=[self.job.slug]))
        self.assertRedirects(response, self.job.get_absolute_url())

    def test_csrf_is_enforced(self):
        client = self.client_class(enforce_csrf_checks=True)
        response = client.post(
            reverse("careers:apply", args=[self.job.slug]),
            {**base_payload(), "cv": make_cv()},
        )
        self.assertEqual(response.status_code, 403)

    def tearDown(self):
        import shutil

        shutil.rmtree("/tmp/techmiary-test-media", ignore_errors=True)
