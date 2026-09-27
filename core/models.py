"""Site-wide configuration, social links and the skills taxonomy."""
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify


class TimeStampedModel(models.Model):
    """Adds created/updated bookkeeping to any model that inherits it."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SiteSettings(models.Model):
    """
    Singleton holding every piece of identity/branding copy used by templates.

    Nothing about the site owner is hard-coded in templates: everything comes
    from this record so it can be edited from the Django admin.
    """

    SINGLETON_CACHE_KEY = "core:site-settings"

    name = models.CharField(max_length=120, help_text="Full name of the site owner.")
    brand_name = models.CharField(
        max_length=80, help_text="Brand shown in the navigation bar, e.g. TECHMIARY."
    )
    company_name = models.CharField(
        max_length=160,
        blank=True,
        help_text="Registered company or trading name, e.g. Techmiary Technology Concepts.",
    )
    professional_title = models.CharField(
        max_length=160, help_text="Primary positioning line, e.g. Software Engineer & Product Builder."
    )
    tagline = models.CharField(
        max_length=255,
        blank=True,
        help_text="Secondary positioning line shown under the title.",
    )
    short_bio = models.TextField(
        help_text="One or two sentences used in the hero and meta description."
    )
    long_bio = models.TextField(blank=True, help_text="Full biography for the About page.")

    profile_image = models.ImageField(upload_to="site/", blank=True)
    og_image = models.ImageField(
        upload_to="site/",
        blank=True,
        help_text="1200x630 image used for link previews.",
    )
    logo = models.ImageField(upload_to="site/", blank=True)
    favicon = models.ImageField(upload_to="site/", blank=True)

    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    location = models.CharField(max_length=160, blank=True)
    show_email_publicly = models.BooleanField(
        default=False,
        help_text="Leave off to keep the address out of the page source; the contact form still reaches it.",
    )

    github_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    whatsapp_url = models.URLField(blank=True)
    website_url = models.URLField(blank=True, help_text="Primary company website.")

    resume_file = models.FileField(upload_to="resume/", blank=True)

    # --- Company profile -------------------------------------------------
    # The site is a company website; these fields carry the corporate copy so
    # no template hard-codes a claim about the organisation.
    legal_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Registered name, if different from the trading name.",
    )
    founded_year = models.PositiveIntegerField(
        null=True, blank=True, help_text="Year the company started operating."
    )
    hero_headline = models.CharField(
        max_length=160,
        blank=True,
        help_text="Main homepage headline. Falls back to the positioning line.",
    )
    hero_subheadline = models.TextField(
        blank=True, help_text="Paragraph under the homepage headline."
    )
    company_overview = models.TextField(
        blank=True, help_text="What the company does. Used on the About page."
    )
    mission = models.TextField(blank=True)
    vision = models.TextField(blank=True)
    address = models.TextField(blank=True, help_text="Full postal address.")
    office_hours = models.CharField(
        max_length=160, blank=True, help_text="e.g. Monday to Friday, 9am – 5pm WAT."
    )
    support_email = models.EmailField(blank=True)
    sales_email = models.EmailField(blank=True)
    secondary_phone = models.CharField(max_length=40, blank=True)
    registration_number = models.CharField(
        max_length=80, blank=True, help_text="Company registration number, if you display one."
    )
    newsletter_blurb = models.CharField(
        max_length=255,
        blank=True,
        help_text="One line above the newsletter form. Falls back to a default.",
    )

    meta_title = models.CharField(max_length=70, blank=True)
    meta_description = models.CharField(max_length=180, blank=True)
    twitter_handle = models.CharField(
        max_length=40, blank=True, help_text="Without the @, e.g. techmiary."
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Site settings"
        verbose_name_plural = "Site settings"

    def __str__(self):
        return f"Site settings ({self.brand_name})"

    def clean(self):
        if not self.pk and SiteSettings.objects.exists():
            raise ValidationError(
                "Site settings already exist. Edit the existing record instead of adding another."
            )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        cache.delete(self.SINGLETON_CACHE_KEY)

    def delete(self, *args, **kwargs):
        cache.delete(self.SINGLETON_CACHE_KEY)
        return super().delete(*args, **kwargs)

    @classmethod
    def load(cls):
        """Return the singleton, or ``None`` when the site has not been configured yet."""
        return cls.objects.first()

    @property
    def display_company(self):
        """The name to show for the organisation, whatever has been filled in."""
        return self.company_name or self.legal_name or self.brand_name

    @property
    def brand_descriptor(self):
        """
        The words that sit under the brand name in the logo lockup.

        Derived from the company name rather than hard-coded, so renaming the
        company in the control panel updates the header, footer and drawer.
        "Techmiary Technology Concepts" with a brand of "TECHMIARY" gives
        "Technology Concepts"; if the two are unrelated, the full company
        name is shown instead.
        """
        company = (self.display_company or "").strip()
        brand = (self.brand_name or "").strip()
        if not company:
            return ""
        if brand and company.lower().startswith(brand.lower()):
            remainder = company[len(brand):].strip(" -–—·,")
            return remainder or company
        return company

    @property
    def resolved_hero_headline(self):
        return self.hero_headline or self.professional_title

    @property
    def resolved_hero_subheadline(self):
        return self.hero_subheadline or self.short_bio

    @property
    def primary_contact_email(self):
        return self.sales_email or self.email

    @property
    def resolved_meta_title(self):
        return self.meta_title or f"{self.name} — {self.professional_title}"

    @property
    def resolved_meta_description(self):
        return self.meta_description or self.short_bio[:180]


class SocialLink(models.Model):
    """A social profile. Only active links with a URL are rendered."""

    ICON_CHOICES = [
        ("github", "GitHub"),
        ("linkedin", "LinkedIn"),
        ("x", "X"),
        ("facebook", "Facebook"),
        ("whatsapp", "WhatsApp"),
        ("instagram", "Instagram"),
        ("youtube", "YouTube"),
        ("link", "Generic link"),
    ]

    name = models.CharField(max_length=60)
    url = models.URLField()
    icon = models.CharField(max_length=20, choices=ICON_CHOICES, default="link")
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "name"]

    def __str__(self):
        return self.name


class SkillCategory(models.Model):
    """Grouping for skills, e.g. Backend, Frontend, Infrastructure."""

    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=90, unique=True, blank=True)
    description = models.CharField(max_length=255, blank=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "name"]
        verbose_name_plural = "Skill categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:90]
        super().save(*args, **kwargs)


class Skill(models.Model):
    """
    A single technology.

    ``proficiency`` is optional and deliberately unranked by default — a skill
    is listed because it is used, not to claim a level that is not verifiable.
    """

    PROFICIENCY_CHOICES = [
        ("", "Not stated"),
        ("working", "Working knowledge"),
        ("proficient", "Proficient"),
        ("primary", "Primary tool"),
    ]

    category = models.ForeignKey(
        SkillCategory, on_delete=models.CASCADE, related_name="skills"
    )
    name = models.CharField(max_length=80)
    description = models.CharField(max_length=255, blank=True)
    proficiency = models.CharField(
        max_length=20, choices=PROFICIENCY_CHOICES, blank=True, default=""
    )
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["category", "name"], name="unique_skill_per_category"
            )
        ]
        indexes = [models.Index(fields=["is_active", "display_order"])]

    def __str__(self):
        return f"{self.name} ({self.category})"


class Partner(models.Model):
    """
    An organisation shown on the landing page, either as a partner or as one
    of the organisations the work is trusted by.

    Like every other claim on this site, nothing here is hard-coded: an entry
    exists only because someone added it in the admin. ``consent_on_file``
    records that the organisation agreed to be named — it does not gate
    display, so that a record never silently disappears, but it is shown in
    the admin list so the obligation stays visible.
    """

    KIND_PARTNER = "partner"
    KIND_TRUSTED = "trusted"
    KIND_CHOICES = [
        (KIND_PARTNER, "Partner"),
        (KIND_TRUSTED, "Trusted by"),
    ]

    name = models.CharField(max_length=160)
    kind = models.CharField(
        max_length=20,
        choices=KIND_CHOICES,
        default=KIND_PARTNER,
        help_text="Partners are collaborators; Trusted by are organisations you have delivered for.",
    )
    logo = models.ImageField(
        upload_to="partners/",
        blank=True,
        help_text=(
            "Upload a dark version — the site background is light blue. "
            "Leave empty to show the name as a wordmark instead."
        ),
    )
    logo_alt = models.CharField(
        max_length=180,
        blank=True,
        help_text="Defaults to the organisation name.",
    )
    url = models.URLField(blank=True, help_text="Optional link to their website.")
    relationship = models.CharField(
        max_length=200,
        blank=True,
        help_text="One short line, e.g. Infrastructure partner. Shown under the name.",
    )
    consent_on_file = models.BooleanField(
        default=False,
        help_text="Tick once the organisation has agreed to be named here.",
    )
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["kind", "name"], name="unique_partner_per_kind"
            )
        ]
        indexes = [models.Index(fields=["is_active", "kind", "display_order"])]

    def __str__(self):
        return f"{self.name} ({self.get_kind_display()})"

    @property
    def logo_alt_text(self):
        return self.logo_alt or f"{self.name} logo"
