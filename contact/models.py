"""Enquiries submitted through the contact form."""
from django.db import models


class ContactMessage(models.Model):
    STATUS_NEW = "new"
    STATUS_READ = "read"
    STATUS_REPLIED = "replied"
    STATUS_SPAM = "spam"
    STATUS_CHOICES = [
        (STATUS_NEW, "New"),
        (STATUS_READ, "Read"),
        (STATUS_REPLIED, "Replied"),
        (STATUS_SPAM, "Spam"),
    ]

    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=40, blank=True)
    company = models.CharField("Company / organisation", max_length=160, blank=True)
    subject = models.CharField(max_length=200)
    message = models.TextField()

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_NEW)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "-created_at"])]

    def __str__(self):
        return f"{self.subject} — {self.name}"

    @property
    def is_read(self):
        return self.status != self.STATUS_NEW


class QuoteRequest(models.Model):
    """
    A structured enquiry from the 'Request a quote' form.

    It captures enough to scope a build without turning into a questionnaire:
    what the organisation is, what they want built, roughly what they can
    spend and when they need it.
    """

    STATUS_NEW = "new"
    STATUS_REVIEWING = "reviewing"
    STATUS_QUOTED = "quoted"
    STATUS_WON = "won"
    STATUS_CLOSED = "closed"
    STATUS_CHOICES = [
        (STATUS_NEW, "New"),
        (STATUS_REVIEWING, "Reviewing"),
        (STATUS_QUOTED, "Quote sent"),
        (STATUS_WON, "Won"),
        (STATUS_CLOSED, "Closed"),
    ]

    BUDGET_CHOICES = [
        ("undecided", "Not decided yet"),
        ("under_1m", "Under ₦1,000,000"),
        ("1m_5m", "₦1,000,000 – ₦5,000,000"),
        ("5m_15m", "₦5,000,000 – ₦15,000,000"),
        ("over_15m", "Above ₦15,000,000"),
    ]

    TIMELINE_CHOICES = [
        ("asap", "As soon as possible"),
        ("1_3_months", "Within 1–3 months"),
        ("3_6_months", "Within 3–6 months"),
        ("exploring", "Still exploring"),
    ]

    ORG_TYPE_CHOICES = [
        ("school", "School or college"),
        ("business", "Business"),
        ("government", "Government or agency"),
        ("ngo", "NGO or non-profit"),
        ("startup", "Startup"),
        ("individual", "Individual"),
        ("other", "Other"),
    ]

    # Step 1 — what they need
    service = models.ForeignKey(
        "services.Service",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quote_requests",
    )
    solution = models.ForeignKey(
        "company.Solution",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quote_requests",
    )
    project_title = models.CharField(max_length=200)
    description = models.TextField()

    # Step 2 — scope
    budget_range = models.CharField(
        max_length=20, choices=BUDGET_CHOICES, default="undecided"
    )
    timeline = models.CharField(
        max_length=20, choices=TIMELINE_CHOICES, default="exploring"
    )
    existing_system = models.BooleanField(
        default=False, help_text="Whether they already run a system this must replace."
    )

    # Step 3 — who they are
    contact_name = models.CharField(max_length=140)
    email = models.EmailField()
    phone = models.CharField(max_length=40, blank=True)
    organisation = models.CharField(max_length=180, blank=True)
    organisation_type = models.CharField(
        max_length=20, choices=ORG_TYPE_CHOICES, default="business"
    )
    country = models.CharField(max_length=120, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_NEW)
    internal_notes = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Quote request"
        indexes = [models.Index(fields=["status", "-created_at"])]

    def __str__(self):
        return f"{self.project_title} — {self.contact_name}"

    @property
    def requested_for(self):
        if self.solution:
            return self.solution.name
        if self.service:
            return self.service.title
        return "General enquiry"


class NewsletterSubscriber(models.Model):
    """An email address that asked for the company's updates."""

    SOURCE_CHOICES = [
        ("footer", "Footer form"),
        ("insights", "Insights page"),
        ("resources", "Resources page"),
        ("admin", "Added by an administrator"),
    ]

    email = models.EmailField(unique=True)
    name = models.CharField(max_length=140, blank=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="footer")
    is_active = models.BooleanField(
        default=True, help_text="Untick instead of deleting when someone unsubscribes."
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.email
