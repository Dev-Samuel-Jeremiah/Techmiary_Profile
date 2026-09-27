from django.contrib import admin
from django.utils.html import format_html

from .models import ContactMessage, NewsletterSubscriber, QuoteRequest


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("subject", "name", "email_link", "company", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("name", "email", "subject", "message", "company", "phone")
    readonly_fields = ("name", "email", "phone", "company", "subject", "message", "ip_address", "user_agent", "created_at")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    actions = ["mark_read", "mark_replied", "mark_spam"]
    fieldsets = (
        ("Enquiry", {"fields": ("name", "email", "phone", "company", "subject", "message")}),
        ("Handling", {"fields": ("status",)}),
        ("Request metadata", {"fields": ("ip_address", "user_agent", "created_at"), "classes": ("collapse",)}),
    )

    def has_add_permission(self, request):
        return False

    @admin.display(description="Email", ordering="email")
    def email_link(self, obj):
        return format_html('<a href="mailto:{}">{}</a>', obj.email, obj.email)

    @admin.action(description="Mark selected as read")
    def mark_read(self, request, queryset):
        updated = queryset.update(status=ContactMessage.STATUS_READ)
        self.message_user(request, f"{updated} message(s) marked as read.")

    @admin.action(description="Mark selected as replied")
    def mark_replied(self, request, queryset):
        updated = queryset.update(status=ContactMessage.STATUS_REPLIED)
        self.message_user(request, f"{updated} message(s) marked as replied.")

    @admin.action(description="Mark selected as spam")
    def mark_spam(self, request, queryset):
        updated = queryset.update(status=ContactMessage.STATUS_SPAM)
        self.message_user(request, f"{updated} message(s) marked as spam.")


@admin.register(QuoteRequest)
class QuoteRequestAdmin(admin.ModelAdmin):
    list_display = (
        "project_title",
        "contact_name",
        "organisation",
        "requested_for",
        "budget_range",
        "timeline",
        "status",
        "created_at",
    )
    list_filter = ("status", "budget_range", "timeline", "organisation_type", "created_at")
    search_fields = ("project_title", "description", "contact_name", "email", "organisation")
    list_select_related = ("service", "solution")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    readonly_fields = (
        "service", "solution", "project_title", "description", "budget_range",
        "timeline", "existing_system", "contact_name", "email", "phone",
        "organisation", "organisation_type", "country", "ip_address", "created_at",
    )
    actions = ["mark_reviewing", "mark_quoted", "mark_closed"]
    fieldsets = (
        ("Project", {"fields": ("project_title", "description", "service", "solution")}),
        ("Scope", {"fields": ("budget_range", "timeline", "existing_system")}),
        ("Contact", {"fields": ("contact_name", "email", "phone", "organisation", "organisation_type", "country")}),
        ("Handling", {"fields": ("status", "internal_notes")}),
        ("Request metadata", {"fields": ("ip_address", "created_at"), "classes": ("collapse",)}),
    )

    def has_add_permission(self, request):
        return False

    @admin.action(description="Mark as reviewing")
    def mark_reviewing(self, request, queryset):
        self.message_user(request, f"{queryset.update(status=QuoteRequest.STATUS_REVIEWING)} updated.")

    @admin.action(description="Mark as quote sent")
    def mark_quoted(self, request, queryset):
        self.message_user(request, f"{queryset.update(status=QuoteRequest.STATUS_QUOTED)} updated.")

    @admin.action(description="Mark as closed")
    def mark_closed(self, request, queryset):
        self.message_user(request, f"{queryset.update(status=QuoteRequest.STATUS_CLOSED)} updated.")


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ("email", "name", "source", "is_active", "created_at")
    list_filter = ("is_active", "source", "created_at")
    list_editable = ("is_active",)
    search_fields = ("email", "name")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    readonly_fields = ("ip_address", "created_at")
    actions = ["export_csv", "unsubscribe"]

    @admin.action(description="Export selected as CSV")
    def export_csv(self, request, queryset):
        import csv

        from django.http import HttpResponse

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="subscribers.csv"'
        writer = csv.writer(response)
        writer.writerow(["email", "name", "source", "active", "subscribed_at"])
        for subscriber in queryset:
            writer.writerow([
                subscriber.email,
                subscriber.name,
                subscriber.get_source_display(),
                "yes" if subscriber.is_active else "no",
                subscriber.created_at.isoformat(),
            ])
        return response

    @admin.action(description="Mark as unsubscribed")
    def unsubscribe(self, request, queryset):
        from django.utils import timezone

        updated = queryset.update(is_active=False, unsubscribed_at=timezone.now())
        self.message_user(request, f"{updated} subscriber(s) unsubscribed.")
