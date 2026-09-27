"""Professional experience timeline."""
from django.db import models


class Experience(models.Model):
    """One role. Nothing about employment history is hard-coded in templates."""

    organization = models.CharField(max_length=160)
    organization_url = models.URLField(blank=True)
    position = models.CharField(max_length=160)
    location = models.CharField(max_length=160, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(
        null=True, blank=True, help_text="Leave empty for a current role."
    )
    is_current = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    technologies = models.CharField(
        max_length=255,
        blank=True,
        help_text="Comma-separated list, e.g. Python, Django, PostgreSQL.",
    )
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "-start_date"]
        verbose_name_plural = "Experience"
        indexes = [models.Index(fields=["is_active", "display_order"])]

    def __str__(self):
        return f"{self.position} — {self.organization}"

    @property
    def technology_list(self):
        return [t.strip() for t in self.technologies.split(",") if t.strip()]

    @property
    def period(self):
        start = self.start_date.strftime("%b %Y")
        if self.is_current or not self.end_date:
            return f"{start} — Present"
        return f"{start} — {self.end_date.strftime('%b %Y')}"


class Responsibility(models.Model):
    """A bullet point under a role."""

    experience = models.ForeignKey(
        Experience, on_delete=models.CASCADE, related_name="responsibilities"
    )
    text = models.CharField(max_length=300)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "id"]
        verbose_name_plural = "Responsibilities"

    def __str__(self):
        return self.text[:60]
