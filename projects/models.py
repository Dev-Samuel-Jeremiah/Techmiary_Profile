"""Projects and their case-study content."""
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class Technology(models.Model):
    """A technology tag reused across projects instead of repeated free text."""

    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=70, unique=True, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Technologies"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:70]
        super().save(*args, **kwargs)


class ProjectCategory(models.Model):
    """e.g. SaaS / School ERP, EdTech / Language Learning."""

    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=130, unique=True, blank=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "name"]
        verbose_name_plural = "Project categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:130]
        super().save(*args, **kwargs)


class PublishedProjectManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_published=True)

    def with_related(self):
        return (
            self.get_queryset()
            .select_related("category")
            .prefetch_related("technologies")
        )


class Project(models.Model):
    """
    A shipped product or system.

    Every claim on a case study comes from this record or its children, so
    nothing is asserted in a template that an editor cannot change or remove.
    """

    STATUS_PLANNING = "planning"
    STATUS_DEVELOPMENT = "development"
    STATUS_LIVE = "live"
    STATUS_MAINTENANCE = "maintenance"
    STATUS_ARCHIVED = "archived"
    STATUS_CHOICES = [
        (STATUS_PLANNING, "Planning"),
        (STATUS_DEVELOPMENT, "Development"),
        (STATUS_LIVE, "Live"),
        (STATUS_MAINTENANCE, "Maintenance"),
        (STATUS_ARCHIVED, "Archived"),
    ]

    title = models.CharField(max_length=140)
    slug = models.SlugField(max_length=160, unique=True)
    category = models.ForeignKey(
        ProjectCategory,
        on_delete=models.PROTECT,
        related_name="projects",
    )
    short_description = models.CharField(
        max_length=300, help_text="One or two lines shown on project cards."
    )
    description = models.TextField(
        blank=True, help_text="Overview section of the case study."
    )
    problem = models.TextField(blank=True, help_text="The problem the software addresses.")
    solution = models.TextField(blank=True, help_text="What was actually built.")
    result = models.TextField(
        blank=True,
        help_text="What was delivered. Do not add user counts or metrics unless they are verified.",
    )
    architecture_description = models.TextField(
        blank=True,
        help_text="Plain-text description of the deployed architecture. Leave blank to hide the section.",
    )
    architecture_diagram = models.ImageField(upload_to="projects/architecture/", blank=True)

    client = models.CharField(
        max_length=160,
        blank=True,
        help_text="Only fill this in for real, named clients who agreed to be listed.",
    )
    year = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_DEVELOPMENT
    )
    website_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)

    cover_image = models.ImageField(upload_to="projects/covers/", blank=True)
    cover_image_alt = models.CharField(max_length=180, blank=True)

    technologies = models.ManyToManyField(
        Technology, related_name="projects", blank=True
    )

    featured = models.BooleanField(
        default=False, help_text="Featured projects appear on the homepage."
    )
    is_published = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    meta_title = models.CharField(max_length=70, blank=True)
    meta_description = models.CharField(max_length=180, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()
    published = PublishedProjectManager()

    class Meta:
        ordering = ["display_order", "-year", "title"]
        indexes = [
            models.Index(fields=["is_published", "featured", "display_order"]),
            models.Index(fields=["slug"]),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)[:160]
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("projects:detail", kwargs={"slug": self.slug})

    @property
    def resolved_meta_title(self):
        return self.meta_title or f"{self.title} — Case Study"

    @property
    def resolved_meta_description(self):
        return self.meta_description or self.short_description[:180]

    @property
    def cover_alt_text(self):
        return self.cover_image_alt or f"{self.title} interface screenshot"

    @property
    def has_case_study_body(self):
        return any(
            [self.description, self.problem, self.solution, self.result]
        )


class ProjectFeature(models.Model):
    """A capability of the product, shown as a card on the case study."""

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="features"
    )
    title = models.CharField(max_length=140)
    description = models.TextField(blank=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "id"]

    def __str__(self):
        return f"{self.project.title}: {self.title}"


class ProjectChallenge(models.Model):
    """An engineering challenge the project actually involved."""

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="challenges"
    )
    title = models.CharField(max_length=140)
    description = models.TextField(blank=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "id"]

    def __str__(self):
        return f"{self.project.title}: {self.title}"


class ProjectImage(models.Model):
    """Gallery image for a project."""

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to="projects/gallery/")
    alt_text = models.CharField(max_length=180)
    caption = models.CharField(max_length=255, blank=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "id"]

    def __str__(self):
        return f"{self.project.title} image {self.pk}"
