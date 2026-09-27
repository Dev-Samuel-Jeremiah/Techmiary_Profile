"""Job openings and the applications submitted against them."""
from django.core.validators import FileExtensionValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


class Department(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.CharField(max_length=255, blank=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:140]
        super().save(*args, **kwargs)


class OpenJobManager(models.Manager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(is_published=True, status=JobOpening.STATUS_OPEN)
            .select_related("department")
        )


class JobOpening(models.Model):
    STATUS_OPEN = "open"
    STATUS_CLOSED = "closed"
    STATUS_DRAFT = "draft"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_OPEN, "Open"),
        (STATUS_CLOSED, "Closed"),
    ]

    EMPLOYMENT_CHOICES = [
        ("full_time", "Full time"),
        ("part_time", "Part time"),
        ("contract", "Contract"),
        ("internship", "Internship"),
    ]

    LOCATION_CHOICES = [
        ("onsite", "On site"),
        ("hybrid", "Hybrid"),
        ("remote", "Remote"),
    ]

    EXPERIENCE_CHOICES = [
        ("entry", "Entry level"),
        ("mid", "Mid level"),
        ("senior", "Senior"),
        ("lead", "Lead"),
    ]

    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name="openings"
    )
    summary = models.TextField(max_length=400, help_text="Shown on the careers listing.")
    description = models.TextField(help_text="What the role involves.")
    responsibilities = models.TextField(
        blank=True, help_text="One responsibility per line."
    )
    requirements = models.TextField(blank=True, help_text="One requirement per line.")
    nice_to_have = models.TextField(blank=True, help_text="One item per line.")
    benefits = models.TextField(blank=True, help_text="One benefit per line.")

    location = models.CharField(max_length=160, blank=True)
    location_type = models.CharField(
        max_length=20, choices=LOCATION_CHOICES, default="onsite"
    )
    employment_type = models.CharField(
        max_length=20, choices=EMPLOYMENT_CHOICES, default="full_time"
    )
    experience_level = models.CharField(
        max_length=20, choices=EXPERIENCE_CHOICES, default="mid"
    )
    # Salary is deliberately free text and optional: no range is implied
    # unless someone types one in.
    salary_range = models.CharField(
        max_length=140, blank=True, help_text="Optional. Leave blank to show nothing."
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    is_published = models.BooleanField(default=False)
    posted_at = models.DateField(null=True, blank=True)
    closes_at = models.DateField(null=True, blank=True)
    display_order = models.PositiveIntegerField(default=0)

    meta_title = models.CharField(max_length=70, blank=True)
    meta_description = models.CharField(max_length=180, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()
    open_roles = OpenJobManager()

    class Meta:
        ordering = ["display_order", "-posted_at", "title"]
        indexes = [
            models.Index(fields=["is_published", "status"]),
            models.Index(fields=["slug"]),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)[:200]
        if self.is_published and self.posted_at is None:
            self.posted_at = timezone.localdate()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("careers:detail", kwargs={"slug": self.slug})

    def _lines(self, value):
        return [line.strip() for line in value.splitlines() if line.strip()]

    @property
    def responsibility_list(self):
        return self._lines(self.responsibilities)

    @property
    def requirement_list(self):
        return self._lines(self.requirements)

    @property
    def nice_to_have_list(self):
        return self._lines(self.nice_to_have)

    @property
    def benefit_list(self):
        return self._lines(self.benefits)

    @property
    def is_accepting_applications(self):
        if self.status != self.STATUS_OPEN or not self.is_published:
            return False
        if self.closes_at and self.closes_at < timezone.localdate():
            return False
        return True

    @property
    def resolved_meta_title(self):
        return self.meta_title or f"{self.title} — Careers"

    @property
    def resolved_meta_description(self):
        return self.meta_description or self.summary[:180]


class JobApplication(models.Model):
    STATUS_NEW = "new"
    STATUS_REVIEWING = "reviewing"
    STATUS_SHORTLISTED = "shortlisted"
    STATUS_REJECTED = "rejected"
    STATUS_HIRED = "hired"
    STATUS_CHOICES = [
        (STATUS_NEW, "New"),
        (STATUS_REVIEWING, "Reviewing"),
        (STATUS_SHORTLISTED, "Shortlisted"),
        (STATUS_REJECTED, "Not proceeding"),
        (STATUS_HIRED, "Hired"),
    ]

    job = models.ForeignKey(
        JobOpening, on_delete=models.CASCADE, related_name="applications"
    )
    full_name = models.CharField(max_length=140)
    email = models.EmailField()
    phone = models.CharField(max_length=40, blank=True)
    location = models.CharField(max_length=160, blank=True)
    portfolio_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    cover_letter = models.TextField(blank=True)
    cv = models.FileField(
        upload_to="careers/applications/",
        validators=[FileExtensionValidator(["pdf", "doc", "docx", "odt", "rtf"])],
        help_text="PDF or Word document.",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_NEW)
    notes = models.TextField(blank=True, help_text="Internal notes. Never shown publicly.")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "-created_at"])]

    def __str__(self):
        return f"{self.full_name} — {self.job.title}"
