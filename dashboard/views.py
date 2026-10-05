"""
The staff dashboard.

A company admin signs in here, sees the state of the pipeline and works on
proposals and enquiries. Deep content editing (pages, projects, team) stays in
the Django admin — this covers the day-to-day commercial work.
"""
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import DetailView, ListView, TemplateView, View

from careers.models import JobApplication
from contact.models import ContactMessage, NewsletterSubscriber, QuoteRequest
from core.models import SiteSettings
from proposals.models import PriceListItem, Proposal, SchoolQuotation

from .access import DashboardAccessMixin
from .forms import (
    AddPriceItemsForm,
    CompanyProfileForm,
    PriceListFormSet,
    QuotationForm,
    QuotationLineFormSet,
    QuotationStartForm,
    ContactStatusForm,
    DashboardLoginForm,
    ProposalForm,
    ProposalItemFormSet,
    ProposalMilestoneFormSet,
    ProposalStartForm,
    QuoteStatusForm,
)


# ---------------------------------------------------------------- auth ----
class DashboardLoginView(auth_views.LoginView):
    template_name = "dashboard/login.html"
    authentication_form = DashboardLoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return self.get_redirect_url() or reverse("dashboard:home")


class DashboardLogoutView(auth_views.LogoutView):
    next_page = reverse_lazy("dashboard:login")


# ----------------------------------------------------------------- home ---
class DashboardHomeView(DashboardAccessMixin, TemplateView):
    template_name = "dashboard/home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = timezone.localdate()
        month_ago = timezone.now() - timedelta(days=30)

        proposals = Proposal.objects.all()
        by_status = {
            row["status"]: row["n"]
            for row in proposals.values("status").annotate(n=Count("id"))
        }

        # Pipeline value counts only what is still open — sent proposals that
        # have not expired. Accepted work is reported separately as won.
        open_proposals = [
            p for p in proposals.filter(status=Proposal.STATUS_SENT)
            if not p.is_expired
        ]
        won = list(proposals.filter(status=Proposal.STATUS_ACCEPTED))

        ctx.update({
            "stat_new_enquiries": ContactMessage.objects.filter(
                status=ContactMessage.STATUS_NEW
            ).count(),
            "stat_open_quotes": QuoteRequest.objects.exclude(
                status__in=["won", "closed"]
            ).count(),
            "stat_applications": JobApplication.objects.count(),
            "stat_subscribers": NewsletterSubscriber.objects.filter(
                unsubscribed_at__isnull=True
            ).count(),
            "proposal_counts": {
                "draft": by_status.get(Proposal.STATUS_DRAFT, 0),
                "sent": by_status.get(Proposal.STATUS_SENT, 0),
                "accepted": by_status.get(Proposal.STATUS_ACCEPTED, 0),
                "declined": by_status.get(Proposal.STATUS_DECLINED, 0),
            },
            "pipeline_total": sum((p.total for p in open_proposals), 0),
            "won_total": sum((p.total for p in won), 0),
            "pipeline_currency": (open_proposals or won or [None])[0].currency_symbol
            if (open_proposals or won) else "",
            "recent_proposals": proposals.select_related("template")[:6],
            "recent_enquiries": ContactMessage.objects.order_by("-created_at")[:6],
            "recent_quotes": QuoteRequest.objects.order_by("-created_at")[:5],
            "expiring_soon": [
                p for p in proposals.filter(
                    status=Proposal.STATUS_SENT,
                    valid_until__isnull=False,
                    valid_until__gte=today,
                    valid_until__lte=today + timedelta(days=7),
                )
            ],
            "new_this_month": proposals.filter(created_at__gte=month_ago).count(),
        })
        return ctx


# ------------------------------------------------------------ proposals ---
class ProposalListView(DashboardAccessMixin, ListView):
    template_name = "dashboard/proposal_list.html"
    context_object_name = "proposals"
    paginate_by = 20
    required_permission = "proposals.view_proposal"

    def get_queryset(self):
        qs = Proposal.objects.select_related("template", "prepared_by")
        self.status = self.request.GET.get("status") or ""
        self.query = (self.request.GET.get("q") or "").strip()
        if self.status:
            qs = qs.filter(status=self.status)
        if self.query:
            qs = qs.filter(
                Q(reference__icontains=self.query)
                | Q(client_organisation__icontains=self.query)
                | Q(client_contact_name__icontains=self.query)
                | Q(title__icontains=self.query)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = Proposal.STATUS_CHOICES
        ctx["active_status"] = self.status
        ctx["query"] = self.query
        return ctx


class ProposalCreateView(DashboardAccessMixin, View):
    """Open a proposal from a template, then hand straight to the editor."""

    required_permission = "proposals.add_proposal"
    template_name = "dashboard/proposal_start.html"

    def get(self, request):
        return render(request, self.template_name, {"form": ProposalStartForm()})

    def post(self, request):
        form = ProposalStartForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})
        proposal = form.save(commit=False)
        proposal.prepared_by = request.user
        proposal.save()
        if proposal.template_id:
            proposal.apply_template()
            messages.success(
                request,
                f"{proposal.reference} created and prefilled from "
                f"“{proposal.template.name}”. Edit the wording and figures below.",
            )
        else:
            messages.success(request, f"{proposal.reference} created.")
        return redirect("dashboard:proposal_edit", pk=proposal.pk)


class ProposalEditView(DashboardAccessMixin, View):
    """The full proposal editor: details, line items and milestones on one page."""

    required_permission = "proposals.change_proposal"
    template_name = "dashboard/proposal_edit.html"

    def get_object(self, pk):
        return get_object_or_404(
            Proposal.objects.prefetch_related("items", "milestones"), pk=pk
        )

    def render_form(self, request, proposal, form=None, items=None, milestones=None):
        return render(request, self.template_name, {
            "proposal": proposal,
            "form": form or ProposalForm(instance=proposal),
            "items": items or ProposalItemFormSet(instance=proposal),
            "milestones": milestones or ProposalMilestoneFormSet(instance=proposal),
        })

    def get(self, request, pk):
        return self.render_form(request, self.get_object(pk))

    def post(self, request, pk):
        proposal = self.get_object(pk)
        form = ProposalForm(request.POST, instance=proposal)
        items = ProposalItemFormSet(request.POST, instance=proposal)
        milestones = ProposalMilestoneFormSet(request.POST, instance=proposal)

        if form.is_valid() and items.is_valid() and milestones.is_valid():
            form.save()
            items.save()
            milestones.save()
            messages.success(request, f"{proposal.reference} saved.")
            if "_download" in request.POST:
                return redirect("proposals:pdf", pk=proposal.pk)
            return redirect("dashboard:proposal_edit", pk=proposal.pk)

        messages.error(request, "Please correct the highlighted fields.")
        return self.render_form(request, proposal, form, items, milestones)


class ProposalStatusView(DashboardAccessMixin, View):
    """Move a proposal through the pipeline from the list or the editor."""

    required_permission = "proposals.change_proposal"

    def post(self, request, pk):
        proposal = get_object_or_404(Proposal, pk=pk)
        status = request.POST.get("status")
        valid = {key for key, _ in Proposal.STATUS_CHOICES}
        if status in valid:
            proposal.status = status
            proposal.save()
            messages.success(
                request, f"{proposal.reference} marked as {proposal.get_status_display().lower()}."
            )
        else:
            messages.error(request, "Unknown status.")
        return redirect(request.POST.get("next") or "dashboard:proposal_list")


# ------------------------------------------------------------ enquiries ---
class EnquiryListView(DashboardAccessMixin, ListView):
    template_name = "dashboard/enquiry_list.html"
    context_object_name = "enquiries"
    paginate_by = 25
    required_permission = "contact.view_contactmessage"

    def get_queryset(self):
        qs = ContactMessage.objects.order_by("-created_at")
        self.status = self.request.GET.get("status") or ""
        if self.status:
            qs = qs.filter(status=self.status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = ContactMessage.STATUS_CHOICES
        ctx["active_status"] = self.status
        return ctx


class EnquiryDetailView(DashboardAccessMixin, DetailView):
    model = ContactMessage
    template_name = "dashboard/enquiry_detail.html"
    context_object_name = "enquiry"
    required_permission = "contact.view_contactmessage"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        # Opening an enquiry is what marks it read; nobody should have to
        # remember to do it by hand.
        if obj.status == ContactMessage.STATUS_NEW:
            obj.status = ContactMessage.STATUS_READ
            obj.save(update_fields=["status"])
        return obj

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form"] = ContactStatusForm(instance=self.object)
        return ctx

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = ContactStatusForm(request.POST, instance=self.object)
        if form.is_valid():
            form.save()
            messages.success(request, "Status updated.")
        return redirect("dashboard:enquiry_detail", pk=self.object.pk)


class QuoteListView(DashboardAccessMixin, ListView):
    template_name = "dashboard/quote_list.html"
    context_object_name = "quotes"
    paginate_by = 25
    required_permission = "contact.view_quoterequest"

    def get_queryset(self):
        return QuoteRequest.objects.order_by("-created_at")


class QuoteDetailView(DashboardAccessMixin, DetailView):
    model = QuoteRequest
    template_name = "dashboard/quote_detail.html"
    context_object_name = "quote"
    required_permission = "contact.view_quoterequest"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form"] = QuoteStatusForm(instance=self.object)
        return ctx

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = QuoteStatusForm(request.POST, instance=self.object)
        if form.is_valid():
            form.save()
            messages.success(request, "Quote request updated.")
        return redirect("dashboard:quote_detail", pk=self.object.pk)


# ------------------------------------------------------- company profile ---
class CompanyProfileView(DashboardAccessMixin, View):
    """
    Edit the company's own details.

    Everything here feeds the public site *and* the proposal letterhead. The
    settings record is cached, but both ``SiteSettings.save()`` and a post_save
    signal drop that cache, so a change is visible on the next request — no
    restart, no waiting for a timeout.
    """

    required_permission = "core.change_sitesettings"
    template_name = "dashboard/company_profile.html"

    def get_settings(self):
        site = SiteSettings.load()
        if site is None:
            # A brand-new installation has no record yet; create one so the
            # form has something to bind to rather than 500ing.
            site = SiteSettings.objects.create(
                name="Company", brand_name="Company",
                professional_title="", short_bio="",
            )
        return site

    def get(self, request):
        site = self.get_settings()
        return render(request, self.template_name, {
            "site_settings": site,
            "form": CompanyProfileForm(instance=site),
        })

    def post(self, request):
        site = self.get_settings()
        form = CompanyProfileForm(request.POST, request.FILES, instance=site)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                "Company profile saved. The website and every new proposal PDF "
                "use these details straight away.",
            )
            return redirect("dashboard:company_profile")
        messages.error(request, "Please correct the highlighted fields.")
        return render(request, self.template_name, {
            "site_settings": site, "form": form,
        })


# ----------------------------------------------------- school quotations ---
class QuotationListView(DashboardAccessMixin, ListView):
    template_name = "dashboard/quotation_list.html"
    context_object_name = "quotations"
    paginate_by = 20
    required_permission = "proposals.view_schoolquotation"

    def get_queryset(self):
        qs = SchoolQuotation.objects.prefetch_related("lines")
        self.status = self.request.GET.get("status") or ""
        self.query = (self.request.GET.get("q") or "").strip()
        if self.status:
            qs = qs.filter(status=self.status)
        if self.query:
            qs = qs.filter(
                Q(reference__icontains=self.query)
                | Q(school_name__icontains=self.query)
                | Q(contact_name__icontains=self.query)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            "status_choices": SchoolQuotation.STATUS_CHOICES,
            "active_status": self.status,
            "query": self.query,
            "unpriced_count": PriceListItem.objects.filter(
                is_active=True, unit_price__lte=0
            ).count(),
        })
        return ctx


class QuotationCreateView(DashboardAccessMixin, View):
    """
    Start a quotation: the school's details and a tick-list of what to include.

    The ticked price-list items become the quotation's lines at today's
    prices. ``?from_request=<id>`` prefills the school from a website quote
    request, so an enquiry becomes a quotation without retyping.
    """

    required_permission = "proposals.add_schoolquotation"
    template_name = "dashboard/quotation_start.html"

    def source_request(self, request):
        pk = request.GET.get("from_request") or request.POST.get("from_request")
        if pk and str(pk).isdigit():
            return QuoteRequest.objects.filter(pk=pk).first()
        return None

    def render_form(self, request, form, source):
        return render(request, self.template_name, {
            "form": form, "source": source,
            "unpriced_count": PriceListItem.objects.filter(
                is_active=True, unit_price__lte=0
            ).count(),
        })

    def get(self, request):
        source = self.source_request(request)
        initial = {}
        if source:
            initial = {
                "school_name": source.organisation,
                "contact_name": source.contact_name,
                "contact_email": source.email,
                "contact_phone": source.phone,
            }
        return self.render_form(request, QuotationStartForm(initial=initial), source)

    def post(self, request):
        source = self.source_request(request)
        form = QuotationStartForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Please correct the highlighted fields.")
            return self.render_form(request, form, source)
        quotation = form.save(commit=False)
        quotation.prepared_by = request.user
        quotation.source_request = source
        quotation.save()
        quotation.add_price_items(form.cleaned_data["items"].order_by(
            "group", "display_order", "name"
        ))
        messages.success(
            request,
            f"{quotation.reference} created for {quotation.school_name}. "
            "Adjust quantities and prices below, then download the PDF.",
        )
        return redirect("dashboard:quotation_edit", pk=quotation.pk)


class QuotationEditView(DashboardAccessMixin, View):
    """The quotation editor: school, lines and terms on one page, with totals."""

    required_permission = "proposals.change_schoolquotation"
    template_name = "dashboard/quotation_edit.html"

    def get_object(self, pk):
        return get_object_or_404(SchoolQuotation.objects.prefetch_related("lines"), pk=pk)

    def render_form(self, request, quotation, form=None, lines=None):
        used = {l.price_item_id for l in quotation.lines.all() if l.price_item_id}
        return render(request, self.template_name, {
            "q": quotation,
            "form": form or QuotationForm(instance=quotation),
            "lines": lines or QuotationLineFormSet(instance=quotation),
            "available_items": PriceListItem.objects.filter(is_active=True).exclude(pk__in=used),
        })

    def get(self, request, pk):
        return self.render_form(request, self.get_object(pk))

    def post(self, request, pk):
        quotation = self.get_object(pk)
        form = QuotationForm(request.POST, instance=quotation)
        lines = QuotationLineFormSet(request.POST, instance=quotation)
        if form.is_valid() and lines.is_valid():
            wants_issue = form.cleaned_data["status"] in (
                SchoolQuotation.STATUS_SENT, SchoolQuotation.STATUS_ACCEPTED
            )
            form.save()
            lines.save()
            quotation = self.get_object(pk)
            problems = quotation.issue_problems
            if wants_issue and problems:
                quotation.status = SchoolQuotation.STATUS_DRAFT
                quotation.save(update_fields=["status"])
                messages.error(
                    request,
                    "Saved, but kept as a draft — it is not ready to send. " + " ".join(problems),
                )
                return redirect("dashboard:quotation_edit", pk=pk)
            messages.success(request, f"{quotation.reference} saved.")
            if "_download" in request.POST:
                return redirect("proposals:quotation_pdf", pk=pk)
            return redirect("dashboard:quotation_edit", pk=pk)
        messages.error(request, "Please correct the highlighted fields.")
        return self.render_form(request, quotation, form, lines)


class QuotationAddItemsView(DashboardAccessMixin, View):
    required_permission = "proposals.change_schoolquotation"

    def post(self, request, pk):
        quotation = get_object_or_404(SchoolQuotation, pk=pk)
        form = AddPriceItemsForm(request.POST)
        if form.is_valid():
            items = form.cleaned_data["items"].order_by("group", "display_order", "name")
            quotation.add_price_items(items)
            messages.success(request, f"Added {items.count()} line(s) at current prices.")
        else:
            messages.error(request, "Tick at least one item to add.")
        return redirect("dashboard:quotation_edit", pk=pk)


class QuotationStatusView(DashboardAccessMixin, View):
    """Move a quotation along; refuses to mark one sent while it is incomplete."""

    required_permission = "proposals.change_schoolquotation"

    def post(self, request, pk):
        quotation = get_object_or_404(
            SchoolQuotation.objects.prefetch_related("lines"), pk=pk
        )
        status = request.POST.get("status")
        if status not in {key for key, _ in SchoolQuotation.STATUS_CHOICES}:
            messages.error(request, "Unknown status.")
        elif status in (SchoolQuotation.STATUS_SENT, SchoolQuotation.STATUS_ACCEPTED) \
                and quotation.issue_problems:
            messages.error(
                request, f"{quotation.reference} is not ready to send. "
                + " ".join(quotation.issue_problems),
            )
        else:
            quotation.status = status
            quotation.save()
            messages.success(
                request,
                f"{quotation.reference} marked as {quotation.get_status_display().lower()}.",
            )
        return redirect(request.POST.get("next") or "dashboard:quotation_list")


class QuotationDuplicateView(DashboardAccessMixin, View):
    """Copy a quotation — e.g. a revised offer — as a new draft with its own reference."""

    required_permission = "proposals.add_schoolquotation"

    def post(self, request, pk):
        original = get_object_or_404(SchoolQuotation.objects.prefetch_related("lines"), pk=pk)
        lines = list(original.lines.all())
        copy = original
        copy.pk = None
        copy.reference = ""
        copy.status = SchoolQuotation.STATUS_DRAFT
        copy.sent_at = None
        copy.valid_until = None
        copy.prepared_by = request.user
        copy._state.adding = True
        copy.save()
        for line in lines:
            line.pk = None
            line.quotation = copy
        copy.lines.model.objects.bulk_create(lines)
        messages.success(request, f"Copied to {copy.reference}. The original is unchanged.")
        return redirect("dashboard:quotation_edit", pk=copy.pk)


class PriceListView(DashboardAccessMixin, View):
    """Every price on one page. Changes affect new quotation lines only."""

    required_permission = "proposals.change_pricelistitem"
    template_name = "dashboard/price_list.html"

    def render_form(self, request, formset=None):
        return render(request, self.template_name, {
            "formset": formset or PriceListFormSet(queryset=PriceListItem.objects.all()),
        })

    def get(self, request):
        return self.render_form(request)

    def post(self, request):
        formset = PriceListFormSet(request.POST, queryset=PriceListItem.objects.all())
        if formset.is_valid():
            formset.save()
            messages.success(
                request,
                "Price list saved. New quotation lines use these prices; quotations "
                "already written keep the prices they were given.",
            )
            return redirect("dashboard:price_list")
        messages.error(request, "Please correct the highlighted rows.")
        return self.render_form(request, formset)
