from django.views.generic import ListView

from core.seo import SEOMixin, breadcrumb_schema

from .models import Experience


class ExperienceListView(SEOMixin, ListView):
    template_name = "experience/experience_list.html"
    context_object_name = "experiences"

    def get_queryset(self):
        return Experience.objects.filter(is_active=True).prefetch_related(
            "responsibilities"
        )

    def get_meta_title(self, context):
        site = context.get("site")
        return f"Experience — {site.name}" if site else "Experience"

    def get_meta_description(self, context):
        return "Professional roles, responsibilities and the technologies used in each."

    def get_structured_data(self, context):
        return breadcrumb_schema([("Home", "/"), ("Experience", "/experience/")])
