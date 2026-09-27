from django import forms

from .models import JobApplication

MAX_CV_BYTES = 5 * 1024 * 1024


class JobApplicationForm(forms.ModelForm):
    """Application form for a single opening, with a CV upload."""

    website = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}),
        label="Leave this field empty",
    )
    consent = forms.BooleanField(
        required=True,
        label="I agree that my details and CV may be stored so this application can be reviewed.",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    class Meta:
        model = JobApplication
        fields = [
            "full_name",
            "email",
            "phone",
            "location",
            "cv",
            "cover_letter",
            "portfolio_url",
            "linkedin_url",
        ]
        widgets = {
            "full_name": forms.TextInput(attrs={"autocomplete": "name", "placeholder": "Your full name"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email", "placeholder": "you@example.com"}),
            "phone": forms.TextInput(attrs={"autocomplete": "tel", "placeholder": "Optional"}),
            "location": forms.TextInput(attrs={"placeholder": "City, country"}),
            "cover_letter": forms.Textarea(
                attrs={"rows": 6, "placeholder": "Why this role, and what you would bring to it."}
            ),
            "portfolio_url": forms.URLInput(attrs={"placeholder": "https:// (optional)"}),
            "linkedin_url": forms.URLInput(attrs={"placeholder": "https:// (optional)"}),
        }
        labels = {
            "cv": "CV / résumé",
            "portfolio_url": "Portfolio or GitHub",
            "linkedin_url": "LinkedIn profile",
            "full_name": "Full name",
            "location": "Where you are based",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name in ("consent",):
                continue
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

    def clean_cv(self):
        cv = self.cleaned_data["cv"]
        if cv.size > MAX_CV_BYTES:
            raise forms.ValidationError("Please keep the file under 5 MB.")
        return cv
