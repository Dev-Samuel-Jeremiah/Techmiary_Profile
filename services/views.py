from django.views.generic import ListView

from core.seo import SEOMixin, breadcrumb_schema

from .models import Service


class ServiceListView(SEOMixin, ListView):
    template_name = "services/service_list.html"
    context_object_name = "services"

    def get_queryset(self):
        return Service.objects.filter(is_active=True)

    def get_meta_title(self, context):
        site = context.get("site")
        return f"Services — {site.name}" if site else "Services"

    def get_meta_description(self, context):
        return (
            "Custom software development, SaaS platforms, school management systems, "
            "EdTech applications, API integrations and production deployment."
        )

    def get_structured_data(self, context):
        return breadcrumb_schema([("Home", "/"), ("Services", "/services/")])
