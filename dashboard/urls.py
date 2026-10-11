from django.urls import path

from . import questionnaire_views as qv
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
    path("quotations/<int:pk>/sync/", views.QuotationSyncView.as_view(), name="quotation_sync"),
    path("quotations/<int:pk>/delete/", views.QuotationDeleteView.as_view(), name="quotation_delete"),
    path("price-list/", views.PriceListView.as_view(), name="price_list"),

    path("questionnaires/", qv.QuestionnaireListView.as_view(), name="questionnaire_list"),
    path("questionnaires/new/", qv.QuestionnaireCreateView.as_view(), name="questionnaire_new"),
    path("questionnaires/<int:pk>/", qv.QuestionnaireFillView.as_view(), name="questionnaire_fill"),
    path("questionnaires/<int:pk>/status/", qv.QuestionnaireStatusView.as_view(), name="questionnaire_status"),
    path("questionnaires/<int:pk>/delete/", qv.QuestionnaireDeleteView.as_view(), name="questionnaire_delete"),
    path("questionnaires/<int:pk>/files/<int:file_id>/", qv.QuestionnaireFileDownloadView.as_view(), name="questionnaire_file"),
    path("questionnaires/<int:pk>/api/", qv.QuestionnaireStateApi.as_view(), name="questionnaire_api_root"),
    path("questionnaires/<int:pk>/api/state/", qv.QuestionnaireStateApi.as_view(), name="questionnaire_api_state"),
    path("questionnaires/<int:pk>/api/files/", qv.QuestionnaireFilesApi.as_view(), name="questionnaire_api_files"),
    path("questionnaires/<int:pk>/api/files/<int:file_id>/", qv.QuestionnaireFileItemApi.as_view(), name="questionnaire_api_file"),

    path("question-bank/", qv.QuestionBankView.as_view(), name="question_bank"),
    path("question-bank/questions/new/", qv.QuestionEditView.as_view(), name="question_new"),
    path("question-bank/questions/<int:pk>/", qv.QuestionEditView.as_view(), name="question_edit"),
    path("question-bank/questions/<int:pk>/delete/", qv.QuestionDeleteView.as_view(), name="question_delete"),
    path("question-bank/sections/new/", qv.SectionEditView.as_view(), name="section_new"),
    path("question-bank/sections/<int:pk>/", qv.SectionEditView.as_view(), name="section_edit"),
    path("question-bank/sections/<int:pk>/delete/", qv.SectionDeleteView.as_view(), name="section_delete"),

    path("company/", views.CompanyProfileView.as_view(), name="company_profile"),

    path("enquiries/", views.EnquiryListView.as_view(), name="enquiry_list"),
    path("enquiries/<int:pk>/", views.EnquiryDetailView.as_view(), name="enquiry_detail"),
    path("quotes/", views.QuoteListView.as_view(), name="quote_list"),
    path("quotes/<int:pk>/", views.QuoteDetailView.as_view(), name="quote_detail"),
]
