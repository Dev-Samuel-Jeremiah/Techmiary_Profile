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
