from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html

from .models import (
    Project,
    ProjectCategory,
    ProjectChallenge,
    ProjectFeature,
    ProjectImage,
    Technology,
)


class ProjectFeatureInline(admin.TabularInline):
    model = ProjectFeature
    extra = 1
    fields = ("title", "description", "display_order")


class ProjectChallengeInline(admin.TabularInline):
    model = ProjectChallenge
    extra = 1
    fields = ("title", "description", "display_order")


class ProjectImageInline(admin.TabularInline):
    model = ProjectImage
    extra = 1
    fields = ("image", "alt_text", "caption", "display_order")


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "year",
        "status",
        "featured",
        "is_published",
        "display_order",
        "website_link",
    )
    list_filter = ("status", "featured", "is_published", "category", "technologies")
    list_editable = ("featured", "is_published", "display_order")
    search_fields = ("title", "short_description", "description", "client")
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("technologies",)
    readonly_fields = ("created_at", "updated_at", "cover_preview")
    list_select_related = ("category",)
    date_hierarchy = "created_at"
    ordering = ("display_order", "-year")
    inlines = [ProjectFeatureInline, ProjectChallengeInline, ProjectImageInline]
    fieldsets = (
        ("Identity", {"fields": ("title", "slug", "category", "technologies")}),
        ("Summary", {"fields": ("short_description", "description")}),
        (
            "Case study",
            {
                "fields": ("problem", "solution", "result"),
                "description": "Describe only what the system actually does. Leave a field blank to hide its section.",
            },
        ),
        ("Architecture", {"fields": ("architecture_description", "architecture_diagram")}),
        ("Facts", {"fields": ("client", "year", "status", "website_url", "github_url")}),
        ("Imagery", {"fields": ("cover_image", "cover_preview", "cover_image_alt")}),
        ("Display", {"fields": ("featured", "is_published", "display_order")}),
        ("SEO", {"fields": ("meta_title", "meta_description"), "classes": ("collapse",)}),
        ("Bookkeeping", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description="Website")
    def website_link(self, obj):
        if obj.website_url:
            return format_html('<a href="{}" target="_blank" rel="noopener">Open</a>', obj.website_url)
        return "—"

    @admin.display(description="Cover preview")
    def cover_preview(self, obj):
        if obj and obj.cover_image:
            return format_html('<img src="{}" alt="" style="max-height:140px;border-radius:8px">', obj.cover_image.url)
        return "No cover uploaded"


@admin.register(ProjectCategory)
class ProjectCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "display_order", "project_count")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)
    ordering = ("display_order", "name")

    def get_queryset(self, request):
        # Counted in the same query as the rows; calling obj.projects.count()
        # per row issues one COUNT per row instead.
        return super().get_queryset(request).annotate(_projects=Count("projects"))

    @admin.display(description="Projects", ordering="_projects")
    def project_count(self, obj):
        return obj._projects


@admin.register(Technology)
class TechnologyAdmin(admin.ModelAdmin):
    list_display = ("name", "project_count")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)
    ordering = ("name",)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_projects=Count("projects"))

    @admin.display(description="Used in", ordering="_projects")
    def project_count(self, obj):
        return obj._projects


@admin.register(ProjectFeature)
class ProjectFeatureAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "display_order")
    list_filter = ("project",)
    search_fields = ("title", "description")
    list_select_related = ("project",)


@admin.register(ProjectImage)
class ProjectImageAdmin(admin.ModelAdmin):
    list_display = ("project", "alt_text", "display_order")
    list_filter = ("project",)
    list_select_related = ("project",)
