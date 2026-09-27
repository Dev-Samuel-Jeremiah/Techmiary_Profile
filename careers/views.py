from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import DetailView, ListView
from django.views.generic.edit import CreateView

from contact.views import client_ip
from core.seo import SEOMixin, absolute, breadcrumb_schema

from .forms import JobApplicationForm
from .models import Department, JobOpening


class JobListView(SEOMixin, ListView):
    template_name = "careers/job_list.html"
    context_object_name = "jobs"

    def get_queryset(self):
        queryset = JobOpening.open_roles.all()
        self.active_department = None
        slug = self.request.GET.get("department")
        if slug:
            self.active_department = Department.objects.filter(slug=slug).first()
            if self.active_department:
                queryset = queryset.filter(department=self.active_department)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["departments"] = Department.objects.filter(
            openings__is_published=True, openings__status=JobOpening.STATUS_OPEN
        ).distinct()
        context["active_department"] = self.active_department
        context["total_open"] = JobOpening.open_roles.count()
        return context

    def get_meta_title(self, context):
        site = context.get("site")
        return f"Careers — {site.display_company}" if site else "Careers"

    def get_meta_description(self, context):
        return (
            "Open roles at the company: engineering, delivery and support positions "
            "building software that organisations depend on."
        )

    def get_structured_data(self, context):
        return breadcrumb_schema([("Home", "/"), ("Careers", "/careers/")])


class JobDetailView(SEOMixin, DetailView):
    template_name = "careers/job_detail.html"
    context_object_name = "job"

    def get_queryset(self):
        return JobOpening.objects.filter(is_published=True).select_related("department")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("form", JobApplicationForm())
        context["other_jobs"] = (
            JobOpening.open_roles.exclude(pk=self.object.pk)[:3]
        )
        return context

    def get_meta_title(self, context):
        return self.object.resolved_meta_title

    def get_meta_description(self, context):
        return self.object.resolved_meta_description

    def get_structured_data(self, context):
        job = self.object
        site = context.get("site")
        data = {
            "@context": "https://schema.org",
            "@type": "JobPosting",
            "title": job.title,
            "description": job.description,
            "employmentType": job.get_employment_type_display().upper().replace(" ", "_"),
            "url": absolute(job.get_absolute_url()),
        }
        if job.posted_at:
            data["datePosted"] = job.posted_at.isoformat()
        if job.closes_at:
            data["validThrough"] = job.closes_at.isoformat()
        if site:
            data["hiringOrganization"] = {
                "@type": "Organization",
                "name": site.display_company,
                **({"sameAs": site.website_url} if site.website_url else {}),
            }
        if job.location:
            data["jobLocation"] = {
                "@type": "Place",
                "address": {"@type": "PostalAddress", "addressLocality": job.location},
            }
        return data


class JobApplyView(SEOMixin, CreateView):
    """Handles the POST from the application form on the job detail page."""

    form_class = JobApplicationForm
    template_name = "careers/job_detail.html"

    def dispatch(self, request, *args, **kwargs):
        self.job = get_object_or_404(
            JobOpening.objects.select_related("department"),
            slug=kwargs["slug"],
            is_published=True,
        )
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return redirect(self.job.get_absolute_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["job"] = self.job
        context["object"] = self.job
        context["other_jobs"] = JobOpening.open_roles.exclude(pk=self.job.pk)[:3]
        context["meta_title"] = self.job.resolved_meta_title
        context["meta_description"] = self.job.resolved_meta_description
        context["canonical_url"] = absolute(self.job.get_absolute_url())
        return context

    def form_valid(self, form):
        if not self.job.is_accepting_applications:
            messages.error(self.request, "This role is no longer accepting applications.")
            return redirect(self.job.get_absolute_url())
        form.instance.job = self.job
        # Reuse the proxy-aware helper rather than trusting the left-hand
        # entry of X-Forwarded-For, which the caller controls.
        form.instance.ip_address = client_ip(self.request)
        response = super().form_valid(form)
        messages.success(
            self.request,
            "Thank you — your application has been received. We reply to every applicant.",
        )
        return response

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the highlighted fields and try again.")
        return super().form_invalid(form)

    def get_success_url(self):
        return self.job.get_absolute_url()
