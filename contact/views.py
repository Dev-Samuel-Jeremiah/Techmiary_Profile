import logging

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.core.mail import send_mail
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.views.generic.edit import CreateView

from core.seo import SEOMixin, breadcrumb_schema

from .forms import ContactForm, NewsletterForm, QuoteRequestForm
from .models import ContactMessage, NewsletterSubscriber, QuoteRequest

logger = logging.getLogger(__name__)


def client_ip(request):
    """
    The caller's IP, used as the rate-limit bucket.

    ``X-Forwarded-For`` is set by the client and only appended to by each
    proxy, so the left-hand entries are attacker-controlled: reading the first
    one lets anyone mint a fresh identity per request and walk straight past
    the rate limit. Only the entries a trusted proxy appended can be believed,
    so we count ``TRUSTED_PROXY_COUNT`` hops in from the right.

    With the shipped nginx config (``$proxy_add_x_forwarded_for``) there is one
    such hop, so set ``TRUSTED_PROXY_COUNT=1``. The default of 0 means the
    header is ignored entirely and ``REMOTE_ADDR`` is used.
    """
    hops = getattr(settings, "TRUSTED_PROXY_COUNT", 0)
    if hops > 0:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        chain = [part.strip() for part in forwarded.split(",") if part.strip()]
        if len(chain) >= hops:
            return chain[-hops]
    return request.META.get("REMOTE_ADDR")


class ContactView(SEOMixin, CreateView):
    model = ContactMessage
    form_class = ContactForm
    template_name = "contact/contact.html"
    success_url = reverse_lazy("contact:contact")

    def get_meta_title(self, context):
        site = context.get("site")
        return f"Contact — {site.name}" if site else "Contact"

    def get_meta_description(self, context):
        return (
            "Start a conversation about a custom application, SaaS platform, "
            "school management system or an integration project."
        )

    def get_structured_data(self, context):
        return breadcrumb_schema([("Home", "/"), ("Contact", "/contact/")])

    # -- rate limiting -----------------------------------------------------
    def rate_limit_key(self):
        return f"contact:rate:{client_ip(self.request)}"

    def is_rate_limited(self):
        count = cache.get(self.rate_limit_key(), 0)
        return count >= settings.CONTACT_RATE_LIMIT

    def register_submission(self):
        key = self.rate_limit_key()
        count = cache.get(key, 0) + 1
        cache.set(key, count, settings.CONTACT_RATE_WINDOW_SECONDS)

    def form_valid(self, form):
        if self.is_rate_limited():
            messages.error(
                self.request,
                "You have sent several messages recently. Please try again later.",
            )
            return self.render_to_response(self.get_context_data(form=form))

        form.instance.ip_address = client_ip(self.request)
        form.instance.user_agent = self.request.META.get("HTTP_USER_AGENT", "")[:300]
        response = super().form_valid(form)
        self.register_submission()
        self.notify(self.object)
        messages.success(
            self.request,
            "Thank you — your message has been received. You will get a reply by email.",
        )
        return response

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the highlighted fields.")
        return super().form_invalid(form)

    def notify(self, message):
        recipient = settings.CONTACT_NOTIFICATION_EMAIL
        if not recipient:
            return
        try:
            send_mail(
                subject=f"[Portfolio] {message.subject}",
                message=(
                    f"From: {message.name} <{message.email}>\n"
                    f"Phone: {message.phone or '-'}\n"
                    f"Company: {message.company or '-'}\n\n"
                    f"{message.message}"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                fail_silently=True,
            )
        except Exception:  # pragma: no cover - notification must never break the form
            logger.exception("Could not send contact notification email")


class QuoteRequestView(SEOMixin, CreateView):
    """Structured project enquiry, presented as three steps in the template."""

    model = QuoteRequest
    form_class = QuoteRequestForm
    template_name = "contact/quote.html"
    success_url = reverse_lazy("contact:quote")

    def get_initial(self):
        initial = super().get_initial()
        solution_slug = self.request.GET.get("solution")
        service_slug = self.request.GET.get("service")
        if solution_slug:
            from company.models import Solution

            solution = Solution.objects.filter(slug=solution_slug, is_active=True).first()
            if solution:
                initial["solution"] = solution
        if service_slug:
            from services.models import Service

            service = Service.objects.filter(slug=service_slug, is_active=True).first()
            if service:
                initial["service"] = service
        return initial

    def get_meta_title(self, context):
        site = context.get("site")
        return f"Request a Quote — {site.display_company}" if site else "Request a Quote"

    def get_meta_description(self, context):
        return (
            "Tell us what you need built, the budget range you are working to and when "
            "you need it live. You get a scoped response, not a sales call."
        )

    def get_structured_data(self, context):
        return breadcrumb_schema([("Home", "/"), ("Request a Quote", "/quote/")])

    def rate_limit_key(self):
        return f"quote:rate:{client_ip(self.request)}"

    def form_valid(self, form):
        count = cache.get(self.rate_limit_key(), 0)
        if count >= settings.CONTACT_RATE_LIMIT:
            messages.error(
                self.request,
                "You have sent several requests recently. Please try again later.",
            )
            return self.render_to_response(self.get_context_data(form=form))

        form.instance.ip_address = client_ip(self.request)
        response = super().form_valid(form)
        cache.set(self.rate_limit_key(), count + 1, settings.CONTACT_RATE_WINDOW_SECONDS)
        self.notify(self.object)
        messages.success(
            self.request,
            "Thank you — your request has been received. You will get a scoped response by email.",
        )
        return response

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the highlighted fields.")
        return super().form_invalid(form)

    def notify(self, quote):
        recipient = settings.CONTACT_NOTIFICATION_EMAIL
        if not recipient:
            return
        try:
            send_mail(
                subject=f"[Quote request] {quote.project_title}",
                message=(
                    f"From: {quote.contact_name} <{quote.email}>\n"
                    f"Organisation: {quote.organisation or '-'} ({quote.get_organisation_type_display()})\n"
                    f"Phone: {quote.phone or '-'}\n"
                    f"Interested in: {quote.requested_for}\n"
                    f"Budget: {quote.get_budget_range_display()}\n"
                    f"Timeline: {quote.get_timeline_display()}\n"
                    f"Replacing an existing system: {'yes' if quote.existing_system else 'no'}\n\n"
                    f"{quote.description}"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                fail_silently=True,
            )
        except Exception:  # pragma: no cover - notification must never break the form
            logger.exception("Could not send quote notification email")


@require_POST
def newsletter_subscribe(request):
    """
    Handle the footer newsletter form.

    Re-submitting an address that already exists reactivates it rather than
    raising a duplicate error at the visitor.
    """
    form = NewsletterForm(request.POST)
    redirect_to = request.POST.get("next") or request.META.get("HTTP_REFERER") or "/"
    if not url_has_allowed_host_and_scheme(
        redirect_to, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        redirect_to = "/"

    if form.is_valid():
        email = form.cleaned_data["email"].lower()
        subscriber, created = NewsletterSubscriber.objects.get_or_create(
            email=email,
            defaults={
                "name": form.cleaned_data.get("name", ""),
                "source": request.POST.get("source", "footer"),
                "ip_address": client_ip(request),
            },
        )
        if not created and not subscriber.is_active:
            subscriber.is_active = True
            subscriber.unsubscribed_at = None
            subscriber.save(update_fields=["is_active", "unsubscribed_at"])
        messages.success(request, "You are subscribed. Thank you.")
    else:
        messages.error(request, "Please enter a valid email address.")
    return redirect(redirect_to)
