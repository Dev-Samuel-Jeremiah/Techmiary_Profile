"""Forms used by the staff dashboard."""
import re
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


# ---------------------------------------------------------- question bank ---
from django.utils.text import slugify  # noqa: E402

from questionnaires.models import Question, QuestionSection  # noqa: E402

QUESTION_CODE_RE = r"^[A-Za-z0-9_-]{1,12}$"


def _lines(text):
    return [line.strip() for line in (text or "").splitlines() if line.strip()]


class QuestionSectionForm(forms.ModelForm):
    class Meta:
        model = QuestionSection
        fields = ["code", "title", "handled_by", "display_order", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)

    def clean_code(self):
        code = self.cleaned_data["code"].strip().upper()
        if not re.match(r"^[A-Z0-9]{1,4}$", code):
            raise forms.ValidationError("Use 1–4 letters or digits, e.g. Y.")
        return code


class QuestionForm(forms.ModelForm):
    """
    The question editor. Options, table rows and table columns are edited as
    plain lines, then stored in the shape the questionnaire page reads.
    """

    options_text = forms.CharField(
        label="Options", required=False, widget=forms.Textarea(attrs={"rows": 6}),
        help_text="One per line. “Other” is added automatically unless you tick “No Other option”.",
    )
    grid_rows_text = forms.CharField(
        label="Table rows", required=False, widget=forms.Textarea(attrs={"rows": 6}),
        help_text="One row per line, e.g. Physics lab.",
    )
    grid_columns_text = forms.CharField(
        label="Table columns", required=False, widget=forms.Textarea(attrs={"rows": 5}),
        help_text=(
            "One column per line: Label | type | options. Types: yn, one, many, num, text. "
            "Options (for one / many) are separated by commas. Add “| no other” to hide Other. "
            "Example: Sections that use it | many | Nursery & Primary, Secondary, Islamic | no other"
        ),
    )

    class Meta:
        model = Question
        fields = ["section", "code", "qtype", "text", "ask_who", "per_section", "long_answer",
                  "no_other", "accept", "single_file", "display_order", "is_active"]
        labels = {"no_other": "No Other option", "ask_who": "Ask (optional)", "accept": "Allowed files"}
        widgets = {"text": forms.TextInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        q = self.instance
        if q.pk:
            self.fields["options_text"].initial = "\n".join(q.options or [])
            self.fields["grid_rows_text"].initial = "\n".join(q.grid_rows or [])
            self.fields["grid_columns_text"].initial = "\n".join(
                " | ".join(
                    [c.get("label", ""), c.get("type", "text")]
                    + ([", ".join(c.get("o") or [])] if c.get("o") else [])
                    + (["no other"] if c.get("noOther") else [])
                )
                for c in (q.grid_columns or [])
            )
        self.fields["accept"].help_text = "File questions only. Leave blank for any document, or image/* for images."
        style_fields(self)

    def clean_code(self):
        code = self.cleaned_data["code"].strip()
        if not re.match(QUESTION_CODE_RE, code):
            raise forms.ValidationError("Use letters, digits, - or _ only (no spaces), e.g. A22.")
        return code

    def _parse_columns(self, text):
        old = {c.get("label"): c.get("k") for c in (self.instance.grid_columns or [])}
        columns, used = [], set()
        for n, line in enumerate(_lines(text), start=1):
            parts = [p.strip() for p in line.split("|")]
            label = parts[0]
            ctype = (parts[1].lower() if len(parts) > 1 and parts[1] else "text")
            if not label:
                raise forms.ValidationError(f"Column line {n} has no label.")
            if ctype not in Question.GRID_COLUMN_TYPES:
                raise forms.ValidationError(f"Column “{label}”: type must be one of yn, one, many, num, text.")
            extras = parts[2:]
            no_other = any(p.lower().replace("-", " ") == "no other" for p in extras)
            option_parts = [p for p in extras if p.lower().replace("-", " ") != "no other"]
            options = [o.strip() for o in ",".join(option_parts).split(",") if o.strip()]
            if ctype in Question.CHOICE_TYPES and not options:
                raise forms.ValidationError(f"Column “{label}” needs options.")
            # Keep the stored key when the label is unchanged, so answers
            # already given to this column stay attached to it.
            key = old.get(label) or slugify(label).replace("-", "_")[:24] or f"c{n}"
            while key in used:
                key += "_"
            used.add(key)
            col = {"k": key, "label": label, "type": ctype}
            if ctype in Question.CHOICE_TYPES:
                col["o"] = options
            if no_other:
                col["noOther"] = True
            columns.append(col)
        return columns

    def clean(self):
        data = super().clean()
        qtype = data.get("qtype")
        options = _lines(data.get("options_text"))
        if qtype in Question.CHOICE_TYPES and not options:
            self.add_error("options_text", "Add at least one option.")
        if qtype == Question.TYPE_GRID:
            rows = _lines(data.get("grid_rows_text"))
            if not rows:
                self.add_error("grid_rows_text", "Add at least one row.")
            try:
                columns = self._parse_columns(data.get("grid_columns_text"))
            except forms.ValidationError as e:
                self.add_error("grid_columns_text", e)
                columns = []
            if not columns and not self.has_error("grid_columns_text"):
                self.add_error("grid_columns_text", "Add at least one column.")
            data["_rows"], data["_columns"] = rows, columns
        if data.get("per_section") and qtype in (Question.TYPE_GRID, Question.TYPE_FILE):
            self.add_error("per_section", "Tables and file uploads cannot be asked per section.")
        data["_options"] = options
        return data

    def save(self, commit=True):
        q = super().save(commit=False)
        data = self.cleaned_data
        q.options = data.get("_options", []) if q.qtype in Question.CHOICE_TYPES else []
        if q.qtype == Question.TYPE_GRID:
            q.grid_rows, q.grid_columns = data.get("_rows", []), data.get("_columns", [])
        else:
            q.grid_rows, q.grid_columns = [], []
        if q.qtype != Question.TYPE_TEXT:
            q.long_answer = False
        if q.qtype != Question.TYPE_FILE:
            q.accept, q.single_file = "", False
        if commit:
            q.save()
        return q
