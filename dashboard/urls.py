from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("login/", views.DashboardLoginView.as_view(), name="login"),
    path("logout/", views.DashboardLogoutView.as_view(), name="logout"),
    path("", views.DashboardHomeView.as_view(), name="home"),

    path("proposals/", views.ProposalListView.as_view(), name="proposal_list"),
    path("proposals/new/", views.ProposalCreateView.as_view(), name="proposal_new"),
    path("proposals/<int:pk>/", views.ProposalEditView.as_view(), name="proposal_edit"),
    path("proposals/<int:pk>/status/", views.ProposalStatusView.as_view(), name="proposal_status"),

    path("quotations/", views.QuotationListView.as_view(), name="quotation_list"),
    path("quotations/new/", views.QuotationCreateView.as_view(), name="quotation_new"),
    path("quotations/<int:pk>/", views.QuotationEditView.as_view(), name="quotation_edit"),
    path("quotations/<int:pk>/add/", views.QuotationAddItemsView.as_view(), name="quotation_add_items"),
    path("quotations/<int:pk>/status/", views.QuotationStatusView.as_view(), name="quotation_status"),
    path("quotations/<int:pk>/duplicate/", views.QuotationDuplicateView.as_view(), name="quotation_duplicate"),
    path("price-list/", views.PriceListView.as_view(), name="price_list"),

    path("company/", views.CompanyProfileView.as_view(), name="company_profile"),

    path("enquiries/", views.EnquiryListView.as_view(), name="enquiry_list"),
    path("enquiries/<int:pk>/", views.EnquiryDetailView.as_view(), name="enquiry_detail"),
    path("quotes/", views.QuoteListView.as_view(), name="quote_list"),
    path("quotes/<int:pk>/", views.QuoteDetailView.as_view(), name="quote_detail"),
]
