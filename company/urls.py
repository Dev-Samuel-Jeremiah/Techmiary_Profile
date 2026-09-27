from django.urls import path

from . import views

app_name = "company"

urlpatterns = [
    path("solutions/", views.SolutionListView.as_view(), name="solution_list"),
    path("solutions/<slug:slug>/", views.SolutionDetailView.as_view(), name="solution_detail"),
    path("industries/", views.IndustryListView.as_view(), name="industry_list"),
    path("industries/<slug:slug>/", views.IndustryDetailView.as_view(), name="industry_detail"),
    path("team/", views.TeamListView.as_view(), name="team_list"),
    path("team/<slug:slug>/", views.TeamDetailView.as_view(), name="team_detail"),
    path("resources/", views.ResourceListView.as_view(), name="resource_list"),
    path("faq/", views.FAQView.as_view(), name="faq"),
    path("clients/", views.ClientListView.as_view(), name="client_list"),
]
