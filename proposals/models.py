"""
Client proposals, written in the admin and issued as a PDF on letterhead.

The commercial figures are stored as entered and the totals are derived, so a
proposal always adds up: nothing is typed twice. Money is held in Decimal —
never float — because these are amounts a client will be invoiced against.
"""
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone

TWO_PLACES = Decimal("0.01")


def money(value):
    """Round half-up to two places, the convention people expect on an invoice."""
    return Decimal(value or 0).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


class ProposalTemplate(models.Model):
    """
    A reusable starting point, e.g. "School Management System".

    Selecting one on a new proposal copies its scope and line items across, so
    a standard engagement is a few edits rather than a blank page.
    """

    name = models.CharField(max_length=140, unique=True)
    slug = models.SlugField(max_length=160, unique=True)
    solution = models.ForeignKey(
        "company.Solution",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="proposal_templates",
        help_text="Links the proposal to a solution on the website, if it matches one.",
    )
    summary = models.CharField(
        max_length=300, help_text="One line describing what this engagement delivers."
    )
    background = models.TextField(
        blank=True,
        help_text="The situation this kind of client is usually in. Edited per proposal.",
    )
    approach = models.TextField(
        blank=True, help_text="How the work is run. One paragraph per phase."
    )
    assumptions = models.TextField(blank=True, help_text="One per line.")
    exclusions = models.TextField(blank=True, help_text="One per line.")
    payment_terms = models.TextField(blank=True)
    default_timeline_weeks = models.PositiveIntegerField(default=8)
    default_validity_days = models.PositiveIntegerField(
        default=30, help_text="How long a proposal from this template stays open."
    )
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "name"]
        verbose_name = "Proposal template"
        verbose_name_plural = "Proposal templates"

    def __str__(self):
        return self.name


class TemplateItem(models.Model):
    """A default line item copied onto proposals built from the template."""

    template = models.ForeignKey(
        ProposalTemplate, on_delete=models.CASCADE, related_name="items"
    )
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    quantity = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("1"))
    unit = models.CharField(max_length=40, blank=True, help_text="e.g. module, day, licence.")
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "id"]
        verbose_name = "Template line item"
        verbose_name_plural = "Template line items"

    def __str__(self):
        return self.title


class Proposal(models.Model):
    """One proposal for one prospective client."""

    STATUS_DRAFT = "draft"
    STATUS_SENT = "sent"
    STATUS_ACCEPTED = "accepted"
    STATUS_DECLINED = "declined"
    STATUS_EXPIRED = "expired"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_SENT, "Sent"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_DECLINED, "Declined"),
        (STATUS_EXPIRED, "Expired"),
    ]

    CURRENCY_CHOICES = [
        ("NGN", "Naira (₦)"),
        ("USD", "US Dollar ($)"),
        ("GBP", "Pound (£)"),
        ("EUR", "Euro (€)"),
    ]
    CURRENCY_SYMBOLS = {"NGN": "₦", "USD": "$", "GBP": "£", "EUR": "€"}

    reference = models.CharField(
        max_length=32,
        unique=True,
        blank=True,
        help_text="Generated on first save, e.g. TMY-2026-0007.",
    )
    template = models.ForeignKey(
        ProposalTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="proposals",
        help_text="Pick one to prefill the scope and line items, then edit freely.",
    )

    # -- Client ----------------------------------------------------------
    client_organisation = models.CharField(max_length=200)
    client_contact_name = models.CharField(max_length=160)
    client_role = models.CharField(
        max_length=120, blank=True, help_text="e.g. Proprietor, Head Teacher, IT Manager."
    )
    client_email = models.EmailField(blank=True)
    client_phone = models.CharField(max_length=40, blank=True)
    client_address = models.TextField(blank=True)

    # -- The engagement ---------------------------------------------------
    title = models.CharField(max_length=200, help_text="e.g. School Management System.")
    summary = models.CharField(max_length=300, help_text="One line, shown under the title.")
    background = models.TextField(blank=True, help_text="The client's current situation.")
    approach = models.TextField(blank=True, help_text="How the work will be run.")
    assumptions = models.TextField(blank=True, help_text="One per line.")
    exclusions = models.TextField(blank=True, help_text="One per line. What is not included.")

    # -- Commercials ------------------------------------------------------
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default="NGN")
    discount_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
    )
    tax_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
        help_text="VAT or equivalent. Leave at 0 if not applicable.",
    )
    deposit_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("50"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
        help_text="Percentage payable to begin work.",
    )
    payment_terms = models.TextField(blank=True)

    timeline_weeks = models.PositiveIntegerField(
        default=8, help_text="Estimated delivery time from kick-off."
    )
    start_estimate = models.CharField(
        max_length=120, blank=True, help_text="e.g. Within two weeks of acceptance."
    )
    valid_until = models.DateField(
        null=True, blank=True, help_text="Blank means the proposal does not expire."
    )

    notes = models.TextField(
        blank=True, help_text="Internal only. Never appears in the PDF."
    )

    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    prepared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="proposals",
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["reference"]),
        ]

    def __str__(self):
        return f"{self.reference or 'Draft'} — {self.client_organisation}"

    # -- Reference ---------------------------------------------------------
    def _next_reference(self):
        """
        TMY-<year>-<sequence>. The sequence restarts each year and is derived
        from the highest existing reference for that year, so deleting a
        proposal never causes a collision.
        """
        year = timezone.now().year
        prefix = f"TMY-{year}-"
        last = (
            Proposal.objects.filter(reference__startswith=prefix)
            .order_by("-reference")
            .values_list("reference", flat=True)
            .first()
        )
        seq = 1
        if last:
            try:
                seq = int(last.rsplit("-", 1)[1]) + 1
            except (IndexError, ValueError):
                seq = Proposal.objects.filter(reference__startswith=prefix).count() + 1
        return f"{prefix}{seq:04d}"

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = self._next_reference()
        if self.status == self.STATUS_SENT and self.sent_at is None:
            self.sent_at = timezone.now()
        super().save(*args, **kwargs)

    # -- Money -------------------------------------------------------------
    @property
    def currency_symbol(self):
        return self.CURRENCY_SYMBOLS.get(self.currency, "")

    @property
    def subtotal(self):
        return money(sum((i.line_total for i in self.items.all()), Decimal("0")))

    @property
    def discount_amount(self):
        return money(self.subtotal * (self.discount_percent or 0) / 100)

    @property
    def net_total(self):
        return money(self.subtotal - self.discount_amount)

    @property
    def tax_amount(self):
        return money(self.net_total * (self.tax_percent or 0) / 100)

    @property
    def total(self):
        return money(self.net_total + self.tax_amount)

    @property
    def deposit_amount(self):
        return money(self.total * (self.deposit_percent or 0) / 100)

    @property
    def balance_amount(self):
        return money(self.total - self.deposit_amount)

    # -- State -------------------------------------------------------------
    @property
    def is_expired(self):
        return bool(self.valid_until and self.valid_until < timezone.localdate())

    @property
    def assumption_list(self):
        return [l.strip() for l in self.assumptions.splitlines() if l.strip()]

    @property
    def exclusion_list(self):
        return [l.strip() for l in self.exclusions.splitlines() if l.strip()]

    def get_pdf_url(self):
        return reverse("proposals:pdf", kwargs={"pk": self.pk})

    def apply_template(self, template=None):
        """
        Copy a template's scope and line items onto this proposal.

        Only blank fields are filled, so applying a template never discards
        something already written. Line items are copied only when there are
        none, for the same reason.
        """
        template = template or self.template
        if template is None:
            return False

        for field in ("summary", "background", "approach", "assumptions",
                      "exclusions", "payment_terms"):
            if not getattr(self, field):
                setattr(self, field, getattr(template, field, "") or "")
        if not self.title:
            self.title = template.name
        if self.timeline_weeks in (None, 0, 8):
            self.timeline_weeks = template.default_timeline_weeks
        if self.valid_until is None and template.default_validity_days:
            self.valid_until = timezone.localdate() + timezone.timedelta(
                days=template.default_validity_days
            )
        self.save()

        if not self.items.exists():
            ProposalItem.objects.bulk_create([
                ProposalItem(
                    proposal=self,
                    title=t.title,
                    description=t.description,
                    quantity=t.quantity,
                    unit=t.unit,
                    unit_price=t.unit_price,
                    display_order=t.display_order,
                )
                for t in template.items.all()
            ])
        return True


class ProposalItem(models.Model):
    """One priced line on a proposal."""

    proposal = models.ForeignKey(Proposal, on_delete=models.CASCADE, related_name="items")
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    quantity = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("1"))
    unit = models.CharField(max_length=40, blank=True)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "id"]
        verbose_name = "Line item"
        verbose_name_plural = "Line items"

    def __str__(self):
        return self.title

    @property
    def line_total(self):
        return money((self.quantity or 0) * (self.unit_price or 0))


class ProposalMilestone(models.Model):
    """A delivery phase, optionally tied to a share of the fee."""

    proposal = models.ForeignKey(
        Proposal, on_delete=models.CASCADE, related_name="milestones"
    )
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    week_from = models.PositiveIntegerField(default=1)
    week_to = models.PositiveIntegerField(default=1)
    percent_of_fee = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
        help_text="Leave at 0 if this phase is not a payment point.",
    )
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "week_from", "id"]

    def __str__(self):
        return self.name

    @property
    def week_label(self):
        if self.week_from == self.week_to:
            return f"Week {self.week_from}"
        return f"Weeks {self.week_from}–{self.week_to}"

    @property
    def amount(self):
        return money(self.proposal.total * (self.percent_of_fee or 0) / 100)


# ==========================================================================
# School quotations
# ==========================================================================
# A quotation is the short, priced document a school approves and pays
# against — distinct from a proposal, which argues the case in prose. It is
# built from a price list the company maintains, and copies each price onto
# the quotation when a line is added, so changing the price list later never
# alters a quotation that has already been sent.

TERMS_PER_YEAR = 3  # Nigerian schools run three terms in a session.


class PriceListItem(models.Model):
    """One thing the company sells to schools, at its current price."""

    GROUP_MODULE = "module"
    GROUP_SERVICE = "service"
    GROUP_RECURRING = "recurring"
    GROUP_CHOICES = [
        (GROUP_MODULE, "System modules"),
        (GROUP_SERVICE, "Delivery & add-ons"),
        (GROUP_RECURRING, "Licence, hosting & support"),
    ]

    BILL_ONE_OFF = "one_off"
    BILL_PER_STUDENT_TERM = "per_student_term"
    BILL_PER_TERM = "per_term"
    BILL_PER_YEAR = "per_year"
    BILLING_CHOICES = [
        (BILL_ONE_OFF, "One-off"),
        (BILL_PER_STUDENT_TERM, "Per student, per term"),
        (BILL_PER_TERM, "Per term"),
        (BILL_PER_YEAR, "Per year"),
    ]

    name = models.CharField(max_length=160, unique=True)
    description = models.TextField(blank=True, help_text="Shown under the line on the quotation.")
    group = models.CharField(max_length=12, choices=GROUP_CHOICES, default=GROUP_MODULE)
    billing = models.CharField(max_length=20, choices=BILLING_CHOICES, default=BILL_ONE_OFF)
    unit = models.CharField(
        max_length=40, blank=True,
        help_text="e.g. module, day, installation. Not needed for per-student lines.",
    )
    unit_price = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    default_quantity = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal("1"),
        help_text="Ignored for per-student lines, which use the school's student count.",
    )
    selected_by_default = models.BooleanField(
        default=False, help_text="Pre-ticked when a new quotation is started.",
    )
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["group", "display_order", "name"]
        verbose_name = "Price list item"
        verbose_name_plural = "Price list"

    def __str__(self):
        return self.name

    @property
    def is_priced(self):
        return (self.unit_price or 0) > 0


class SchoolQuotation(models.Model):
    """A priced quotation for one school."""

    STATUS_DRAFT = "draft"
    STATUS_SENT = "sent"
    STATUS_ACCEPTED = "accepted"
    STATUS_DECLINED = "declined"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_SENT, "Sent"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_DECLINED, "Declined"),
    ]

    SCHOOL_TYPE_CHOICES = [
        ("nursery_primary", "Nursery & primary"),
        ("secondary", "Secondary"),
        ("combined", "Nursery, primary & secondary"),
        ("tertiary", "College / training institute"),
    ]

    DEPLOY_ONLINE = "online"
    DEPLOY_OFFLINE = "offline"
    DEPLOY_HYBRID = "hybrid"
    DEPLOYMENT_CHOICES = [
        (DEPLOY_ONLINE, "Online — hosted and maintained by us"),
        (DEPLOY_OFFLINE, "Offline — installed on the school's computers"),
        (DEPLOY_HYBRID, "Online and offline"),
    ]

    reference = models.CharField(
        max_length=32, unique=True, blank=True,
        help_text="Generated on first save, e.g. TMY-Q-2026-0003.",
    )
    source_request = models.ForeignKey(
        "contact.QuoteRequest", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="school_quotations",
        help_text="The website quote request this was raised from, if any.",
    )

    # -- The school -------------------------------------------------------
    school_name = models.CharField(max_length=200)
    contact_name = models.CharField(max_length=160)
    contact_role = models.CharField(
        max_length=120, blank=True, help_text="e.g. Proprietor, Principal, Bursar."
    )
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=40, blank=True)
    school_address = models.TextField(blank=True)
    school_type = models.CharField(max_length=20, choices=SCHOOL_TYPE_CHOICES, default="combined")
    student_count = models.PositiveIntegerField(
        default=0, help_text="Used to price every per-student line."
    )
    campus_count = models.PositiveIntegerField(default=1)
    deployment = models.CharField(max_length=10, choices=DEPLOYMENT_CHOICES, default=DEPLOY_ONLINE)

    # -- Commercials ------------------------------------------------------
    currency = models.CharField(max_length=3, choices=Proposal.CURRENCY_CHOICES, default="NGN")
    discount_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
        help_text="Applied to the one-off setup cost only.",
    )
    tax_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
        help_text="VAT, applied to every amount. Nigerian VAT is 7.5%; leave 0 if not charged.",
    )
    deposit_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("60"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
        help_text="Share of the one-off cost payable to begin work.",
    )
    delivery_weeks = models.PositiveIntegerField(default=6, help_text="From payment of the deposit.")
    valid_until = models.DateField(null=True, blank=True)
    payment_terms = models.TextField(blank=True)
    client_notes = models.TextField(
        blank=True, help_text="Printed on the quotation, under the prices."
    )
    internal_notes = models.TextField(blank=True, help_text="Internal only. Never printed.")

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    prepared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="school_quotations",
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    DEFAULT_PAYMENT_TERMS = (
        "The deposit is payable on acceptance and schedules the work. The balance of "
        "the one-off cost is due on handover, before the system goes live.\n"
        "Termly licence fees are invoiced at the start of each term. Yearly hosting and "
        "support is invoiced in advance at the start of each session.\n"
        "SMS credit and payment-gateway charges are billed at cost."
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "School quotation"
        verbose_name_plural = "School quotations"
        indexes = [models.Index(fields=["status", "-created_at"])]

    def __str__(self):
        return f"{self.reference or 'Draft'} — {self.school_name}"

    def _next_reference(self):
        """TMY-Q-<year>-<sequence>, restarting each year, collision-free after deletes."""
        prefix = f"TMY-Q-{timezone.now().year}-"
        last = (
            SchoolQuotation.objects.filter(reference__startswith=prefix)
            .order_by("-reference").values_list("reference", flat=True).first()
        )
        seq = 1
        if last:
            try:
                seq = int(last.rsplit("-", 1)[1]) + 1
            except (IndexError, ValueError):
                seq = SchoolQuotation.objects.filter(reference__startswith=prefix).count() + 1
        return f"{prefix}{seq:04d}"

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = self._next_reference()
        if self.valid_until is None:
            self.valid_until = timezone.localdate() + timezone.timedelta(days=30)
        if not self.payment_terms:
            self.payment_terms = self.DEFAULT_PAYMENT_TERMS
        if self.status == self.STATUS_SENT and self.sent_at is None:
            self.sent_at = timezone.now()
        super().save(*args, **kwargs)

    def add_price_items(self, items):
        """Copy price-list items onto this quotation at today's prices."""
        start = (self.lines.aggregate(m=models.Max("display_order"))["m"] or 0) + 1
        SchoolQuotationLine.objects.bulk_create([
            SchoolQuotationLine(
                quotation=self, price_item=item, title=item.name,
                description=item.description, billing=item.billing,
                quantity=item.default_quantity, unit=item.unit,
                unit_price=item.unit_price, display_order=start + i,
            )
            for i, item in enumerate(items)
        ])

    # -- Money ------------------------------------------------------------
    @property
    def currency_symbol(self):
        return Proposal.CURRENCY_SYMBOLS.get(self.currency, "")

    @staticmethod
    def _pct(value):
        """7.50 -> '7.5', 60.00 -> '60' — percentages as people write them."""
        text = f"{Decimal(value or 0):f}"
        return text.rstrip("0").rstrip(".") if "." in text else text

    @property
    def discount_label(self):
        return self._pct(self.discount_percent)

    @property
    def tax_label(self):
        return self._pct(self.tax_percent)

    @property
    def deposit_label(self):
        return self._pct(self.deposit_percent)

    def _lines(self, *billings):
        return [l for l in self.lines.all() if l.billing in billings]

    @property
    def one_off_lines(self):
        return self._lines(PriceListItem.BILL_ONE_OFF)

    @property
    def termly_lines(self):
        return self._lines(PriceListItem.BILL_PER_STUDENT_TERM, PriceListItem.BILL_PER_TERM)

    @property
    def yearly_lines(self):
        return self._lines(PriceListItem.BILL_PER_YEAR)

    def _tax(self, amount):
        return money(amount * (self.tax_percent or 0) / 100)

    @property
    def one_off_subtotal(self):
        return money(sum((l.line_total for l in self.one_off_lines), Decimal("0")))

    @property
    def discount_amount(self):
        return money(self.one_off_subtotal * (self.discount_percent or 0) / 100)

    @property
    def one_off_net(self):
        return money(self.one_off_subtotal - self.discount_amount)

    @property
    def one_off_tax(self):
        return self._tax(self.one_off_net)

    @property
    def one_off_total(self):
        return money(self.one_off_net + self.one_off_tax)

    @property
    def termly_subtotal(self):
        return money(sum((l.line_total for l in self.termly_lines), Decimal("0")))

    @property
    def termly_total(self):
        return money(self.termly_subtotal + self._tax(self.termly_subtotal))

    @property
    def yearly_subtotal(self):
        return money(sum((l.line_total for l in self.yearly_lines), Decimal("0")))

    @property
    def yearly_total(self):
        return money(self.yearly_subtotal + self._tax(self.yearly_subtotal))

    @property
    def first_year_total(self):
        """Everything the school pays in its first session."""
        return money(self.one_off_total + self.termly_total * TERMS_PER_YEAR + self.yearly_total)

    @property
    def deposit_amount(self):
        return money(self.one_off_total * (self.deposit_percent or 0) / 100)

    @property
    def balance_amount(self):
        return money(self.one_off_total - self.deposit_amount)

    @property
    def per_student_termly_cost(self):
        if not self.student_count:
            return Decimal("0")
        return money(self.termly_total / self.student_count)

    # -- State ------------------------------------------------------------
    @property
    def unpriced_lines(self):
        return [l for l in self.lines.all() if not (l.unit_price or 0) > 0]

    @property
    def needs_student_count(self):
        return not self.student_count and any(
            l.is_per_student for l in self.lines.all()
        )

    @property
    def issue_problems(self):
        """Reasons this quotation should not go to a school yet."""
        problems = []
        if not self.lines.exists():
            problems.append("It has no lines.")
        unpriced = self.unpriced_lines
        if unpriced:
            names = ", ".join(l.title for l in unpriced[:4])
            more = f" and {len(unpriced) - 4} more" if len(unpriced) > 4 else ""
            problems.append(f"These lines have no price: {names}{more}.")
        if self.needs_student_count:
            problems.append("Per-student lines need the school's student count.")
        return problems

    @property
    def is_expired(self):
        return bool(self.valid_until and self.valid_until < timezone.localdate())

    def get_pdf_url(self):
        return reverse("proposals:quotation_pdf", kwargs={"pk": self.pk})


class SchoolQuotationLine(models.Model):
    """One priced line on a school quotation."""

    quotation = models.ForeignKey(
        SchoolQuotation, on_delete=models.CASCADE, related_name="lines"
    )
    price_item = models.ForeignKey(
        PriceListItem, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="quotation_lines",
    )
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    billing = models.CharField(
        max_length=20, choices=PriceListItem.BILLING_CHOICES, default=PriceListItem.BILL_ONE_OFF
    )
    quantity = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal("1"),
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Ignored for per-student lines.",
    )
    unit = models.CharField(max_length=40, blank=True)
    unit_price = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "id"]
        verbose_name = "Quotation line"
        verbose_name_plural = "Quotation lines"

    def __str__(self):
        return self.title

    @property
    def is_per_student(self):
        return self.billing == PriceListItem.BILL_PER_STUDENT_TERM

    @property
    def effective_quantity(self):
        """Per-student lines follow the school's student count automatically."""
        if self.is_per_student:
            return Decimal(self.quotation.student_count or 0)
        return self.quantity or Decimal("0")

    @property
    def quantity_label(self):
        qty = self.effective_quantity
        shown = f"{qty:,.0f}" if qty == qty.to_integral() else f"{qty:,.2f}"
        if self.is_per_student:
            return f"{shown} student{'s' if qty != 1 else ''}"
        if self.unit:
            return f"{shown} {self.unit}{'s' if qty != 1 and not self.unit.endswith('s') else ''}"
        return shown

    @property
    def line_total(self):
        return money(self.effective_quantity * (self.unit_price or 0))
