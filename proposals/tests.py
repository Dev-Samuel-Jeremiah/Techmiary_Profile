"""Tests for proposal maths, references, templating and PDF access."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import SiteSettings

from .models import Proposal, ProposalItem, ProposalMilestone, ProposalTemplate, TemplateItem


def make_proposal(**kwargs):
    defaults = dict(
        client_organisation="Bright Future Academy",
        client_contact_name="Amina Yusuf",
        title="School Management System",
        summary="One system for the school.",
    )
    defaults.update(kwargs)
    return Proposal.objects.create(**defaults)


class ReferenceTests(TestCase):
    def test_reference_is_generated_and_sequential(self):
        a = make_proposal()
        b = make_proposal(client_organisation="Second School")
        year = timezone.now().year
        self.assertEqual(a.reference, f"TMY-{year}-0001")
        self.assertEqual(b.reference, f"TMY-{year}-0002")

    def test_deleting_a_proposal_does_not_cause_a_collision(self):
        """
        The sequence comes from the highest existing reference, not a count,
        so removing one cannot make the next save collide.
        """
        a = make_proposal()
        b = make_proposal(client_organisation="Second")
        a.delete()
        c = make_proposal(client_organisation="Third")
        self.assertNotEqual(c.reference, b.reference)
        self.assertEqual(c.reference, f"TMY-{timezone.now().year}-0003")

    def test_an_existing_reference_is_never_overwritten(self):
        p = make_proposal()
        original = p.reference
        p.title = "Changed"
        p.save()
        self.assertEqual(p.reference, original)


class MoneyTests(TestCase):
    def setUp(self):
        self.p = make_proposal(
            discount_percent=Decimal("5"),
            tax_percent=Decimal("7.5"),
            deposit_percent=Decimal("40"),
        )
        ProposalItem.objects.create(proposal=self.p, title="Build", quantity=Decimal("1"),
                                    unit_price=Decimal("1000000"))
        ProposalItem.objects.create(proposal=self.p, title="Training", quantity=Decimal("2"),
                                    unit_price=Decimal("125000"))

    def test_line_total(self):
        training = self.p.items.get(title="Training")
        self.assertEqual(training.line_total, Decimal("250000.00"))

    def test_totals_reconcile(self):
        p = self.p
        self.assertEqual(p.subtotal, Decimal("1250000.00"))
        self.assertEqual(p.discount_amount, Decimal("62500.00"))
        self.assertEqual(p.net_total, Decimal("1187500.00"))
        self.assertEqual(p.tax_amount, Decimal("89062.50"))
        self.assertEqual(p.total, Decimal("1276562.50"))

    def test_deposit_and_balance_sum_to_the_total(self):
        p = self.p
        self.assertEqual(p.deposit_amount + p.balance_amount, p.total)

    def test_no_items_means_zero_not_an_error(self):
        empty = make_proposal(client_organisation="Empty")
        self.assertEqual(empty.subtotal, Decimal("0.00"))
        self.assertEqual(empty.total, Decimal("0.00"))

    def test_amounts_are_decimal_not_float(self):
        """Money must never round through binary floating point."""
        self.assertIsInstance(self.p.total, Decimal)
        self.assertIsInstance(self.p.items.first().line_total, Decimal)


class TemplateTests(TestCase):
    def setUp(self):
        self.tpl = ProposalTemplate.objects.create(
            name="School Management System", slug="sms",
            summary="One system for the school.",
            background="Schools run on spreadsheets.",
            approach="Discovery, build, handover.",
            assumptions="Records supplied\nStaff contact available",
            default_timeline_weeks=12, default_validity_days=30,
        )
        TemplateItem.objects.create(template=self.tpl, title="Discovery",
                                    unit_price=Decimal("450000"), display_order=1)
        TemplateItem.objects.create(template=self.tpl, title="Build",
                                    unit_price=Decimal("650000"), display_order=2)

    def test_applying_a_template_copies_scope_and_items(self):
        p = Proposal.objects.create(
            client_organisation="A School", client_contact_name="Head",
            title="", summary="", template=self.tpl,
        )
        p.apply_template()
        p.refresh_from_db()
        self.assertEqual(p.items.count(), 2)
        self.assertEqual(p.title, "School Management System")
        self.assertEqual(p.background, "Schools run on spreadsheets.")
        self.assertEqual(p.timeline_weeks, 12)
        self.assertIsNotNone(p.valid_until)

    def test_applying_a_template_never_overwrites_existing_wording(self):
        p = Proposal.objects.create(
            client_organisation="A School", client_contact_name="Head",
            title="Bespoke title", summary="Bespoke summary",
            background="Already written", template=self.tpl,
        )
        p.apply_template()
        p.refresh_from_db()
        self.assertEqual(p.title, "Bespoke title")
        self.assertEqual(p.background, "Already written")

    def test_items_are_not_duplicated_on_a_second_apply(self):
        p = Proposal.objects.create(
            client_organisation="A School", client_contact_name="Head",
            title="", summary="", template=self.tpl,
        )
        p.apply_template()
        p.apply_template()
        self.assertEqual(p.items.count(), 2)


class MilestoneTests(TestCase):
    def test_amount_is_a_share_of_the_total(self):
        p = make_proposal()
        ProposalItem.objects.create(proposal=p, title="Build", unit_price=Decimal("1000000"))
        m = ProposalMilestone.objects.create(proposal=p, name="Phase 1",
                                             percent_of_fee=Decimal("25"))
        self.assertEqual(m.amount, Decimal("250000.00"))

    def test_week_label(self):
        p = make_proposal()
        single = ProposalMilestone.objects.create(proposal=p, name="A", week_from=3, week_to=3)
        span = ProposalMilestone.objects.create(proposal=p, name="B", week_from=3, week_to=6)
        self.assertEqual(single.week_label, "Week 3")
        self.assertEqual(span.week_label, "Weeks 3–6")


class PdfAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        SiteSettings.objects.create(
            name="Samuel Jeremiah", brand_name="TECHMIARY",
            company_name="Techmiary Technology Concepts",
            professional_title="Software Engineer", short_bio="Bio.",
        )
        cls.staff = get_user_model().objects.create_user(
            "staffer", "staff@example.com", "pw-for-tests", is_staff=True, is_superuser=True
        )
        cls.other = get_user_model().objects.create_user(
            "visitor", "visitor@example.com", "pw-for-tests"
        )
        cls.proposal = make_proposal()
        ProposalItem.objects.create(proposal=cls.proposal, title="Build",
                                    unit_price=Decimal("500000"))

    def url(self):
        return reverse("proposals:pdf", kwargs={"pk": self.proposal.pk})

    def test_anonymous_is_redirected_to_login(self):
        """A proposal holds client contact details and pricing — never public."""
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 302)
        self.assertNotEqual(response.get("Content-Type"), "application/pdf")

    def test_non_staff_is_refused(self):
        self.client.force_login(self.other)
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 302)

    def test_staff_gets_a_pdf(self):
        self.client.force_login(self.staff)
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        content = b"".join(response.streaming_content) if response.streaming else response.content
        self.assertTrue(content.startswith(b"%PDF-"))
        self.assertGreater(len(content), 1000)

    def test_filename_carries_the_reference_and_client(self):
        self.client.force_login(self.staff)
        response = self.client.get(self.url())
        disposition = response["Content-Disposition"]
        self.assertIn(self.proposal.reference, disposition)
        self.assertIn("bright-future-academy", disposition)

    def test_missing_proposal_is_404(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("proposals:pdf", kwargs={"pk": 999999}))
        self.assertEqual(response.status_code, 404)
