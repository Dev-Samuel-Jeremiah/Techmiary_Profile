from django.contrib import admin

from .models import Experience, Responsibility


class ResponsibilityInline(admin.TabularInline):
    model = Responsibility
    extra = 2
    fields = ("text", "display_order")


@admin.register(Experience)
class ExperienceAdmin(admin.ModelAdmin):
    list_display = ("position", "organization", "period", "is_current", "is_active", "display_order")
    list_filter = ("is_current", "is_active")
    list_editable = ("display_order", "is_active")
    search_fields = ("organization", "position", "description", "technologies")
    ordering = ("display_order", "-start_date")
    inlines = [ResponsibilityInline]
    fieldsets = (
        ("Role", {"fields": ("organization", "organization_url", "position", "location")}),
        ("Dates", {"fields": ("start_date", "end_date", "is_current")}),
        ("Detail", {"fields": ("description", "technologies")}),
        ("Display", {"fields": ("display_order", "is_active")}),
    )
