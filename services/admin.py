from django.contrib import admin

from .models import Service


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("title", "icon", "is_featured", "is_active", "display_order")
    list_filter = ("is_active", "is_featured")
    list_editable = ("display_order", "is_active", "is_featured")
    search_fields = ("title", "summary", "description")
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("display_order", "title")
    fieldsets = (
        ("Service", {"fields": ("title", "slug", "icon")}),
        ("Content", {"fields": ("summary", "description", "deliverables")}),
        ("Display", {"fields": ("display_order", "is_active", "is_featured")}),
    )
