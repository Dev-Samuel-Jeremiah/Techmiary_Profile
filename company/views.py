"""Solutions, industries, team, clients, resources and the FAQ."""
from django.db.models import Count, Q
from django.views.generic import DetailView, ListView, TemplateView

from core.seo import SEOMixin, absolute, breadcrumb_schema

from .models import (
    FAQ,
    Client,
    FAQCategory,
    Industry,
    Resource,
    ResourceCategory,
    Solution,
    TeamMember,
    Testimonial,
)


class SolutionListView(SEOMixin, ListView):
    template_name = "company/solution_list.html"
    context_object_name = "solutions"

    def get_queryset(self):
        return (
            Solution.objects.active()
            .prefetch_related("industries", "capabilities")
            .select_related("related_project")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["industries"] = Industry.objects.active()
        return context

    def get_meta_title(self, context):
        site = context.get("site")
        return f"Solutions — {site.display_company}" if site else "Solutions"

    def get_meta_description(self, context):
        return (
            "Platforms built and maintained by the company: school ERP, learning "
            "systems and business information systems, deployable for your organisation."
        )

    def get_structured_data(self, context):
        return breadcrumb_schema([("Home", "/"), ("Solutions", "/solutions/")])


class SolutionDetailView(SEOMixin, DetailView):
    template_name = "company/solution_detail.html"
    context_object_name = "solution"

    def get_queryset(self):
        return (
            Solution.objects.active()
            .prefetch_related("industries", "capabilities")
            .select_related("related_project")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["other_solutions"] = (
            Solution.objects.active().exclude(pk=self.object.pk).prefetch_related("industries")[:3]
        )
        return context

    def get_meta_title(self, context):
        return self.object.resolved_meta_title

    def get_meta_description(self, context):
        return self.object.resolved_meta_description

    def get_structured_data(self, context):
        solution = self.object
        site = context.get("site")
        data = {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": solution.name,
            "description": solution.summary,
            "url": absolute(solution.get_absolute_url()),
            "category": "Software",
        }
        if site:
            data["brand"] = {"@type": "Brand", "name": site.display_company}
        if solution.hero_image:
            data["image"] = absolute(solution.hero_image.url)
        return data


class IndustryListView(SEOMixin, ListView):
    template_name = "company/industry_list.html"
    context_object_name = "industries"

    def get_queryset(self):
        return Industry.objects.active().prefetch_related("solutions")

    def get_meta_title(self, context):
        site = context.get("site")
        return f"Industries — {site.display_company}" if site else "Industries"

    def get_meta_description(self, context):
        return (
            "The sectors the company builds for, the problems each one brings and "
            "the systems built to address them."
        )

    def get_structured_data(self, context):
        return breadcrumb_schema([("Home", "/"), ("Industries", "/industries/")])


class IndustryDetailView(SEOMixin, DetailView):
    template_name = "company/industry_detail.html"
    context_object_name = "industry"

    def get_queryset(self):
        return Industry.objects.active().prefetch_related("solutions", "clients")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["clients"] = self.object.clients.filter(is_active=True)
        context["other_industries"] = Industry.objects.active().exclude(pk=self.object.pk)[:4]
        return context

    def get_meta_title(self, context):
        return f"{self.object.name} — Industries"

    def get_meta_description(self, context):
        return (self.object.tagline or self.object.summary)[:180]

    def get_structured_data(self, context):
        return breadcrumb_schema(
            [("Home", "/"), ("Industries", "/industries/"), (self.object.name, self.object.get_absolute_url())]
        )


class TeamListView(SEOMixin, ListView):
    template_name = "company/team_list.html"
    context_object_name = "members"

    def get_queryset(self):
        return TeamMember.objects.active()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        members = list(context["members"])
        context["leadership"] = [m for m in members if m.is_leadership]
        context["team"] = [m for m in members if not m.is_leadership]
        return context

    def get_meta_title(self, context):
        site = context.get("site")
        return f"Leadership & Team — {site.display_company}" if site else "Team"

    def get_meta_description(self, context):
        return "The people who design, build and support the company's software."

    def get_structured_data(self, context):
        return breadcrumb_schema([("Home", "/"), ("Team", "/team/")])


class TeamDetailView(SEOMixin, DetailView):
    template_name = "company/team_detail.html"
    context_object_name = "member"

    def get_queryset(self):
        return TeamMember.objects.active()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.object.is_founder:
            from experience.models import Experience

            context["experiences"] = list(
                Experience.objects.filter(is_active=True).prefetch_related("responsibilities")
            )
        context["colleagues"] = TeamMember.objects.active().exclude(pk=self.object.pk)[:3]
        return context

    def get_meta_title(self, context):
        return f"{self.object.name} — {self.object.role}"

    def get_meta_description(self, context):
        return (self.object.short_bio or self.object.bio)[:180]

    def get_structured_data(self, context):
        member = self.object
        site = context.get("site")
        data = {
            "@context": "https://schema.org",
            "@type": "Person",
            "name": member.name,
            "jobTitle": member.role,
            "url": absolute(member.get_absolute_url()),
        }
        if site and site.display_company:
            data["worksFor"] = {"@type": "Organization", "name": site.display_company}
        same_as = [u for u in (member.linkedin_url, member.github_url, member.twitter_url) if u]
        if same_as:
            data["sameAs"] = same_as
        if member.photo:
            data["image"] = absolute(member.photo.url)
        return data


class ResourceListView(SEOMixin, ListView):
    template_name = "company/resource_list.html"
    context_object_name = "resources"

    def get_queryset(self):
        queryset = Resource.objects.active().select_related("category")
        self.active_category = None
        slug = self.request.GET.get("category")
        if slug:
            self.active_category = ResourceCategory.objects.filter(slug=slug).first()
            if self.active_category:
                queryset = queryset.filter(category=self.active_category)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = ResourceCategory.objects.annotate(
            total=Count("resources", filter=Q(resources__is_active=True))
        ).filter(total__gt=0)
        context["active_category"] = self.active_category
        return context

    def get_meta_title(self, context):
        site = context.get("site")
        return f"Resources — {site.display_company}" if site else "Resources"

    def get_meta_description(self, context):
        return "Guides, checklists and documents on planning, building and running business software."

    def get_structured_data(self, context):
        return breadcrumb_schema([("Home", "/"), ("Resources", "/resources/")])


class FAQView(SEOMixin, TemplateView):
    template_name = "company/faq.html"

    @property
    def faq_groups(self):
        """Active questions grouped by category, computed once per request.

        The SEO mixin builds structured data while assembling the context, so
        the grouping has to be available to both without running twice.
        """
        if hasattr(self, "_faq_groups"):
            return self._faq_groups

        query = (self.request.GET.get("q") or "").strip()
        faqs = FAQ.objects.active().select_related("category")
        if query:
            faqs = faqs.filter(Q(question__icontains=query) | Q(answer__icontains=query))
        faqs = list(faqs)

        grouped = []
        for category in FAQCategory.objects.all():
            items = [f for f in faqs if f.category_id == category.pk]
            if items:
                grouped.append((category, items))
        uncategorised = [f for f in faqs if f.category_id is None]
        if uncategorised:
            grouped.append((None, uncategorised))

        self._faq_query = query
        self._faq_flat = faqs
        self._faq_groups = grouped
        return grouped

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["grouped_faqs"] = self.faq_groups
        context["faq_total"] = len(self._faq_flat)
        context["query"] = self._faq_query
        return context

    def get_meta_title(self, context):
        site = context.get("site")
        return f"Frequently Asked Questions — {site.display_company}" if site else "FAQ"

    def get_meta_description(self, context):
        return "Answers on how projects are scoped, built, priced, deployed and supported."

    def get_structured_data(self, context):
        faqs = [item for _, items in self.faq_groups for item in items]
        if not faqs:
            return breadcrumb_schema([("Home", "/"), ("FAQ", "/faq/")])
        return {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": faq.question,
                    "acceptedAnswer": {"@type": "Answer", "text": faq.answer},
                }
                for faq in faqs
            ],
        }


class ClientListView(SEOMixin, ListView):
    template_name = "company/client_list.html"
    context_object_name = "clients"

    def get_queryset(self):
        return Client.objects.active().select_related("industry")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["testimonials"] = Testimonial.objects.active().select_related("client")
        return context

    def get_meta_title(self, context):
        site = context.get("site")
        return f"Clients — {site.display_company}" if site else "Clients"

    def get_meta_description(self, context):
        return "Organisations the company has delivered software for, and what they say about the work."

    def get_structured_data(self, context):
        return breadcrumb_schema([("Home", "/"), ("Clients", "/clients/")])
