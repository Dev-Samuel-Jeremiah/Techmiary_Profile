"""Admin control panel for building and issuing proposals."""
from django.contrib import admin, messages
from django.db.models import Count
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import (
    Proposal,
    ProposalItem,
    ProposalMilestone,
    ProposalTemplate,
    TemplateItem,
)


class TemplateItemInline(admin.TabularInline):
    model = TemplateItem
    extra = 1
    fields = ("display_order", "title", "description", "quantity", "unit", "unit_price")
    ordering = ("display_order",)


@admin.register(ProposalTemplate)
class ProposalTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "solution", "item_count", "default_timeline_weeks", "is_active")
    list_filter = ("is_active", "solution")
    list_editable = ("is_active",)
    search_fields = ("name", "summary")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [TemplateItemInline]
    fieldsets = (
        (None, {"fields": ("name", "slug", "solution", "summary", "is_active", "display_order")}),
        ("Standard wording", {
            "fields": ("background", "approach", "assumptions", "exclusions", "payment_terms"),
            "description": "Copied onto a new proposal, then edited for that client.",
        }),
        ("Defaults", {"fields": ("default_timeline_weeks", "default_validity_days")}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_items=Count("items"))

    @admin.display(description="Line items", ordering="_items")
    def item_count(self, obj):
        return obj._items


class ProposalItemInline(admin.TabularInline):
    model = ProposalItem
    extra = 1
    fields = ("display_order", "title", "description", "quantity", "unit", "unit_price", "line_total_display")
    readonly_fields = ("line_total_display",)
    ordering = ("display_order",)

    @admin.display(description="Line total")
    def line_total_display(self, obj):
        if obj.pk is None:
            return "—"
        return f"{obj.proposal.currency_symbol}{obj.line_total:,.2f}"


class ProposalMilestoneInline(admin.TabularInline):
    model = ProposalMilestone
    extra = 0
    fields = ("display_order", "name", "description", "week_from", "week_to", "percent_of_fee")
    ordering = ("display_order",)


@admin.register(Proposal)
class ProposalAdmin(admin.ModelAdmin):
    list_display = (
        "reference", "client_organisation", "title",
        "total_display", "status_badge", "valid_until", "download_link",
    )
    list_filter = ("status", "currency", "template", "created_at")
    search_fields = (
        "reference", "client_organisation", "client_contact_name",
        "client_email", "title",
    )
    date_hierarchy = "created_at"
    inlines = [ProposalItemInline, ProposalMilestoneInline]
    autocomplete_fields = ()
    readonly_fields = ("reference", "created_at", "updated_at", "sent_at", "totals_panel")
    actions = ("mark_sent", "mark_accepted", "duplicate_proposal")

    fieldsets = (
        ("Start here", {
            "fields": ("template", "reference", "status", "prepared_by"),
            "description": (
                "Pick a template to prefill the scope and line items, save, then edit. "
                "The reference is generated automatically."
            ),
        }),
        ("Client", {
            "fields": (
                "client_organisation", "client_contact_name", "client_role",
                "client_email", "client_phone", "client_address",
            ),
        }),
        ("The engagement", {
            "fields": ("title", "summary", "background", "approach"),
        }),
        ("Scope boundaries", {
            "fields": ("assumptions", "exclusions"),
            "classes": ("collapse",),
            "description": "One per line. Both appear as bulleted lists in the PDF.",
        }),
        ("Commercials", {
            "fields": (
                "currency", "discount_percent", "tax_percent",
                "deposit_percent", "payment_terms", "totals_panel",
            ),
        }),
        ("Timing", {"fields": ("timeline_weeks", "start_estimate", "valid_until")}),
        ("Internal", {
            "fields": ("notes", "created_at", "updated_at", "sent_at"),
            "classes": ("collapse",),
            "description": "Notes are never included in the PDF.",
        }),
    )

    class Media:
        css = {"all": ("admin/proposals.css",)}

    # -- computed columns --------------------------------------------------
    @admin.display(description="Total", ordering="id")
    def total_display(self, obj):
        return f"{obj.currency_symbol}{obj.total:,.2f}"

    @admin.display(description="Status")
    def status_badge(self, obj):
        colours = {
            obj.STATUS_DRAFT: "#64748b",
            obj.STATUS_SENT: "#1b4dff",
            obj.STATUS_ACCEPTED: "#0e9f6e",
            obj.STATUS_DECLINED: "#dc2626",
            obj.STATUS_EXPIRED: "#b45309",
        }
        label = obj.get_status_display()
        if obj.is_expired and obj.status in (obj.STATUS_DRAFT, obj.STATUS_SENT):
            label, colour = "Expired", colours[obj.STATUS_EXPIRED]
        else:
            colour = colours.get(obj.status, "#64748b")
        return format_html(
            '<span style="display:inline-block;padding:2px 10px;border-radius:999px;'
            'font-size:11px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;'
            'color:#fff;background:{}">{}</span>',
            colour, label,
        )

    @admin.display(description="PDF")
    def download_link(self, obj):
        if obj.pk is None:
            return "—"
        return format_html(
            '<a class="button" style="white-space:nowrap" href="{}" target="_blank">Download</a>',
            reverse("proposals:pdf", kwargs={"pk": obj.pk}),
        )

    @admin.display(description="Totals")
    def totals_panel(self, obj):
        """A live summary so the figures are visible without opening the PDF."""
        if obj.pk is None:
            return mark_safe("<em>Save the proposal to see totals.</em>")
        s = obj.currency_symbol
        rows = [
            ("Subtotal", f"{s}{obj.subtotal:,.2f}", False),
            (f"Discount ({obj.discount_percent}%)", f"−{s}{obj.discount_amount:,.2f}", False),
            ("Net", f"{s}{obj.net_total:,.2f}", False),
            (f"Tax ({obj.tax_percent}%)", f"{s}{obj.tax_amount:,.2f}", False),
            ("Total", f"{s}{obj.total:,.2f}", True),
            (f"Deposit ({obj.deposit_percent}%)", f"{s}{obj.deposit_amount:,.2f}", False),
            ("Balance", f"{s}{obj.balance_amount:,.2f}", False),
        ]
        html = ['<table class="proposal-totals">']
        for label, value, strong in rows:
            tag = "strong" if strong else "span"
            html.append(
                f"<tr><th>{label}</th><td><{tag}>{value}</{tag}></td></tr>"
            )
        html.append("</table>")
        return mark_safe("".join(html))

    # -- behaviour ---------------------------------------------------------
    def save_model(self, request, obj, form, change):
        if obj.prepared_by_id is None:
            obj.prepared_by = request.user
        super().save_model(request, obj, form, change)
        # Applying the template after the first save means the proposal has a
        # primary key, so its line items can be attached.
        if not change and obj.template_id:
            obj.apply_template()
            self.message_user(
                request,
                f"Prefilled from the “{obj.template.name}” template. Edit the wording "
                "and line items, then use Download to issue the PDF.",
                messages.INFO,
            )

    def response_change(self, request, obj):
        if "_download_pdf" in request.POST:
            return HttpResponseRedirect(reverse("proposals:pdf", kwargs={"pk": obj.pk}))
        return super().response_change(request, obj)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["show_download_pdf"] = True
        return super().change_view(request, object_id, form_url, extra_context)

    # -- actions -----------------------------------------------------------
    @admin.action(description="Mark selected as sent")
    def mark_sent(self, request, queryset):
        n = 0
        for p in queryset:
            p.status = Proposal.STATUS_SENT
            p.save()
            n += 1
        self.message_user(request, f"{n} proposal(s) marked as sent.", messages.SUCCESS)

    @admin.action(description="Mark selected as accepted")
    def mark_accepted(self, request, queryset):
        n = queryset.update(status=Proposal.STATUS_ACCEPTED)
        self.message_user(request, f"{n} proposal(s) marked as accepted.", messages.SUCCESS)

    @admin.action(description="Duplicate selected (as new drafts)")
    def duplicate_proposal(self, request, queryset):
        made = 0
        for original in queryset:
            items = list(original.items.all())
            milestones = list(original.milestones.all())
            original.pk = None
            original.reference = ""
            original.status = Proposal.STATUS_DRAFT
            original.sent_at = None
            original.save()
            ProposalItem.objects.bulk_create([
                ProposalItem(
                    proposal=original, title=i.title, description=i.description,
                    quantity=i.quantity, unit=i.unit, unit_price=i.unit_price,
                    display_order=i.display_order,
                ) for i in items
            ])
            ProposalMilestone.objects.bulk_create([
                ProposalMilestone(
                    proposal=original, name=m.name, description=m.description,
                    week_from=m.week_from, week_to=m.week_to,
                    percent_of_fee=m.percent_of_fee, display_order=m.display_order,
                ) for m in milestones
            ])
            made += 1
        self.message_user(request, f"{made} draft(s) created.", messages.SUCCESS)
