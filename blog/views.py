from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from django.views.generic import DetailView, ListView

from core.seo import SEOMixin, absolute, breadcrumb_schema

from .models import BlogCategory, BlogPost


class PostListView(SEOMixin, ListView):
    template_name = "blog/post_list.html"
    context_object_name = "posts"
    paginate_by = 6

    def get_paginate_by(self, queryset):
        return settings.BLOG_PAGE_SIZE

    def get_queryset(self):
        queryset = BlogPost.live.all()
        self.query = (self.request.GET.get("q") or "").strip()
        self.active_category = None

        slug = self.request.GET.get("category")
        if slug:
            self.active_category = BlogCategory.objects.filter(slug=slug).first()
            if self.active_category:
                queryset = queryset.filter(category=self.active_category)

        if self.query:
            queryset = queryset.filter(
                Q(title__icontains=self.query)
                | Q(excerpt__icontains=self.query)
                | Q(content__icontains=self.query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Must match BlogPost.live: a category whose only post is scheduled
        # for the future would otherwise show a filter chip leading nowhere.
        context["categories"] = BlogCategory.objects.filter(
            posts__published=True, posts__published_at__lte=timezone.now()
        ).distinct()
        context["active_category"] = self.active_category
        context["query"] = self.query
        context["featured_post"] = (
            BlogPost.live.filter(is_featured=True).first()
            if not (self.query or self.active_category)
            else None
        )
        return context

    def get_meta_title(self, context):
        site = context.get("site")
        return f"Blog — {site.brand_name}" if site else "Blog"

    def get_meta_description(self, context):
        return (
            "Notes on Django, Python, SaaS architecture, PostgreSQL, Linux deployment "
            "and lessons from running production systems."
        )

    def get_structured_data(self, context):
        return breadcrumb_schema([("Home", "/"), ("Blog", "/blog/")])


class PostDetailView(SEOMixin, DetailView):
    template_name = "blog/post_detail.html"
    context_object_name = "post"

    def get_queryset(self):
        return BlogPost.live.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["related_posts"] = (
            BlogPost.live.filter(category=self.object.category)
            .exclude(pk=self.object.pk)[:3]
            if self.object.category
            else BlogPost.live.exclude(pk=self.object.pk)[:3]
        )
        return context

    def get_meta_title(self, context):
        return self.object.resolved_meta_title

    def get_meta_description(self, context):
        return self.object.resolved_meta_description

    def get_structured_data(self, context):
        post = self.object
        site = context.get("site")
        data = {
            "@context": "https://schema.org",
            "@type": "BlogPosting",
            "headline": post.title,
            "description": post.excerpt,
            "datePublished": post.published_at.isoformat() if post.published_at else None,
            "dateModified": post.updated_at.isoformat(),
            "mainEntityOfPage": absolute(post.get_absolute_url()),
        }
        if site:
            data["author"] = {"@type": "Person", "name": site.name}
            data["publisher"] = {"@type": "Organization", "name": site.company_name or site.brand_name}
        if post.featured_image:
            data["image"] = absolute(post.featured_image.url)
        return {k: v for k, v in data.items() if v is not None}
