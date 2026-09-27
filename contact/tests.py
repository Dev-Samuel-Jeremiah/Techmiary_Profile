from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from .forms import ContactForm
from .models import ContactMessage

VALID = {
    "name": "Adaeze Okoro",
    "email": "adaeze@example.com",
    "phone": "+2348000000000",
    "company": "Bright Future Academy",
    "subject": "School management system",
    "message": "We need a system to manage results, attendance and school fees.",
    "website": "",
}


class ContactFormTests(TestCase):
    def test_valid_submission(self):
        self.assertTrue(ContactForm(data=VALID).is_valid())

    def test_required_fields(self):
        form = ContactForm(data={})
        self.assertFalse(form.is_valid())
        for field in ("name", "email", "subject", "message"):
            self.assertIn(field, form.errors)

    def test_invalid_email_is_rejected(self):
        form = ContactForm(data={**VALID, "email": "not-an-email"})
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_short_message_is_rejected(self):
        form = ContactForm(data={**VALID, "message": "Hi"})
        self.assertFalse(form.is_valid())
        self.assertIn("message", form.errors)

    def test_honeypot_blocks_automated_submissions(self):
        form = ContactForm(data={**VALID, "website": "http://spam.example"})
        self.assertFalse(form.is_valid())
        self.assertIn("website", form.errors)

    def test_link_heavy_message_is_rejected(self):
        form = ContactForm(data={**VALID, "message": "http://a http://b http://c http://d http://e more"})
        self.assertFalse(form.is_valid())


class ContactViewTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_get_renders_the_form_with_a_csrf_token(self):
        response = self.client.get(reverse("contact:contact"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "csrfmiddlewaretoken")

    def test_valid_post_stores_the_message(self):
        response = self.client.post(reverse("contact:contact"), VALID, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ContactMessage.objects.count(), 1)
        message = ContactMessage.objects.get()
        self.assertEqual(message.name, "Adaeze Okoro")
        self.assertEqual(message.status, ContactMessage.STATUS_NEW)
        self.assertIsNotNone(message.ip_address)
        self.assertContains(response, "your message has been received")

    def test_invalid_post_does_not_store_anything(self):
        response = self.client.post(reverse("contact:contact"), {**VALID, "email": "bad"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ContactMessage.objects.count(), 0)

    def test_csrf_is_enforced(self):
        client = self.client_class(enforce_csrf_checks=True)
        response = client.post(reverse("contact:contact"), VALID)
        self.assertEqual(response.status_code, 403)

    @override_settings(CONTACT_RATE_LIMIT=2)
    def test_rate_limit_blocks_further_submissions(self):
        for _ in range(2):
            self.client.post(reverse("contact:contact"), VALID)
        self.assertEqual(ContactMessage.objects.count(), 2)
        response = self.client.post(reverse("contact:contact"), VALID, follow=True)
        self.assertEqual(ContactMessage.objects.count(), 2)
        self.assertContains(response, "sent several messages recently")

    @override_settings(CONTACT_NOTIFICATION_EMAIL="owner@example.com")
    def test_notification_email_is_sent_when_configured(self):
        from django.core import mail

        self.client.post(reverse("contact:contact"), VALID)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("School management system", mail.outbox[0].subject)


class ContactMessageModelTests(TestCase):
    def test_str_and_read_flag(self):
        message = ContactMessage.objects.create(
            name="Adaeze", email="a@example.com", subject="Hello", message="Body"
        )
        self.assertEqual(str(message), "Hello — Adaeze")
        self.assertFalse(message.is_read)
        message.status = ContactMessage.STATUS_REPLIED
        self.assertTrue(message.is_read)


class ClientIPTests(TestCase):
    """
    X-Forwarded-For is caller-supplied, so trusting the left-hand entry lets
    anyone mint a new rate-limit bucket per request.
    """

    def setUp(self):
        cache.clear()

    @override_settings(CONTACT_RATE_LIMIT=2, TRUSTED_PROXY_COUNT=0)
    def test_spoofed_forwarded_header_cannot_bypass_the_rate_limit(self):
        for i in range(4):
            self.client.post(
                reverse("contact:contact"),
                VALID,
                HTTP_X_FORWARDED_FOR=f"203.0.113.{i}",
            )
        # Without the fix each spoofed address got its own bucket and all four
        # were stored; the limit must hold regardless of the header.
        self.assertEqual(ContactMessage.objects.count(), 2)

    @override_settings(TRUSTED_PROXY_COUNT=1)
    def test_one_proxy_hop_reads_the_address_the_proxy_appended(self):
        from contact.views import client_ip
        from django.test import RequestFactory

        request = RequestFactory().get("/")
        # nginx's $proxy_add_x_forwarded_for appends the real peer on the right.
        request.META["HTTP_X_FORWARDED_FOR"] = "1.1.1.1, 2.2.2.2, 198.51.100.7"
        self.assertEqual(client_ip(request), "198.51.100.7")

    @override_settings(TRUSTED_PROXY_COUNT=0)
    def test_header_is_ignored_when_no_proxy_is_configured(self):
        from contact.views import client_ip
        from django.test import RequestFactory

        request = RequestFactory().get("/", REMOTE_ADDR="192.0.2.9")
        request.META["HTTP_X_FORWARDED_FOR"] = "203.0.113.1"
        self.assertEqual(client_ip(request), "192.0.2.9")

    @override_settings(TRUSTED_PROXY_COUNT=2)
    def test_a_short_chain_falls_back_to_remote_addr(self):
        """A chain shorter than the configured hop count cannot be trusted."""
        from contact.views import client_ip
        from django.test import RequestFactory

        request = RequestFactory().get("/", REMOTE_ADDR="192.0.2.9")
        request.META["HTTP_X_FORWARDED_FOR"] = "203.0.113.1"
        self.assertEqual(client_ip(request), "192.0.2.9")


QUOTE_VALID = {
    "project_title": "Student records system for three campuses",
    "description": (
        "We run three campuses on separate spreadsheets and need one system for "
        "students, results and fees."
    ),
    "budget_range": "1m_5m",
    "timeline": "1_3_months",
    "contact_name": "Adaeze Okoro",
    "email": "adaeze@example.com",
    "phone": "+2348000000000",
    "organisation": "Bright Future Academy",
    "organisation_type": "school",
    "country": "Nigeria",
    "website": "",
}


class QuoteRequestTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_page_renders_with_the_three_steps(self):
        response = self.client.get(reverse("contact:quote"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "What do you need built?")
        self.assertContains(response, "Budget and timeline")
        self.assertContains(response, "Who should we reply to?")
        self.assertContains(response, "csrfmiddlewaretoken")

    def test_valid_request_is_stored(self):
        from .models import QuoteRequest

        response = self.client.post(reverse("contact:quote"), QUOTE_VALID, follow=True)
        self.assertEqual(QuoteRequest.objects.count(), 1)
        quote = QuoteRequest.objects.get()
        self.assertEqual(quote.contact_name, "Adaeze Okoro")
        self.assertEqual(quote.status, QuoteRequest.STATUS_NEW)
        self.assertIsNotNone(quote.ip_address)
        self.assertContains(response, "your request has been received")

    def test_short_description_is_rejected(self):
        from .models import QuoteRequest

        self.client.post(reverse("contact:quote"), {**QUOTE_VALID, "description": "Need app"})
        self.assertEqual(QuoteRequest.objects.count(), 0)

    def test_honeypot_blocks_bots(self):
        from .models import QuoteRequest

        self.client.post(
            reverse("contact:quote"), {**QUOTE_VALID, "website": "http://spam.example"}
        )
        self.assertEqual(QuoteRequest.objects.count(), 0)

    def test_requested_for_falls_back_to_a_general_enquiry(self):
        from .models import QuoteRequest

        self.client.post(reverse("contact:quote"), QUOTE_VALID)
        self.assertEqual(QuoteRequest.objects.get().requested_for, "General enquiry")

    def test_a_solution_can_be_preselected_from_the_query_string(self):
        from company.models import Solution

        solution = Solution.objects.create(
            name="School ERP Platform", tagline="SaaS", summary="Platform."
        )
        response = self.client.get(reverse("contact:quote"), {"solution": solution.slug})
        self.assertEqual(response.context["form"].initial["solution"], solution)

    def test_quote_links_a_selected_solution(self):
        from company.models import Solution

        from .models import QuoteRequest

        solution = Solution.objects.create(
            name="School ERP Platform", tagline="SaaS", summary="Platform."
        )
        self.client.post(reverse("contact:quote"), {**QUOTE_VALID, "solution": solution.pk})
        self.assertEqual(QuoteRequest.objects.get().requested_for, "School ERP Platform")

    @override_settings(CONTACT_RATE_LIMIT=2)
    def test_rate_limit_applies(self):
        from .models import QuoteRequest

        for _ in range(2):
            self.client.post(reverse("contact:quote"), QUOTE_VALID)
        self.assertEqual(QuoteRequest.objects.count(), 2)
        response = self.client.post(reverse("contact:quote"), QUOTE_VALID, follow=True)
        self.assertEqual(QuoteRequest.objects.count(), 2)
        self.assertContains(response, "sent several requests recently")

    @override_settings(CONTACT_NOTIFICATION_EMAIL="owner@example.com")
    def test_notification_email_is_sent_when_configured(self):
        from django.core import mail

        self.client.post(reverse("contact:quote"), QUOTE_VALID)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Student records system", mail.outbox[0].subject)

    def test_csrf_is_enforced(self):
        client = self.client_class(enforce_csrf_checks=True)
        self.assertEqual(
            client.post(reverse("contact:quote"), QUOTE_VALID).status_code, 403
        )


class NewsletterTests(TestCase):
    def test_subscribing_stores_the_address(self):
        from .models import NewsletterSubscriber

        response = self.client.post(
            reverse("contact:newsletter"),
            {"email": "reader@example.com", "source": "footer", "next": "/"},
            follow=True,
        )
        self.assertEqual(NewsletterSubscriber.objects.count(), 1)
        subscriber = NewsletterSubscriber.objects.get()
        self.assertEqual(subscriber.email, "reader@example.com")
        self.assertTrue(subscriber.is_active)
        self.assertContains(response, "You are subscribed")

    def test_resubscribing_does_not_duplicate_or_error(self):
        from .models import NewsletterSubscriber

        for _ in range(2):
            self.client.post(
                reverse("contact:newsletter"), {"email": "reader@example.com", "next": "/"}
            )
        self.assertEqual(NewsletterSubscriber.objects.count(), 1)

    def test_resubscribing_reactivates_an_unsubscribed_address(self):
        from .models import NewsletterSubscriber

        NewsletterSubscriber.objects.create(email="reader@example.com", is_active=False)
        self.client.post(
            reverse("contact:newsletter"), {"email": "reader@example.com", "next": "/"}
        )
        self.assertTrue(NewsletterSubscriber.objects.get().is_active)

    def test_invalid_address_is_rejected(self):
        from .models import NewsletterSubscriber

        response = self.client.post(
            reverse("contact:newsletter"), {"email": "not-an-email", "next": "/"}, follow=True
        )
        self.assertEqual(NewsletterSubscriber.objects.count(), 0)
        self.assertContains(response, "valid email address")

    def test_get_is_not_allowed(self):
        self.assertEqual(self.client.get(reverse("contact:newsletter")).status_code, 405)

    def test_open_redirect_is_refused(self):
        response = self.client.post(
            reverse("contact:newsletter"),
            {"email": "reader@example.com", "next": "https://evil.example/"},
        )
        self.assertEqual(response["Location"], "/")
