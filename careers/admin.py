from django.contrib import admin
from django.utils.html import format_html

from .models import Department, JobApplication, JobOpening


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "display_order", "open_count")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "description")

    @admin.display(description="Open roles")
    def open_count(self, obj):
        return obj.openings.filter(status=JobOpening.STATUS_OPEN, is_published=True).count()


class JobApplicationInline(admin.TabularInline):
    model = JobApplication
    extra = 0
    can_delete = False
    fields = ("full_name", "email", "status", "created_at")
    readonly_fields = ("full_name", "email", "created_at")
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(JobOpening)
class JobOpeningAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "department",
        "location_type",
        "employment_type",
        "status",
        "is_published",
        "application_count",
        "posted_at",
    )
    list_filter = ("status", "is_published", "department", "location_type", "employment_type", "experience_level")
    list_editable = ("status", "is_published")
    search_fields = ("title", "summary", "description")
    prepopulated_fields = {"slug": ("title",)}
    list_select_related = ("department",)
    date_hierarchy = "created_at"
    readonly_fields = ("created_at", "updated_at")
    inlines = [JobApplicationInline]
    actions = ["open_roles", "close_roles"]
    fieldsets = (
        ("Role", {"fields": ("title", "slug", "department", "summary")}),
        ("Detail", {"fields": ("description", "responsibilities", "requirements", "nice_to_have", "benefits")}),
        ("Conditions", {"fields": ("location", "location_type", "employment_type", "experience_level", "salary_range")}),
        ("Publishing", {"fields": ("status", "is_published", "posted_at", "closes_at", "display_order")}),
        ("SEO", {"fields": ("meta_title", "meta_description"), "classes": ("collapse",)}),
        ("Bookkeeping", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description="Applications")
    def application_count(self, obj):
        return obj.applications.count()

    @admin.action(description="Mark selected roles as open")
    def open_roles(self, request, queryset):
        updated = queryset.update(status=JobOpening.STATUS_OPEN)
        self.message_user(request, f"{updated} role(s) opened.")

    @admin.action(description="Mark selected roles as closed")
    def close_roles(self, request, queryset):
        updated = queryset.update(status=JobOpening.STATUS_CLOSED)
        self.message_user(request, f"{updated} role(s) closed.")


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ("full_name", "job", "email_link", "status", "cv_link", "created_at")
    list_filter = ("status", "job", "created_at")
    search_fields = ("full_name", "email", "cover_letter", "location")
    list_select_related = ("job",)
    date_hierarchy = "created_at"
    readonly_fields = (
        "job", "full_name", "email", "phone", "location",
        "portfolio_url", "linkedin_url", "cover_letter", "cv", "ip_address", "created_at",
    )
    actions = ["mark_reviewing", "mark_shortlisted", "mark_rejected"]
    fieldsets = (
        ("Applicant", {"fields": ("job", "full_name", "email", "phone", "location")}),
        ("Submission", {"fields": ("cv", "cover_letter", "portfolio_url", "linkedin_url")}),
        ("Handling", {"fields": ("status", "notes")}),
        ("Request metadata", {"fields": ("ip_address", "created_at"), "classes": ("collapse",)}),
    )

    def has_add_permission(self, request):
        return False

    @admin.display(description="Email", ordering="email")
    def email_link(self, obj):
        return format_html('<a href="mailto:{}">{}</a>', obj.email, obj.email)

    @admin.display(description="CV")
    def cv_link(self, obj):
        if obj.cv:
            return format_html('<a href="{}" target="_blank" rel="noopener">Download</a>', obj.cv.url)
        return "—"

    @admin.action(description="Mark as reviewing")
    def mark_reviewing(self, request, queryset):
        self.message_user(request, f"{queryset.update(status=JobApplication.STATUS_REVIEWING)} updated.")

    @admin.action(description="Mark as shortlisted")
    def mark_shortlisted(self, request, queryset):
        self.message_user(request, f"{queryset.update(status=JobApplication.STATUS_SHORTLISTED)} updated.")

    @admin.action(description="Mark as not proceeding")
    def mark_rejected(self, request, queryset):
        self.message_user(request, f"{queryset.update(status=JobApplication.STATUS_REJECTED)} updated.")
