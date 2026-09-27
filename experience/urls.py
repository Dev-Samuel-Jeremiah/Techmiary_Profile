from django.urls import path

from . import views

app_name = "experience"

urlpatterns = [path("", views.ExperienceListView.as_view(), name="list")]
