from django.urls import path

from . import views

app_name = "careers"

urlpatterns = [
    path("", views.JobListView.as_view(), name="list"),
    path("<slug:slug>/", views.JobDetailView.as_view(), name="detail"),
    path("<slug:slug>/apply/", views.JobApplyView.as_view(), name="apply"),
]
