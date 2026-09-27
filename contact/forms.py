from django import forms

from .models import ContactMessage, NewsletterSubscriber, QuoteRequest


class ContactForm(forms.ModelForm):
    """
    Contact form with a honeypot field.

    ``website`` is hidden from real users with CSS and left empty; bots that
    fill in every input are rejected without a visible challenge.
    """

    website = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}),
        label="Leave this field empty",
    )

    class Meta:
        model = ContactMessage
        fields = ["name", "email", "phone", "company", "subject", "message"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Your full name", "autocomplete": "name"}),
            "email": forms.EmailInput(attrs={"placeholder": "you@example.com", "autocomplete": "email"}),
            "phone": forms.TextInput(attrs={"placeholder": "Optional", "autocomplete": "tel"}),
            "company": forms.TextInput(attrs={"placeholder": "Optional", "autocomplete": "organization"}),
            "subject": forms.TextInput(attrs={"placeholder": "What is this about?"}),
            "message": forms.Textarea(attrs={"rows": 6, "placeholder": "Describe the project, system or problem."}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            css = "form-control"
            if name == "website":
                css = "form-control hp-field"
            field.widget.attrs.setdefault("class", css)
            if field.required:
                field.widget.attrs["aria-required"] = "true"

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("This submission looks automated.")
        return ""

    def clean_message(self):
        message = self.cleaned_data["message"].strip()
        if len(message) < 20:
            raise forms.ValidationError(
                "Please add a little more detail — at least 20 characters."
            )
        if message.count("http") > 4:
            raise forms.ValidationError("Too many links in this message.")
        return message

    def clean_name(self):
        return self.cleaned_data["name"].strip()


class QuoteRequestForm(forms.ModelForm):
    """
    The 'Request a quote' form.

    It is one HTML form presented as three steps by the template, so it works
    without JavaScript: with JS off every step is simply visible at once and
    the single submit still validates server-side.
    """

    website = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}),
        label="Leave this field empty",
    )

    class Meta:
        model = QuoteRequest
        fields = [
            "service",
            "solution",
            "project_title",
            "description",
            "budget_range",
            "timeline",
            "existing_system",
            "contact_name",
            "email",
            "phone",
            "organisation",
            "organisation_type",
            "country",
        ]
        widgets = {
            "project_title": forms.TextInput(
                attrs={"placeholder": "e.g. Student records system for three campuses"}
            ),
            "description": forms.Textarea(
                attrs={
                    "rows": 6,
                    "placeholder": "What should the system do? Who will use it? What do you use today?",
                }
            ),
            "contact_name": forms.TextInput(attrs={"autocomplete": "name"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
            "phone": forms.TextInput(attrs={"autocomplete": "tel"}),
            "organisation": forms.TextInput(attrs={"autocomplete": "organization"}),
            "country": forms.TextInput(attrs={"autocomplete": "country-name"}),
        }
        labels = {
            "service": "Service you need",
            "solution": "Solution you are interested in",
            "existing_system": "We already run a system this would replace",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from company.models import Solution
        from services.models import Service

        self.fields["service"].queryset = Service.objects.filter(is_active=True)
        self.fields["solution"].queryset = Solution.objects.filter(is_active=True)
        self.fields["service"].empty_label = "Not sure yet"
        self.fields["solution"].empty_label = "Not sure yet"

        for name, field in self.fields.items():
            if name == "existing_system":
                field.widget.attrs.setdefault("class", "form-check-input")
                continue
            css = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            if name == "website":
                css = "form-control hp-field"
            field.widget.attrs.setdefault("class", css)
            if field.required:
                field.widget.attrs["aria-required"] = "true"

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("This submission looks automated.")
        return ""

    def clean_description(self):
        description = self.cleaned_data["description"].strip()
        if len(description) < 30:
            raise forms.ValidationError(
                "Please describe the project in a little more detail — at least 30 characters."
            )
        return description


class NewsletterForm(forms.ModelForm):
    """Email capture. Re-subscribing an existing address reactivates it."""

    class Meta:
        model = NewsletterSubscriber
        fields = ["email", "name"]
        widgets = {
            "email": forms.EmailInput(
                attrs={
                    "placeholder": "you@example.com",
                    "autocomplete": "email",
                    "class": "form-control",
                    "aria-label": "Email address",
                }
            ),
            "name": forms.TextInput(
                attrs={
                    "placeholder": "Your name (optional)",
                    "autocomplete": "name",
                    "class": "form-control",
                    "aria-label": "Your name",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["name"].required = False
        # A duplicate address is not an error for the visitor; the view
        # reactivates the existing record instead.
        self.fields["email"].validators = [
            v for v in self.fields["email"].validators
        ]

    def validate_unique(self):
        return
