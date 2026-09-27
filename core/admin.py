from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html

from .models import Partner, SiteSettings, Skill, SkillCategory, SocialLink


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    """Singleton admin: one record, no add button once it exists."""

    list_display = ("brand_name", "name", "professional_title", "updated_at")
    readonly_fields = ("updated_at", "profile_preview")
    fieldsets = (
        ("Identity", {"fields": ("name", "brand_name", "company_name", "professional_title", "tagline")}),
        ("Biography", {"fields": ("short_bio", "long_bio")}),
        ("Imagery", {"fields": ("profile_image", "profile_preview", "og_image", "logo", "favicon")}),
        ("Contact", {"fields": ("email", "show_email_publicly", "phone", "location")}),
        ("Links", {"fields": ("website_url", "github_url", "linkedin_url", "twitter_url", "whatsapp_url")}),
        ("Documents", {"fields": ("resume_file",)}),
        ("SEO", {"fields": ("meta_title", "meta_description", "twitter_handle")}),
        ("Bookkeeping", {"fields": ("updated_at",), "classes": ("collapse",)}),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Preview")
    def profile_preview(self, obj):
        if obj and obj.profile_image:
            return format_html(
                '<img src="{}" alt="" style="max-height:120px;border-radius:8px">',
                obj.profile_image.url,
            )
        return "No image uploaded"


@admin.register(SocialLink)
class SocialLinkAdmin(admin.ModelAdmin):
    list_display = ("name", "icon", "url", "display_order", "is_active")
    list_filter = ("is_active", "icon")
    list_editable = ("display_order", "is_active")
    search_fields = ("name", "url")
    ordering = ("display_order", "name")


class SkillInline(admin.TabularInline):
    model = Skill
    extra = 1
    fields = ("name", "description", "proficiency", "display_order", "is_active")
    ordering = ("display_order", "name")


@admin.register(SkillCategory)
class SkillCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "display_order", "skill_count")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "description")
    ordering = ("display_order", "name")
    inlines = [SkillInline]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_skills=Count("skills"))

    @admin.display(description="Skills", ordering="_skills")
    def skill_count(self, obj):
        return obj._skills


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "proficiency", "display_order", "is_active")
    list_filter = ("category", "is_active", "proficiency")
    list_editable = ("display_order", "is_active")
    search_fields = ("name", "description")
    list_select_related = ("category",)
    ordering = ("category", "display_order", "name")


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "kind",
        "relationship",
        "has_logo",
        "consent_on_file",
        "display_order",
        "is_active",
    )
    list_filter = ("kind", "is_active", "consent_on_file")
    list_editable = ("display_order", "is_active", "consent_on_file")
    search_fields = ("name", "relationship")
    ordering = ("kind", "display_order", "name")
    fieldsets = (
        (None, {"fields": ("name", "kind", "relationship", "url")}),
        ("Logo", {"fields": ("logo", "logo_alt")}),
        (
            "Publishing",
            {
                "fields": ("consent_on_file", "display_order", "is_active"),
                "description": (
                    "Only name an organisation that has agreed to appear here. "
                    "Untick 'is active' to remove it from the site without deleting "
                    "the record."
                ),
            },
        ),
    )

    @admin.display(description="Logo", boolean=True)
    def has_logo(self, obj):
        return bool(obj.logo)
