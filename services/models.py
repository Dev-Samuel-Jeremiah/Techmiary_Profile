"""Services offered."""
from django.db import models
from django.utils.text import slugify


class Service(models.Model):
    """A service line, fully editable from the admin."""

    title = models.CharField(max_length=140)
    slug = models.SlugField(max_length=160, unique=True, blank=True)
    summary = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    icon = models.CharField(
        max_length=40,
        default="code",
        help_text="Icon key rendered by the template, e.g. code, cloud, school, api.",
    )
    deliverables = models.TextField(
        blank=True, help_text="One deliverable per line."
    )
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(
        default=False, help_text="Featured services appear on the homepage."
    )

    class Meta:
        ordering = ["display_order", "title"]
        indexes = [models.Index(fields=["is_active", "display_order"])]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)[:160]
        super().save(*args, **kwargs)

    @property
    def deliverable_list(self):
        return [line.strip() for line in self.deliverables.splitlines() if line.strip()]
