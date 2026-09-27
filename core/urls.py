from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = "core"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("about/", views.AboutView.as_view(), name="about"),
    path("technology/", views.TechnologyView.as_view(), name="skills"),
    # The stack page used to live at /skills/; keep the old address working.
    path("skills/", RedirectView.as_view(pattern_name="core:skills", permanent=True)),
    path("privacy/", views.PrivacyView.as_view(), name="privacy"),
    path("terms/", views.TermsView.as_view(), name="terms"),
]
