from django.contrib import admin
from django.utils.html import format_html

from .models import (
    FAQ,
    Client,
    CompanyValue,
    FAQCategory,
    Industry,
    Milestone,
    Resource,
    ResourceCategory,
    Solution,
    SolutionCapability,
    TeamMember,
    Testimonial,
)


class SolutionCapabilityInline(admin.TabularInline):
    model = SolutionCapability
    extra = 1
    fields = ("title", "description", "icon", "display_order")


@admin.register(Solution)
class SolutionAdmin(admin.ModelAdmin):
    list_display = ("name", "tagline", "is_featured", "is_active", "display_order")
    list_filter = ("is_active", "is_featured", "industries")
    list_editable = ("is_featured", "is_active", "display_order")
    search_fields = ("name", "tagline", "summary", "overview")
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ("industries",)
    readonly_fields = ("created_at", "updated_at", "hero_preview")
    inlines = [SolutionCapabilityInline]
    fieldsets = (
        ("Identity", {"fields": ("name", "slug", "icon", "industries", "related_project")}),
        ("Copy", {"fields": ("tagline", "summary", "overview", "who_its_for", "outcome")}),
        ("Imagery", {"fields": ("hero_image", "hero_preview", "hero_image_alt")}),
        ("Display", {"fields": ("is_featured", "is_active", "display_order")}),
        ("SEO", {"fields": ("meta_title", "meta_description"), "classes": ("collapse",)}),
        ("Bookkeeping", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description="Preview")
    def hero_preview(self, obj):
        if obj and obj.hero_image:
            return format_html('<img src="{}" alt="" style="max-height:130px;border-radius:8px">', obj.hero_image.url)
        return "No image uploaded"


@admin.register(Industry)
class IndustryAdmin(admin.ModelAdmin):
    list_display = ("name", "tagline", "solution_count", "is_active", "display_order")
    list_filter = ("is_active",)
    list_editable = ("is_active", "display_order")
    search_fields = ("name", "summary", "overview")
    prepopulated_fields = {"slug": ("name",)}
    fieldsets = (
        ("Identity", {"fields": ("name", "slug", "icon")}),
        ("Copy", {"fields": ("tagline", "summary", "overview", "challenges")}),
        ("Imagery", {"fields": ("image", "image_alt")}),
        ("Display", {"fields": ("is_active", "display_order")}),
    )

    @admin.display(description="Solutions")
    def solution_count(self, obj):
        return obj.solutions.count()


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ("name", "role", "department", "is_leadership", "is_founder", "is_active", "display_order")
    list_filter = ("is_leadership", "is_founder", "is_active", "department")
    list_editable = ("is_leadership", "is_active", "display_order")
    search_fields = ("name", "role", "short_bio", "bio")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("photo_preview",)
    fieldsets = (
        ("Person", {"fields": ("name", "slug", "role", "department")}),
        ("Biography", {"fields": ("short_bio", "bio")}),
        ("Photo", {"fields": ("photo", "photo_preview", "photo_alt")}),
        ("Links", {"fields": ("email", "linkedin_url", "github_url", "twitter_url")}),
        ("Display", {"fields": ("is_leadership", "is_founder", "is_active", "display_order")}),
    )

    @admin.display(description="Preview")
    def photo_preview(self, obj):
        if obj and obj.photo:
            return format_html('<img src="{}" alt="" style="max-height:120px;border-radius:50%">', obj.photo.url)
        return "No photo uploaded"


@admin.register(CompanyValue)
class CompanyValueAdmin(admin.ModelAdmin):
    list_display = ("title", "icon", "is_active", "display_order")
    list_editable = ("is_active", "display_order")
    list_filter = ("is_active",)
    search_fields = ("title", "description")


@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    list_display = ("year", "title", "is_active", "display_order")
    list_editable = ("is_active", "display_order")
    list_filter = ("is_active", "year")
    search_fields = ("title", "description")
    ordering = ("year",)


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("name", "industry", "engagement", "consent_on_file", "is_active", "display_order")
    list_filter = ("consent_on_file", "is_active", "industry")
    list_editable = ("consent_on_file", "is_active", "display_order")
    search_fields = ("name", "engagement")
    prepopulated_fields = {"slug": ("name",)}
    list_select_related = ("industry",)
    fieldsets = (
        ("Organisation", {"fields": ("name", "slug", "industry", "website_url", "engagement")}),
        ("Logo", {"fields": ("logo", "logo_alt")}),
        (
            "Permission",
            {
                "fields": ("consent_on_file",),
                "description": "Only add an organisation you are permitted to name publicly.",
            },
        ),
        ("Display", {"fields": ("is_active", "display_order")}),
    )


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ("author_name", "organisation", "consent_on_file", "is_active", "display_order")
    list_filter = ("consent_on_file", "is_active")
    list_editable = ("consent_on_file", "is_active", "display_order")
    search_fields = ("quote", "author_name", "organisation")
    list_select_related = ("client",)
    fieldsets = (
        ("Quote", {"fields": ("quote",)}),
        ("Attribution", {"fields": ("author_name", "author_role", "organisation", "client", "author_photo")}),
        (
            "Permission",
            {
                "fields": ("consent_on_file",),
                "description": "Only publish a quote the person actually gave and approved.",
            },
        ),
        ("Display", {"fields": ("is_active", "display_order")}),
    )


@admin.register(ResourceCategory)
class ResourceCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "display_order", "resource_count")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)

    @admin.display(description="Resources")
    def resource_count(self, obj):
        return obj.resources.count()


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "category", "published_at", "is_available", "is_active")
    list_filter = ("kind", "category", "is_active")
    list_editable = ("is_active",)
    search_fields = ("title", "summary")
    prepopulated_fields = {"slug": ("title",)}
    list_select_related = ("category",)
    date_hierarchy = "published_at"
    fieldsets = (
        ("Resource", {"fields": ("title", "slug", "kind", "category")}),
        ("Content", {"fields": ("summary", "file", "external_url", "cover_image", "pages", "published_at")}),
        ("Display", {"fields": ("is_active", "display_order")}),
    )

    @admin.display(boolean=True, description="Downloadable")
    def is_available(self, obj):
        return obj.is_available


@admin.register(FAQCategory)
class FAQCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "display_order", "faq_count")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)

    @admin.display(description="Questions")
    def faq_count(self, obj):
        return obj.faqs.count()


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ("question", "category", "is_active", "display_order")
    list_filter = ("category", "is_active")
    list_editable = ("is_active", "display_order")
    search_fields = ("question", "answer")
    list_select_related = ("category",)
