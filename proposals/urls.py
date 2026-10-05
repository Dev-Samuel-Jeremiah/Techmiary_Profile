from django.urls import path

from . import views

app_name = "proposals"

urlpatterns = [
    path("proposal/<int:pk>/pdf/", views.proposal_pdf, name="pdf"),
    path("quotation/<int:pk>/pdf/", views.quotation_pdf, name="quotation_pdf"),
]
