"""Access control and workflow tests for the staff dashboard."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from contact.models import ContactMessage
from proposals.models import Proposal, ProposalTemplate, TemplateItem

from .access import COMPANY_ADMIN_GROUP, sync_company_admin_group

PASSWORD = "Dash-Test-Pass!2026"


def make_user(username, **flags):
    user = get_user_model().objects.create_user(username, f"{username}@example.com", PASSWORD)
    for k, v in flags.items():
        setattr(user, k, v)
    user.save()
    return user


class AccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        group, _ = sync_company_admin_group()
        cls.company_admin = make_user("company", is_staff=True)
        cls.company_admin.groups.add(group)
        cls.visitor = make_user("visitor")
        cls.superuser = make_user("root", is_staff=True, is_superuser=True)

    def test_anonymous_is_sent_to_the_dashboard_login_not_the_admin(self):
        response = self.client.get(reverse("dashboard:home"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("dashboard:login"), response["Location"])
        self.assertNotIn("/admin/", response["Location"])

    def test_signed_in_non_staff_is_refused(self):
        self.client.force_login(self.visitor)
        response = self.client.get(reverse("dashboard:home"))
        self.assertEqual(response.status_code, 403)

    def test_company_admin_has_access_without_being_a_superuser(self):
        self.assertFalse(self.company_admin.is_superuser)
        self.client.force_login(self.company_admin)
        response = self.client.get(reverse("dashboard:home"))
        self.assertEqual(response.status_code, 200)

    def test_superuser_has_access(self):
        self.client.force_login(self.superuser)
        self.assertEqual(self.client.get(reverse("dashboard:home")).status_code, 200)

    def test_login_form_rejects_a_non_staff_account(self):
        """The refusal happens at the form, so the message explains why."""
        response = self.client.post(
            reverse("dashboard:login"),
            {"username": "visitor", "password": PASSWORD},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "does not have dashboard access")

    def test_login_succeeds_for_a_company_admin(self):
        response = self.client.post(
            reverse("dashboard:login"),
            {"username": "company", "password": PASSWORD},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Overview")

    def test_group_holds_commercial_permissions_and_the_company_profile(self):
        """
        A company admin runs the commercial side and owns the company's own
        details — the letterhead is theirs to correct. Editorial content
        (solutions, blog, team) stays out, or the group becomes a superuser
        by another name.
        """
        perms = {
            f"{p.content_type.app_label}.{p.codename}"
            for p in self.company_admin.groups.get(name=COMPANY_ADMIN_GROUP).permissions.all()
        }
        self.assertIn("proposals.add_proposal", perms)
        self.assertIn("contact.view_contactmessage", perms)
        self.assertIn("core.change_sitesettings", perms)
        self.assertNotIn("company.change_solution", perms)
        self.assertNotIn("blog.add_blogpost", perms)
        self.assertNotIn("careers.add_jobopening", perms)

    def test_permission_gate_blocks_a_staff_user_without_the_permission(self):
        bare_staff = make_user("barestaff", is_staff=True)
        self.client.force_login(bare_staff)
        # The overview needs no model permission...
        self.assertEqual(self.client.get(reverse("dashboard:home")).status_code, 200)
        # ...but the proposal list does.
        self.assertEqual(
            self.client.get(reverse("dashboard:proposal_list")).status_code, 403
        )


class ProposalWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        group, _ = sync_company_admin_group()
        cls.user = make_user("seller", is_staff=True)
        cls.user.groups.add(group)
        cls.template = ProposalTemplate.objects.create(
            name="School Management System", slug="sms",
            summary="One system for the school.", default_timeline_weeks=12,
        )
        TemplateItem.objects.create(template=cls.template, title="Discovery",
                                    unit_price=Decimal("450000"), display_order=1)
        TemplateItem.objects.create(template=cls.template, title="Build",
                                    unit_price=Decimal("650000"), display_order=2)

    def setUp(self):
        self.client.force_login(self.user)

    def test_creating_from_a_template_prefills_and_redirects_to_the_editor(self):
        response = self.client.post(reverse("dashboard:proposal_new"), {
            "template": self.template.pk,
            "client_organisation": "Al-Noor School",
            "client_contact_name": "Usman Bello",
            "client_email": "usman@example.com",
            "title": "",
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        proposal = Proposal.objects.get(client_organisation="Al-Noor School")
        self.assertEqual(proposal.items.count(), 2)
        self.assertEqual(proposal.title, "School Management System")
        self.assertEqual(proposal.total, Decimal("1100000.00"))
        self.assertEqual(proposal.prepared_by, self.user)
        self.assertRedirects(
            response, reverse("dashboard:proposal_edit", kwargs={"pk": proposal.pk})
        )

    def test_the_creator_is_recorded(self):
        self.client.post(reverse("dashboard:proposal_new"), {
            "template": self.template.pk, "client_organisation": "X School",
            "client_contact_name": "Head", "client_email": "a@b.com", "title": "",
        })
        self.assertEqual(Proposal.objects.get(client_organisation="X School").prepared_by,
                         self.user)

    def test_status_can_be_changed(self):
        p = Proposal.objects.create(client_organisation="A", client_contact_name="B",
                                    title="T", summary="S")
        response = self.client.post(
            reverse("dashboard:proposal_status", kwargs={"pk": p.pk}),
            {"status": Proposal.STATUS_SENT, "next": reverse("dashboard:proposal_list")},
            follow=True,
        )
        p.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(p.status, Proposal.STATUS_SENT)
        self.assertIsNotNone(p.sent_at)

    def test_an_unknown_status_is_rejected(self):
        p = Proposal.objects.create(client_organisation="A", client_contact_name="B",
                                    title="T", summary="S")
        self.client.post(reverse("dashboard:proposal_status", kwargs={"pk": p.pk}),
                         {"status": "not-a-status"})
        p.refresh_from_db()
        self.assertEqual(p.status, Proposal.STATUS_DRAFT)

    def test_list_filters_by_status_and_search(self):
        Proposal.objects.create(client_organisation="Alpha School", client_contact_name="A",
                                title="T", summary="S", status=Proposal.STATUS_SENT)
        Proposal.objects.create(client_organisation="Beta College", client_contact_name="B",
                                title="T", summary="S", status=Proposal.STATUS_DRAFT)
        r = self.client.get(reverse("dashboard:proposal_list"), {"status": "sent"})
        self.assertContains(r, "Alpha School")
        self.assertNotContains(r, "Beta College")
        r = self.client.get(reverse("dashboard:proposal_list"), {"q": "Beta"})
        self.assertContains(r, "Beta College")
        self.assertNotContains(r, "Alpha School")


class EnquiryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        group, _ = sync_company_admin_group()
        cls.user = make_user("support", is_staff=True)
        cls.user.groups.add(group)

    def setUp(self):
        self.client.force_login(self.user)

    def test_opening_a_new_enquiry_marks_it_read(self):
        e = ContactMessage.objects.create(
            name="A", email="a@b.com", subject="Hello",
            message="A message long enough to be stored.",
        )
        self.assertEqual(e.status, ContactMessage.STATUS_NEW)
        self.client.get(reverse("dashboard:enquiry_detail", kwargs={"pk": e.pk}))
        e.refresh_from_db()
        self.assertEqual(e.status, ContactMessage.STATUS_READ)

    def test_status_can_be_set_from_the_detail_page(self):
        e = ContactMessage.objects.create(
            name="A", email="a@b.com", subject="Hello",
            message="A message long enough to be stored.",
        )
        self.client.post(reverse("dashboard:enquiry_detail", kwargs={"pk": e.pk}),
                         {"status": ContactMessage.STATUS_REPLIED})
        e.refresh_from_db()
        self.assertEqual(e.status, ContactMessage.STATUS_REPLIED)


class CompanyProfileTests(TestCase):
    """The company profile feeds the public site and the proposal letterhead."""

    @classmethod
    def setUpTestData(cls):
        from core.models import SiteSettings

        group, _ = sync_company_admin_group()
        cls.user = make_user("owner", is_staff=True)
        cls.user.groups.add(group)
        cls.site = SiteSettings.objects.create(
            name="Samuel Jeremiah", brand_name="TECHMIARY",
            company_name="Techmiary Technology Concepts",
            legal_name="Techmiary Technology Concepts",
            professional_title="Software Engineer", short_bio="Bio.",
            registration_number="8491604",
            phone="+234 800 000 0000", sales_email="sales@techmiary.tech",
            address="14 Baga Road, Maiduguri",
        )

    def setUp(self):
        self.client.force_login(self.user)

    def payload(self, **overrides):
        data = {
            "company_name": self.site.company_name,
            "legal_name": self.site.legal_name,
            "brand_name": self.site.brand_name,
            "registration_number": self.site.registration_number,
            "founded_year": 2021,
            "tagline": "", "email": "", "sales_email": self.site.sales_email,
            "support_email": "", "phone": self.site.phone, "secondary_phone": "",
            "address": self.site.address, "location": "", "office_hours": "",
            "website_url": "", "linkedin_url": "", "twitter_url": "",
            "github_url": "", "whatsapp_url": "",
        }
        data.update(overrides)
        return data

    def test_page_loads(self):
        response = self.client.get(reverse("dashboard:company_profile"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Company profile")
        # Without this the browser posts filenames, not files.
        self.assertContains(response, 'enctype="multipart/form-data"')

    def test_staff_without_the_permission_is_refused(self):
        bare = make_user("barestaff2", is_staff=True)
        self.client.force_login(bare)
        self.assertEqual(
            self.client.get(reverse("dashboard:company_profile")).status_code, 403
        )

    def test_saving_updates_the_record(self):
        self.client.post(
            reverse("dashboard:company_profile"),
            self.payload(phone="+234 802 111 2222", address="7 Circular Road"),
        )
        self.site.refresh_from_db()
        self.assertEqual(self.site.phone, "+234 802 111 2222")
        self.assertEqual(self.site.address, "7 Circular Road")

    def test_a_registration_prefix_is_stripped(self):
        """Stored bare, so each surface can word the label itself."""
        for entered in ("BN 8491604", "RC-8491604", "No. 8491604", "8491604"):
            self.client.post(
                reverse("dashboard:company_profile"),
                self.payload(registration_number=entered),
            )
            self.site.refresh_from_db()
            self.assertEqual(self.site.registration_number, "8491604", entered)

    def test_an_edit_reaches_the_proposal_pdf_immediately(self):
        """
        The settings record is cached. Both save() and a post_save signal drop
        that cache, so a corrected phone number must not wait for a timeout.
        """
        from decimal import Decimal
        from django.core.cache import cache
        from core.models import SiteSettings
        from proposals.models import Proposal, ProposalItem

        proposal = Proposal.objects.create(
            client_organisation="A School", client_contact_name="Head",
            title="SMS", summary="One system.",
        )
        ProposalItem.objects.create(proposal=proposal, title="Build",
                                    unit_price=Decimal("100000"))

        # Warm the cache the way an ordinary page view would.
        cache.set(SiteSettings.SINGLETON_CACHE_KEY, self.site, 300)

        self.client.post(
            reverse("dashboard:company_profile"),
            self.payload(phone="+234 999 888 7777"),
        )
        response = self.client.get(
            reverse("proposals:pdf", kwargs={"pk": proposal.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")

        # What matters is the rendered document, not the cache internals:
        # rendering repopulates the cache, so asserting it is empty would be
        # asserting the wrong thing. Read the text back out of the PDF.
        import shutil, subprocess, tempfile

        pdf = b"".join(response.streaming_content) if response.streaming else response.content
        if shutil.which("pdftotext"):
            with tempfile.NamedTemporaryFile(suffix=".pdf") as fh:
                fh.write(pdf)
                fh.flush()
                text = subprocess.run(
                    ["pdftotext", fh.name, "-"], capture_output=True, text=True
                ).stdout
            self.assertIn("+234 999 888 7777", text)

        # And the cached copy now holds the new value, not the stale one.
        cached = cache.get(SiteSettings.SINGLETON_CACHE_KEY)
        if cached is not None:
            self.assertEqual(cached.phone, "+234 999 888 7777")
        self.site.refresh_from_db()
        self.assertEqual(self.site.phone, "+234 999 888 7777")

    def test_saving_without_a_file_keeps_the_existing_image(self):
        """
        An empty file input must not clear the logo — otherwise editing a
        phone number would silently wipe the branding.
        """
        import io
        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        buf = io.BytesIO()
        Image.new("RGB", (60, 20), (10, 20, 40)).save(buf, format="PNG")
        self.site.logo.save("brand.png", SimpleUploadedFile(
            "brand.png", buf.getvalue(), content_type="image/png"), save=True)
        original = self.site.logo.name
        self.assertTrue(original)

        self.client.post(reverse("dashboard:company_profile"), self.payload())
        self.site.refresh_from_db()
        self.assertEqual(self.site.logo.name, original)


class FooterTests(TestCase):
    """The staff entry point on the public site."""

    @classmethod
    def setUpTestData(cls):
        from core.models import SiteSettings

        SiteSettings.objects.create(
            name="S", brand_name="TECHMIARY",
            company_name="Techmiary Technology Concepts",
            professional_title="", short_bio="",
            registration_number="8491604",
        )

    def test_visitors_see_a_staff_login_link(self):
        response = self.client.get("/")
        self.assertContains(response, reverse("dashboard:login"))
        self.assertContains(response, "Staff login")

    def test_registration_number_is_shown(self):
        response = self.client.get("/")
        self.assertContains(response, "Business name reg. No. 8491604")

    def test_signed_in_staff_get_a_direct_link_to_the_panel(self):
        staff = make_user("footerstaff", is_staff=True)
        self.client.force_login(staff)
        response = self.client.get("/")
        self.assertContains(response, reverse("dashboard:home"))
        self.assertContains(response, "Control panel")


# ------------------------------------------------------- school quotations ---
from proposals.models import PriceListItem, SchoolQuotation  # noqa: E402


class SchoolQuotationTests(TestCase):
    """The quotation builder: pricing maths, the issue guard, and the PDF."""

    @classmethod
    def setUpTestData(cls):
        group, _ = sync_company_admin_group()
        cls.admin = make_user("quoter", is_staff=True)
        cls.admin.groups.add(group)
        P = PriceListItem
        cls.setup = P.objects.create(name="Setup", billing=P.BILL_ONE_OFF, unit_price=Decimal("500000"),
                                     selected_by_default=True, display_order=1)
        cls.training = P.objects.create(name="Training", billing=P.BILL_ONE_OFF, unit="day",
                                        default_quantity=Decimal("2"), unit_price=Decimal("100000"),
                                        group=P.GROUP_SERVICE, display_order=2)
        cls.licence = P.objects.create(name="Licence", billing=P.BILL_PER_STUDENT_TERM,
                                       unit_price=Decimal("1500"), group=P.GROUP_RECURRING,
                                       selected_by_default=True, display_order=3)
        cls.hosting = P.objects.create(name="Hosting", billing=P.BILL_PER_YEAR,
                                       unit_price=Decimal("300000"), group=P.GROUP_RECURRING,
                                       display_order=4)
        cls.unpriced = P.objects.create(name="Hostel", billing=P.BILL_ONE_OFF, display_order=5)

    def setUp(self):
        self.client.force_login(self.admin)

    def start(self, items, students=400, **extra):
        data = {
            "school_name": "Hillside Academy", "contact_name": "Mrs Okafor",
            "school_type": "combined", "student_count": students, "campus_count": 1,
            "deployment": "online", "items": [i.pk for i in items], **extra,
        }
        response = self.client.post(reverse("dashboard:quotation_new"), data)
        self.assertEqual(response.status_code, 302, getattr(response, "context", None) and response.context["form"].errors)
        return SchoolQuotation.objects.latest("pk")

    def test_company_admin_holds_the_quotation_permissions(self):
        for perm in ["proposals.add_schoolquotation", "proposals.change_schoolquotation",
                     "proposals.change_pricelistitem"]:
            self.assertTrue(self.admin.has_perm(perm), perm)
        self.assertFalse(self.admin.has_perm("proposals.delete_pricelistitem"))

    def test_start_page_pre_ticks_the_default_items(self):
        response = self.client.get(reverse("dashboard:quotation_new"))
        initial = response.context["form"].fields["items"].initial
        self.assertEqual(set(initial), {self.setup.pk, self.licence.pk})

    def test_ticked_items_become_lines_at_todays_prices(self):
        q = self.start([self.setup, self.training, self.licence, self.hosting])
        self.assertRegex(q.reference, r"^TMY-Q-\d{4}-0001$")
        self.assertEqual(q.lines.count(), 4)
        self.assertEqual(q.prepared_by, self.admin)
        # A later price change must not touch a quotation already written.
        PriceListItem.objects.filter(pk=self.setup.pk).update(unit_price=Decimal("999999"))
        self.assertEqual(q.lines.get(title="Setup").unit_price, Decimal("500000"))

    def test_totals_split_one_off_termly_and_yearly(self):
        q = self.start([self.setup, self.training, self.licence, self.hosting],
                       students=400)
        q.discount_percent = Decimal("10")
        q.tax_percent = Decimal("7.5")
        q.deposit_percent = Decimal("60")
        q.save()
        q = SchoolQuotation.objects.prefetch_related("lines").get(pk=q.pk)
        # One-off: 500,000 + 2 days × 100,000 = 700,000; less 10% = 630,000; + 7.5% VAT
        self.assertEqual(q.one_off_subtotal, Decimal("700000.00"))
        self.assertEqual(q.one_off_net, Decimal("630000.00"))
        self.assertEqual(q.one_off_total, Decimal("677250.00"))
        self.assertEqual(q.deposit_amount, Decimal("406350.00"))
        self.assertEqual(q.balance_amount, Decimal("270900.00"))
        # Per term: 400 students × 1,500 = 600,000 + VAT. The discount is setup-only.
        self.assertEqual(q.termly_total, Decimal("645000.00"))
        self.assertEqual(q.yearly_total, Decimal("322500.00"))
        self.assertEqual(q.first_year_total, Decimal("677250.00") + Decimal("645000.00") * 3 + Decimal("322500.00"))
        self.assertEqual(q.per_student_termly_cost, Decimal("1612.50"))

    def test_per_student_lines_follow_the_student_count(self):
        q = self.start([self.licence], students=100)
        q.student_count = 250
        q.save()
        q = SchoolQuotation.objects.prefetch_related("lines").get(pk=q.pk)
        self.assertEqual(q.termly_subtotal, Decimal("375000.00"))
        self.assertEqual(q.lines.get().quantity_label, "250 students")

    def test_unpriced_line_blocks_sending_and_keeps_a_draft(self):
        q = self.start([self.setup, self.unpriced])
        self.assertTrue(q.issue_problems)
        response = self.client.post(
            reverse("dashboard:quotation_status", args=[q.pk]), {"status": "sent"}, follow=True
        )
        self.assertContains(response, "not ready to send")
        q.refresh_from_db()
        self.assertEqual(q.status, "draft")

    def test_fully_priced_quotation_can_be_sent(self):
        q = self.start([self.setup, self.licence])
        self.client.post(reverse("dashboard:quotation_status", args=[q.pk]), {"status": "sent"})
        q.refresh_from_db()
        self.assertEqual(q.status, "sent")
        self.assertIsNotNone(q.sent_at)

    def test_editor_saves_lines_and_adds_a_custom_one(self):
        q = self.start([self.setup])
        line = q.lines.get()
        data = {
            "school_name": q.school_name, "contact_name": q.contact_name,
            "school_type": q.school_type, "student_count": 300, "campus_count": 1,
            "deployment": "hybrid", "status": "draft", "currency": "NGN",
            "discount_percent": "0", "tax_percent": "0", "deposit_percent": "50",
            "delivery_weeks": "6", "valid_until": "2030-01-31", "payment_terms": "Deposit first.",
            "client_notes": "", "internal_notes": "",
            "lines-TOTAL_FORMS": "2", "lines-INITIAL_FORMS": "1",
            "lines-MIN_NUM_FORMS": "0", "lines-MAX_NUM_FORMS": "1000",
            "lines-0-id": line.pk, "lines-0-title": "Setup", "lines-0-description": "",
            "lines-0-billing": "one_off", "lines-0-quantity": "1", "lines-0-unit": "",
            "lines-0-unit_price": "450000", "lines-0-display_order": "1",
            "lines-1-title": "Offline result manager", "lines-1-description": "",
            "lines-1-billing": "one_off", "lines-1-quantity": "2", "lines-1-unit": "installation",
            "lines-1-unit_price": "80000", "lines-1-display_order": "2",
        }
        response = self.client.post(reverse("dashboard:quotation_edit", args=[q.pk]), data)
        self.assertEqual(response.status_code, 302)
        q = SchoolQuotation.objects.prefetch_related("lines").get(pk=q.pk)
        self.assertEqual(q.deployment, "hybrid")
        self.assertEqual(q.one_off_subtotal, Decimal("610000.00"))
        self.assertEqual(q.lines.get(title="Offline result manager").quantity_label, "2 installations")

    def test_duplicate_makes_an_independent_draft(self):
        q = self.start([self.setup, self.licence])
        self.client.post(reverse("dashboard:quotation_duplicate", args=[q.pk]))
        copy = SchoolQuotation.objects.latest("pk")
        self.assertNotEqual(copy.pk, q.pk)
        self.assertNotEqual(copy.reference, q.reference)
        self.assertEqual(copy.lines.count(), 2)
        self.assertEqual(q.lines.count(), 2)

    def test_start_prefills_from_a_website_quote_request(self):
        from contact.models import QuoteRequest
        request = QuoteRequest.objects.create(
            project_title="SMS for our school", description="We need results and fees.",
            contact_name="Mr Bello", email="bello@school.example", organisation="Unity College",
        )
        response = self.client.get(reverse("dashboard:quotation_new") + f"?from_request={request.pk}")
        self.assertEqual(response.context["form"].initial["school_name"], "Unity College")
        q = self.start([self.setup], from_request=request.pk)
        self.assertEqual(q.source_request, request)

    def test_price_list_page_saves_prices(self):
        response = self.client.get(reverse("dashboard:price_list"))
        self.assertEqual(response.status_code, 200)
        formset = response.context["formset"]
        data = {"form-TOTAL_FORMS": str(formset.total_form_count()),
                "form-INITIAL_FORMS": str(formset.initial_form_count()),
                "form-MIN_NUM_FORMS": "0", "form-MAX_NUM_FORMS": "1000"}
        for i, form in enumerate(formset.forms):
            inst = form.instance
            if not inst.pk:
                # The blank "new item" row, posted as a browser would: untouched defaults.
                data.update({f"form-{i}-group": "module", f"form-{i}-billing": "one_off",
                             f"form-{i}-unit_price": "0", f"form-{i}-default_quantity": "1",
                             f"form-{i}-is_active": "on", f"form-{i}-display_order": "0"})
                continue
            price = "250000" if inst.pk == self.unpriced.pk else str(inst.unit_price)
            data.update({
                f"form-{i}-id": inst.pk, f"form-{i}-name": inst.name, f"form-{i}-description": inst.description,
                f"form-{i}-group": inst.group, f"form-{i}-billing": inst.billing, f"form-{i}-unit": inst.unit,
                f"form-{i}-unit_price": price, f"form-{i}-default_quantity": str(inst.default_quantity),
                f"form-{i}-is_active": "on", f"form-{i}-display_order": inst.display_order,
            })
        response = self.client.post(reverse("dashboard:price_list"), data)
        self.assertEqual(response.status_code, 302,
                         response.status_code == 200 and response.context["formset"].errors)
        self.unpriced.refresh_from_db()
        self.assertEqual(self.unpriced.unit_price, Decimal("250000"))

    def test_pdf_renders_with_the_school_and_totals(self):
        from io import BytesIO
        q = self.start([self.setup, self.licence, self.hosting], students=400)
        response = self.client.get(reverse("proposals:quotation_pdf", args=[q.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))
        try:
            from pypdf import PdfReader
        except ImportError:
            return
        text = "".join(p.extract_text() for p in PdfReader(BytesIO(response.content)).pages)
        self.assertIn("Hillside Academy", text)
        self.assertIn(q.reference, text)

    def test_pdf_is_staff_only(self):
        q = self.start([self.setup])
        self.client.logout()
        response = self.client.get(reverse("proposals:quotation_pdf", args=[q.pk]))
        self.assertEqual(response.status_code, 302)
