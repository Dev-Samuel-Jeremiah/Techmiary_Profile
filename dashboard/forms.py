"""Forms used by the staff dashboard."""
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.forms import inlineformset_factory, modelformset_factory

from contact.models import ContactMessage, QuoteRequest
from core.models import SiteSettings
from proposals.models import (
    PriceListItem,
    Proposal,
    ProposalItem,
    ProposalMilestone,
    SchoolQuotation,
    SchoolQuotationLine,
)


class DashboardLoginForm(AuthenticationForm):
    """Branded sign-in. Styling only — the authentication logic is Django's."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {"class": "dash-input", "placeholder": "Username", "autofocus": True,
             "autocomplete": "username"}
        )
        self.fields["password"].widget.attrs.update(
            {"class": "dash-input", "placeholder": "Password",
             "autocomplete": "current-password"}
        )

    def confirm_login_allowed(self, user):
        """
        Reject non-staff at the form, so the message is about access rather
        than a redirect to a page they cannot open.
        """
        super().confirm_login_allowed(user)
        if not user.is_staff:
            raise forms.ValidationError(
                "This account does not have dashboard access.", code="no_dashboard",
            )


TEXT_WIDGETS = {
    "background": forms.Textarea(attrs={"rows": 5}),
    "approach": forms.Textarea(attrs={"rows": 6}),
    "assumptions": forms.Textarea(attrs={"rows": 4}),
    "exclusions": forms.Textarea(attrs={"rows": 4}),
    "payment_terms": forms.Textarea(attrs={"rows": 4}),
    "client_address": forms.Textarea(attrs={"rows": 3}),
    "notes": forms.Textarea(attrs={"rows": 3}),
}


class ProposalForm(forms.ModelForm):
    class Meta:
        model = Proposal
        fields = [
            "template", "status",
            "client_organisation", "client_contact_name", "client_role",
            "client_email", "client_phone", "client_address",
            "title", "summary", "background", "approach",
            "assumptions", "exclusions",
            "currency", "discount_percent", "tax_percent", "deposit_percent",
            "payment_terms",
            "timeline_weeks", "start_estimate", "valid_until",
            "notes",
        ]
        widgets = {
            **TEXT_WIDGETS,
            "summary": forms.TextInput(),
            "valid_until": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            css = "dash-input"
            if isinstance(field.widget, forms.Select):
                css = "dash-select"
            elif isinstance(field.widget, forms.Textarea):
                css = "dash-input dash-textarea"
            elif isinstance(field.widget, forms.CheckboxInput):
                css = "dash-check"
            field.widget.attrs.setdefault("class", css)


class ProposalStartForm(forms.ModelForm):
    """
    The short form used to open a proposal.

    Only what is needed to create the record; everything else is filled from
    the template and then edited on the full form.
    """

    class Meta:
        model = Proposal
        fields = ["template", "client_organisation", "client_contact_name",
                  "client_email", "title"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["title"].required = False
        self.fields["title"].help_text = "Leave blank to use the template's name."
        self.fields["template"].queryset = self.fields["template"].queryset.filter(
            is_active=True
        )
        for name, field in self.fields.items():
            css = "dash-select" if isinstance(field.widget, forms.Select) else "dash-input"
            field.widget.attrs.setdefault("class", css)


ProposalItemFormSet = inlineformset_factory(
    Proposal, ProposalItem,
    fields=["title", "description", "quantity", "unit", "unit_price", "display_order"],
    extra=1, can_delete=True,
    widgets={"description": forms.Textarea(attrs={"rows": 2, "class": "dash-input dash-textarea"})},
)

ProposalMilestoneFormSet = inlineformset_factory(
    Proposal, ProposalMilestone,
    fields=["name", "description", "week_from", "week_to", "percent_of_fee", "display_order"],
    extra=1, can_delete=True,
    widgets={"description": forms.Textarea(attrs={"rows": 2, "class": "dash-input dash-textarea"})},
)


class ContactStatusForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ["status"]
        widgets = {"status": forms.Select(attrs={"class": "dash-select"})}


class QuoteStatusForm(forms.ModelForm):
    class Meta:
        model = QuoteRequest
        fields = ["status", "internal_notes"]
        widgets = {
            "status": forms.Select(attrs={"class": "dash-select"}),
            "internal_notes": forms.Textarea(attrs={"rows": 4, "class": "dash-input dash-textarea"}),
        }


class CompanyProfileForm(forms.ModelForm):
    """
    The company's own record: what appears on the site and, more importantly,
    on the letterhead of every proposal.

    Fields are grouped in the template. Images are optional on every save —
    an empty file input must leave the existing image alone rather than
    clearing it, which is what ``ClearableFileInput`` gives us.
    """

    class Meta:
        model = SiteSettings
        fields = [
            # Identity
            "company_name", "legal_name", "brand_name", "registration_number",
            "founded_year", "tagline",
            # Contact
            "email", "sales_email", "support_email",
            "phone", "secondary_phone",
            "address", "location", "office_hours",
            "website_url",
            # Payment details
            "bank_name", "bank_account_name", "bank_account_number",
            # Brand assets
            "logo", "favicon", "og_image",
            # Social
            "linkedin_url", "twitter_url", "github_url", "whatsapp_url",
        ]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
            "tagline": forms.TextInput(),
        }
        help_texts = {
            "legal_name": "The registered name. Used on proposal letterheads.",
            "registration_number": "Business name registration number. Shown in the footer and on proposals.",
            "sales_email": "Where proposals ask clients to reply.",
            "address": "Shown on the proposal letterhead.",
            "logo": "Used in the site header and at the top of every proposal PDF.",
            "favicon": "The small icon shown in a browser tab.",
            "bank_account_number": "Printed on school quotations under “How to pay”. Leave blank to omit.",
            "og_image": "1200×630. Shown when a link to the site is shared.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.ClearableFileInput):
                widget.attrs.setdefault("class", "dash-file")
                widget.attrs.setdefault("accept", "image/*")
            elif isinstance(widget, forms.Select):
                widget.attrs.setdefault("class", "dash-select")
            elif isinstance(widget, forms.Textarea):
                widget.attrs.setdefault("class", "dash-input dash-textarea")
            elif isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("class", "dash-check")
            else:
                widget.attrs.setdefault("class", "dash-input")

    def clean_registration_number(self):
        # Stored bare so the label can be worded per surface; strip a prefix
        # if someone pastes one in.
        value = (self.cleaned_data.get("registration_number") or "").strip()
        for prefix in ("BN", "RC", "No.", "No", "#"):
            if value.upper().startswith(prefix.upper()):
                value = value[len(prefix):].strip(" .:-")
        return value


# ------------------------------------------------------ school quotations ---
def style_fields(form):
    """Give every widget the control panel's classes."""
    for field in form.fields.values():
        widget = field.widget
        if isinstance(widget, forms.CheckboxSelectMultiple):
            continue
        if isinstance(widget, forms.Select):
            css = "dash-select"
        elif isinstance(widget, forms.Textarea):
            css = "dash-input dash-textarea"
        elif isinstance(widget, forms.CheckboxInput):
            css = "dash-check"
        else:
            css = "dash-input"
        widget.attrs.setdefault("class", css)


SCHOOL_FIELDS = [
    "school_name", "contact_name", "contact_role", "contact_email", "contact_phone",
    "school_address", "school_type", "student_count", "campus_count", "deployment",
]


class PriceItemChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, item):
        return item.name


class QuotationStartForm(forms.ModelForm):
    """School details plus the modules to quote for. Lines are built from the ticks."""

    items = PriceItemChoiceField(
        queryset=PriceListItem.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="What to include",
    )

    class Meta:
        model = SchoolQuotation
        fields = SCHOOL_FIELDS
        widgets = {"school_address": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        active = PriceListItem.objects.filter(is_active=True)
        self.fields["items"].queryset = active
        if not self.is_bound:
            self.fields["items"].initial = [i.pk for i in active if i.selected_by_default]
        style_fields(self)

    def grouped_items(self):
        """Price-list choices grouped for display, each with its checkbox."""
        by_pk = {str(w.data["value"]): w for w in self["items"]}
        items = self.fields["items"].queryset
        groups = []
        for key, label in PriceListItem.GROUP_CHOICES:
            rows = [(item, by_pk.get(str(item.pk))) for item in items if item.group == key]
            if rows:
                groups.append((label, rows))
        return groups


class QuotationForm(forms.ModelForm):
    class Meta:
        model = SchoolQuotation
        fields = SCHOOL_FIELDS + [
            "status", "currency", "discount_percent", "tax_percent", "deposit_percent",
            "delivery_weeks", "valid_until", "payment_terms", "client_notes",
            "internal_notes",
        ]
        widgets = {
            "school_address": forms.Textarea(attrs={"rows": 2}),
            "payment_terms": forms.Textarea(attrs={"rows": 4}),
            "client_notes": forms.Textarea(attrs={"rows": 3}),
            "internal_notes": forms.Textarea(attrs={"rows": 3}),
            "valid_until": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)


QuotationLineFormSet = inlineformset_factory(
    SchoolQuotation, SchoolQuotationLine,
    fields=["title", "description", "billing", "quantity", "unit", "unit_price", "display_order"],
    extra=1, can_delete=True,
    widgets={
        "description": forms.Textarea(attrs={"rows": 2, "class": "dash-input dash-textarea"}),
        "billing": forms.Select(attrs={"class": "dash-select"}),
    },
)


class AddPriceItemsForm(forms.Form):
    """Add more price-list items to an existing quotation."""

    items = PriceItemChoiceField(
        queryset=PriceListItem.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple,
    )


PriceListFormSet = modelformset_factory(
    PriceListItem,
    fields=["name", "description", "group", "billing", "unit", "unit_price",
            "default_quantity", "selected_by_default", "is_active", "display_order"],
    extra=1, can_delete=False,
    widgets={
        "description": forms.Textarea(attrs={"rows": 2, "class": "dash-input dash-textarea"}),
        "group": forms.Select(attrs={"class": "dash-select"}),
        "billing": forms.Select(attrs={"class": "dash-select"}),
    },
)
