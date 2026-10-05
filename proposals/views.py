"""Rendering a proposal as a PDF on the company letterhead."""
import logging
from pathlib import Path

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.utils.text import slugify

from core.models import SiteSettings

from .models import Proposal, SchoolQuotation

logger = logging.getLogger(__name__)


def _local_file_uri(filefield):
    """
    A ``file://`` URI for an image, so WeasyPrint reads it from disk.

    Given only a URL, WeasyPrint fetches it over HTTP — the server making a
    request to itself, which is slow, fails when the host is unreachable from
    inside the box, and cannot pass through authentication. Local storage can
    be read directly; remote storage (S3 and friends) has no local path, so
    those fall back to the URL.
    """
    if not filefield:
        return ""
    try:
        return Path(filefield.path).as_uri()
    except (NotImplementedError, ValueError, AttributeError):
        try:
            return filefield.url
        except Exception:
            return ""


@staff_member_required
def proposal_pdf(request, pk):
    """
    Render one proposal to PDF.

    Staff-only: a proposal carries a client's contact details and commercial
    terms, so it is never served from a public URL.
    """
    proposal = get_object_or_404(
        Proposal.objects.select_related("template", "prepared_by")
        .prefetch_related("items", "milestones"),
        pk=pk,
    )
    # An unsaved, empty profile rather than None, so a fresh install still renders.
    site = SiteSettings.load() or SiteSettings()

    html = render_to_string(
        "proposals/proposal_pdf.html",
        {
            "proposal": proposal,
            "site": site,
            "logo_src": _local_file_uri(getattr(site, "logo", None)),
            "items": proposal.items.all(),
            "milestones": proposal.milestones.all(),
        },
        request=request,
    )

    org = slugify(proposal.client_organisation) or "client"
    return _pdf_response(request, html, f"{proposal.reference}-{org}.pdf")


def _pdf_response(request, html, filename):
    """Render letterhead HTML to a PDF response, or explain why it cannot."""
    try:
        from weasyprint import HTML
    except ImportError:  # pragma: no cover - depends on the deployment
        logger.exception("WeasyPrint is not installed; cannot render PDFs")
        return HttpResponse(
            "PDF rendering is unavailable on this server: WeasyPrint is not installed. "
            "Run `pip install -r requirements.txt` and restart.",
            status=503,
            content_type="text/plain",
        )

    # base_url lets WeasyPrint resolve the logo and stylesheet by URL.
    pdf = HTML(string=html, base_url=request.build_absolute_uri("/")).write_pdf()
    response = HttpResponse(pdf, content_type="application/pdf")
    # `inline` opens in the browser's viewer; the browser offers the download.
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    return response


@staff_member_required
def quotation_pdf(request, pk):
    """
    Render one school quotation to PDF.

    Staff-only for the same reason as proposals: it carries a school's
    contact details and prices.
    """
    quotation = get_object_or_404(
        SchoolQuotation.objects.select_related("prepared_by").prefetch_related("lines"),
        pk=pk,
    )
    # An unsaved, empty profile rather than None, so a fresh install still renders.
    site = SiteSettings.load() or SiteSettings()
    html = render_to_string(
        "proposals/quotation_pdf.html",
        {
            "q": quotation,
            "site": site,
            "logo_src": _local_file_uri(getattr(site, "logo", None)),
        },
        request=request,
    )
    school = slugify(quotation.school_name) or "school"
    return _pdf_response(request, html, f"{quotation.reference}-{school}.pdf")
