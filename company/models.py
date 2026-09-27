"""
Corporate content: what the company does, who it serves and who it is.

Every record here is created by an administrator. Nothing in this module
fabricates a client, a metric or an endorsement — models that could imply one
(Client, Testimonial) carry an explicit consent flag so the obligation stays
visible in the admin.
"""
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class OrderedActiveQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)


class Solution(models.Model):
    """
    A productised offering the company sells, e.g. a school ERP platform.

    Solutions differ from Services: a service is work performed, a solution is
    a system the company has built and can deploy.
    """

    name = models.CharField(max_length=140)
    slug = models.SlugField(max_length=160, unique=True, blank=True)
    tagline = models.CharField(
        max_length=200, help_text="One line shown under the name on cards."
    )
    summary = models.TextField(help_text="Two or three sentences for listing pages.")
    overview = models.TextField(blank=True, help_text="Full description on the detail page.")
    who_its_for = models.TextField(
        blank=True, help_text="The kind of organisation this is built for."
    )
    outcome = models.TextField(
        blank=True,
        help_text="What an organisation can do after adopting it. State capabilities, not statistics.",
    )
    icon = models.CharField(
        max_length=40,
        default="layers",
        help_text="Icon key rendered by the template, e.g. cloud, school, api, shield.",
    )
    hero_image = models.ImageField(upload_to="solutions/", blank=True)
    hero_image_alt = models.CharField(max_length=180, blank=True)
    industries = models.ManyToManyField(
        "Industry", related_name="solutions", blank=True
    )
    related_project = models.ForeignKey(
        "projects.Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="solutions",
        help_text="Link the case study for the system this solution is based on.",
    )
    display_order = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(
        default=False, help_text="Featured solutions appear on the homepage."
    )
    is_active = models.BooleanField(default=True)
    meta_title = models.CharField(max_length=70, blank=True)
    meta_description = models.CharField(max_length=180, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = OrderedActiveQuerySet.as_manager()

    class Meta:
        ordering = ["display_order", "name"]
        indexes = [models.Index(fields=["is_active", "display_order"])]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:160]
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("company:solution_detail", kwargs={"slug": self.slug})

    @property
    def resolved_meta_title(self):
        return self.meta_title or f"{self.name} — Solutions"

    @property
    def resolved_meta_description(self):
        return self.meta_description or self.summary[:180]

    @property
    def image_alt(self):
        return self.hero_image_alt or f"{self.name} interface"


class SolutionCapability(models.Model):
    """A capability of a solution, shown as a card on its detail page."""

    solution = models.ForeignKey(
        Solution, on_delete=models.CASCADE, related_name="capabilities"
    )
    title = models.CharField(max_length=140)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=40, default="check")
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "id"]
        verbose_name_plural = "Solution capabilities"

    def __str__(self):
        return f"{self.solution.name}: {self.title}"


class Industry(models.Model):
    """A sector the company builds for."""

    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    tagline = models.CharField(max_length=200, blank=True)
    summary = models.TextField(help_text="What this sector needs from software.")
    overview = models.TextField(blank=True)
    challenges = models.TextField(
        blank=True, help_text="One challenge per line. Rendered as a list."
    )
    icon = models.CharField(max_length=40, default="school")
    image = models.ImageField(upload_to="industries/", blank=True)
    image_alt = models.CharField(max_length=180, blank=True)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    objects = OrderedActiveQuerySet.as_manager()

    class Meta:
        ordering = ["display_order", "name"]
        verbose_name_plural = "Industries"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:140]
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("company:industry_detail", kwargs={"slug": self.slug})

    @property
    def challenge_list(self):
        return [line.strip() for line in self.challenges.splitlines() if line.strip()]


class TeamMember(models.Model):
    """A person in the company. Shown on the leadership and team pages."""

    name = models.CharField(max_length=140)
    slug = models.SlugField(max_length=160, unique=True, blank=True)
    role = models.CharField(max_length=160)
    department = models.CharField(max_length=120, blank=True)
    short_bio = models.CharField(max_length=300, blank=True)
    bio = models.TextField(blank=True)
    photo = models.ImageField(upload_to="team/", blank=True)
    photo_alt = models.CharField(max_length=180, blank=True)
    email = models.EmailField(blank=True)
    linkedin_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    is_leadership = models.BooleanField(
        default=False, help_text="Leadership members appear on the About page."
    )
    is_founder = models.BooleanField(
        default=False,
        help_text="The founder's page also shows the career history from the Experience section.",
    )
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    objects = OrderedActiveQuerySet.as_manager()

    class Meta:
        ordering = ["display_order", "name"]
        indexes = [models.Index(fields=["is_active", "display_order"])]

    def __str__(self):
        return f"{self.name} — {self.role}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:160]
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("company:team_detail", kwargs={"slug": self.slug})

    @property
    def image_alt(self):
        return self.photo_alt or f"Portrait of {self.name}"

    @property
    def initials(self):
        parts = [p for p in self.name.split() if p]
        return "".join(p[0].upper() for p in parts[:2]) or "?"

    @property
    def has_social(self):
        return any([self.linkedin_url, self.github_url, self.twitter_url, self.email])


class CompanyValue(models.Model):
    """A principle the company works by. Used on the About page."""

    title = models.CharField(max_length=140)
    description = models.TextField()
    icon = models.CharField(max_length=40, default="shield")
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    objects = OrderedActiveQuerySet.as_manager()

    class Meta:
        ordering = ["display_order", "title"]

    def __str__(self):
        return self.title


class Milestone(models.Model):
    """A dated event in the company's history."""

    year = models.PositiveIntegerField()
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    objects = OrderedActiveQuerySet.as_manager()

    class Meta:
        ordering = ["year", "display_order"]

    def __str__(self):
        return f"{self.year} — {self.title}"


class Client(models.Model):
    """
    An organisation the company has delivered for.

    ``consent_on_file`` records that they agreed to be named. It does not hide
    the record, so nothing silently disappears, but it is surfaced in the admin
    list so the obligation is never forgotten.
    """

    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    logo = models.ImageField(
        upload_to="clients/",
        blank=True,
        help_text="Leave empty to show the name as a wordmark.",
    )
    logo_alt = models.CharField(max_length=180, blank=True)
    website_url = models.URLField(blank=True)
    industry = models.ForeignKey(
        Industry,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clients",
    )
    engagement = models.CharField(
        max_length=200, blank=True, help_text="One line, e.g. School ERP deployment."
    )
    consent_on_file = models.BooleanField(
        default=False, help_text="Tick once the client has agreed to be named publicly."
    )
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    objects = OrderedActiveQuerySet.as_manager()

    class Meta:
        ordering = ["display_order", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:200]
        super().save(*args, **kwargs)

    @property
    def image_alt(self):
        return self.logo_alt or f"{self.name} logo"


class Testimonial(models.Model):
    """
    A quote from a real, named person who agreed to be quoted.

    There is no seeded example: the section simply does not render until a
    genuine testimonial is entered.
    """

    quote = models.TextField()
    author_name = models.CharField(max_length=140)
    author_role = models.CharField(max_length=160, blank=True)
    organisation = models.CharField(max_length=180, blank=True)
    author_photo = models.ImageField(upload_to="testimonials/", blank=True)
    client = models.ForeignKey(
        Client,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="testimonials",
    )
    consent_on_file = models.BooleanField(
        default=False, help_text="Tick once the person has approved this quote."
    )
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = OrderedActiveQuerySet.as_manager()

    class Meta:
        ordering = ["display_order", "-created_at"]

    def __str__(self):
        return f"{self.author_name} — {self.organisation or 'unattributed'}"

    @property
    def attribution(self):
        parts = [self.author_role, self.organisation]
        return ", ".join(p for p in parts if p)


class ResourceCategory(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.CharField(max_length=255, blank=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "name"]
        verbose_name_plural = "Resource categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:140]
        super().save(*args, **kwargs)


class Resource(models.Model):
    """A downloadable document: a guide, a checklist, a capability statement."""

    KIND_CHOICES = [
        ("guide", "Guide"),
        ("whitepaper", "Whitepaper"),
        ("checklist", "Checklist"),
        ("brochure", "Brochure"),
        ("template", "Template"),
        ("report", "Report"),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    summary = models.TextField(max_length=400)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default="guide")
    category = models.ForeignKey(
        ResourceCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resources",
    )
    file = models.FileField(upload_to="resources/", blank=True)
    external_url = models.URLField(
        blank=True, help_text="Use instead of a file when the resource is hosted elsewhere."
    )
    cover_image = models.ImageField(upload_to="resources/covers/", blank=True)
    pages = models.PositiveIntegerField(null=True, blank=True)
    published_at = models.DateField(null=True, blank=True)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    objects = OrderedActiveQuerySet.as_manager()

    class Meta:
        ordering = ["display_order", "-published_at", "title"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)[:220]
        super().save(*args, **kwargs)

    @property
    def download_url(self):
        if self.file:
            return self.file.url
        return self.external_url or ""

    @property
    def is_available(self):
        return bool(self.download_url)


class FAQCategory(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "name"]
        verbose_name = "FAQ category"
        verbose_name_plural = "FAQ categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:140]
        super().save(*args, **kwargs)


class FAQ(models.Model):
    category = models.ForeignKey(
        FAQCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="faqs",
    )
    question = models.CharField(max_length=255)
    answer = models.TextField()
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    objects = OrderedActiveQuerySet.as_manager()

    class Meta:
        ordering = ["display_order", "id"]
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"

    def __str__(self):
        return self.question
