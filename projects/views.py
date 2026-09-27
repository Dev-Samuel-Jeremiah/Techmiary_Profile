from django.views.generic import DetailView, ListView

from core.seo import SEOMixin, breadcrumb_schema, project_schema

from .models import Project, ProjectCategory


class ProjectListView(SEOMixin, ListView):
    template_name = "projects/project_list.html"
    context_object_name = "projects"
    paginate_by = 9

    def get_paginate_by(self, queryset):
        from django.conf import settings

        return settings.PROJECT_PAGE_SIZE

    def get_queryset(self):
        queryset = Project.published.with_related()
        self.active_category = None
        slug = self.request.GET.get("category")
        if slug:
            self.active_category = ProjectCategory.objects.filter(slug=slug).first()
            if self.active_category:
                queryset = queryset.filter(category=self.active_category)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = ProjectCategory.objects.filter(
            projects__is_published=True
        ).distinct()
        context["active_category"] = self.active_category
        return context

    def get_meta_title(self, context):
        site = context.get("site")
        return f"Projects — {site.name}" if site else "Projects"

    def get_meta_description(self, context):
        return (
            "SaaS platforms, school management systems, EdTech applications and "
            "business information systems built with Python and Django."
        )

    def get_structured_data(self, context):
        return breadcrumb_schema([("Home", "/"), ("Projects", "/projects/")])


class ProjectDetailView(SEOMixin, DetailView):
    template_name = "projects/project_detail.html"
    context_object_name = "project"

    def get_queryset(self):
        return Project.published.with_related().prefetch_related(
            "features", "challenges", "images"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.object
        context["related_projects"] = (
            Project.published.with_related()
            .filter(category=project.category)
            .exclude(pk=project.pk)[:3]
        )
        return context

    def get_meta_title(self, context):
        return self.object.resolved_meta_title

    def get_meta_description(self, context):
        return self.object.resolved_meta_description

    def get_structured_data(self, context):
        project = self.object
        return {
            "@context": "https://schema.org",
            "@graph": [
                {k: v for k, v in project_schema(project).items() if k != "@context"},
                {
                    k: v
                    for k, v in breadcrumb_schema(
                        [
                            ("Home", "/"),
                            ("Projects", "/projects/"),
                            (project.title, project.get_absolute_url()),
                        ]
                    ).items()
                    if k != "@context"
                },
            ],
        }
