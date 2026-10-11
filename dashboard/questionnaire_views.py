"""
School questionnaires in the control panel.

Staff fill a school's questionnaire on the same page as the original
questionnaire; the page saves to the API below as answers change. The question
bank is edited here too, so questions can be added and removed without code.
"""
import json
import mimetypes
import re
from pathlib import Path

from django.contrib import messages
from django.db.models import Count, Max
from django.http import FileResponse, Http404, JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import ListView

from questionnaires.models import (
    Question,
    QuestionSection,
    QuestionnaireResponse,
    ResponseFile,
    bank,
)

from .access import DashboardAccessMixin
from .forms import QuestionForm, QuestionSectionForm

MAX_FILE_MB = 20
MAX_STATE_BYTES = 2 * 1024 * 1024
# What a school is likely to send: documents, spreadsheets, photos, scans,
# voice notes and short videos. SVG and HTML are excluded — they can carry
# script, and these files are opened from the control panel's own origin.
ALLOWED_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".csv", ".txt", ".rtf", ".odt", ".ods",
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".heif", ".bmp",
    ".mp3", ".m4a", ".wav", ".ogg", ".oga", ".aac", ".webm", ".opus",
    ".mp4", ".mov", ".3gp",
}
INLINE_TYPES = ("image/", "audio/", "video/", "application/pdf")
CODE_RE = re.compile(r"^[A-Za-z0-9_-]{1,12}$")


# ----------------------------------------------------------------- pages ---
class QuestionnaireListView(DashboardAccessMixin, ListView):
    template_name = "dashboard/questionnaire_list.html"
    context_object_name = "responses"
    paginate_by = 25
    required_permission = "questionnaires.view_questionnaireresponse"

    def get_queryset(self):
        qs = QuestionnaireResponse.objects.select_related("created_by", "quotation").annotate(
            file_count=Count("files")
        )
        self.query = (self.request.GET.get("q") or "").strip()
        if self.query:
            qs = qs.filter(school_name__icontains=self.query)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["query"] = self.query
        ctx["question_total"] = Question.objects.filter(is_active=True, section__is_active=True).count()
        return ctx


class QuestionnaireCreateView(DashboardAccessMixin, View):
    required_permission = "questionnaires.add_questionnaireresponse"

    def post(self, request):
        name = (request.POST.get("school_name") or "").strip()[:200]
        response = QuestionnaireResponse.objects.create(created_by=request.user, school_name=name)
        if name:
            response.data = {"answers": {"A1": name}, "notes": {}, "meta": {}, "updatedAt": 0}
        response.refresh_summary(save=False)
        response.save()
        return redirect(response.get_absolute_url())


class QuestionnaireFillView(DashboardAccessMixin, View):
    """The questionnaire page itself, wired to save into this response."""

    required_permission = "questionnaires.change_questionnaireresponse"
    template_name = "dashboard/questionnaire_fill.html"

    def get(self, request, pk):
        response = get_object_or_404(QuestionnaireResponse, pk=pk)
        config = {
            "apiBase": reverse("dashboard:questionnaire_api_root", kwargs={"pk": pk}).rstrip("/"),
            "csrfToken": get_token(request),
            "storageKey": f"techmiary-questionnaire-{pk}",
            "maxFileMB": MAX_FILE_MB,
            "filePrefix": f"questionnaire-{pk}",
        }
        page = render(request, self.template_name, {
            "response_obj": response, "bank": bank(), "sq_config": config,
        })
        # The site blocks the microphone everywhere; voice notes need it here.
        page["Permissions-Policy"] = "camera=(), microphone=(self), geolocation=(), interest-cohort=()"
        return page


class QuestionnaireDeleteView(DashboardAccessMixin, View):
    required_permission = "questionnaires.delete_questionnaireresponse"

    def get(self, request, pk):
        response = get_object_or_404(QuestionnaireResponse.objects.annotate(file_count=Count("files")), pk=pk)
        return render(request, "dashboard/questionnaire_delete.html", {"response_obj": response})

    def post(self, request, pk):
        response = get_object_or_404(QuestionnaireResponse, pk=pk)
        name = response.display_name
        for f in list(response.files.all()):
            f.delete()  # removes the stored file as well as the row
        response.delete()
        messages.success(request, f"The questionnaire for {name} was deleted.")
        return redirect("dashboard:questionnaire_list")


class QuestionnaireStatusView(DashboardAccessMixin, View):
    required_permission = "questionnaires.change_questionnaireresponse"

    def post(self, request, pk):
        response = get_object_or_404(QuestionnaireResponse, pk=pk)
        status = request.POST.get("status")
        if status in dict(QuestionnaireResponse.STATUS_CHOICES):
            response.status = status
            response.save(update_fields=["status", "updated_at"])
            messages.success(request, f"{response.display_name} marked {response.get_status_display().lower()}.")
        return redirect(request.POST.get("next") or "dashboard:questionnaire_list")


# ------------------------------------------------------------------- API ---
class ApiAccessMixin(DashboardAccessMixin):
    """
    The page's save calls get JSON errors, never a redirect to the sign-in
    page: a redirect would come back as a 200 HTML page and the page would
    wrongly report "Saved to server".
    """

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated or not user.is_active or not user.is_staff:
            return JsonResponse({"error": "Please sign in again."}, status=403)
        if self.required_permission and not user.has_perm(self.required_permission):
            return JsonResponse({"error": "Your account cannot edit questionnaires."}, status=403)
        self.response_obj = get_object_or_404(QuestionnaireResponse, pk=kwargs["pk"])
        return View.dispatch(self, request, *args, **kwargs)


class QuestionnaireStateApi(ApiAccessMixin, View):
    required_permission = "questionnaires.change_questionnaireresponse"

    def get(self, request, pk):
        return JsonResponse(self.response_obj.page_state())

    def post(self, request, pk):
        if len(request.body) > MAX_STATE_BYTES:
            return JsonResponse({"error": "Too much data in one save."}, status=413)
        try:
            incoming = json.loads(request.body or b"{}")
        except (ValueError, UnicodeDecodeError):
            return JsonResponse({"error": "Invalid data."}, status=400)
        if not isinstance(incoming, dict):
            return JsonResponse({"error": "Invalid data."}, status=400)
        self.response_obj.store_state(incoming)
        return JsonResponse({"ok": True, "files": self.response_obj.files_by_question(),
                             "answered": self.response_obj.answered_count})


class QuestionnaireFilesApi(ApiAccessMixin, View):
    required_permission = "questionnaires.change_questionnaireresponse"

    def post(self, request, pk):
        upload = request.FILES.get("file")
        code = (request.POST.get("question") or "").strip()
        if upload is None:
            return JsonResponse({"error": "No file was sent."}, status=400)
        if not CODE_RE.match(code):
            return JsonResponse({"error": "Unknown question."}, status=400)
        if upload.size > MAX_FILE_MB * 1024 * 1024:
            return JsonResponse({"error": f"That file is too big ({MAX_FILE_MB} MB limit)."}, status=413)
        ext = Path(upload.name).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            return JsonResponse(
                {"error": "That file type isn't allowed. Use PDF, Office documents, images, audio or video."},
                status=415,
            )
        kind = request.POST.get("kind")
        content_type = upload.content_type or mimetypes.guess_type(upload.name)[0] or "application/octet-stream"
        record = ResponseFile.objects.create(
            response=self.response_obj, question_code=code,
            kind=kind if kind in (ResponseFile.KIND_FILE, ResponseFile.KIND_VOICE) else ResponseFile.KIND_FILE,
            file=upload, name=Path(upload.name).name[:255], label=(request.POST.get("label") or "")[:120],
            content_type=content_type[:120], size=upload.size, uploaded_by=request.user,
        )
        self.response_obj.refresh_summary()
        return JsonResponse(record.as_dict(), status=201)


class QuestionnaireFileItemApi(ApiAccessMixin, View):
    required_permission = "questionnaires.change_questionnaireresponse"

    def delete(self, request, pk, file_id):
        record = get_object_or_404(ResponseFile, pk=file_id, response=self.response_obj)
        record.delete()
        self.response_obj.refresh_summary()
        return JsonResponse({"ok": True})


class QuestionnaireFileDownloadView(DashboardAccessMixin, View):
    """Files are private; this is the only way to read one."""

    required_permission = "questionnaires.view_questionnaireresponse"

    def get(self, request, pk, file_id):
        record = get_object_or_404(ResponseFile, pk=file_id, response_id=pk)
        try:
            handle = record.file.open("rb")
        except (FileNotFoundError, ValueError):
            raise Http404("The file is missing from storage.")
        inline = record.content_type.startswith(INLINE_TYPES) and "svg" not in record.content_type
        return FileResponse(handle, as_attachment=not inline, filename=record.name,
                            content_type=record.content_type or "application/octet-stream")


# --------------------------------------------------------- question bank ---
class QuestionBankView(DashboardAccessMixin, View):
    required_permission = "questionnaires.change_question"
    template_name = "dashboard/question_bank.html"

    def get(self, request):
        sections = QuestionSection.objects.prefetch_related("questions")
        return render(request, self.template_name, {
            "sections": sections,
            "active_count": (active := Question.objects.filter(is_active=True, section__is_active=True).count()),
            "hidden_count": Question.objects.count() - active,
        })


def _next_code(section):
    """A1..A21 → A22. Falls back to the section letter plus a number."""
    numbers = []
    for code in section.questions.values_list("code", flat=True):
        m = re.match(rf"^{re.escape(section.code)}(\d+)$", code)
        if m:
            numbers.append(int(m.group(1)))
    n = (max(numbers) + 1) if numbers else 1
    while Question.objects.filter(code=f"{section.code}{n}").exists():
        n += 1
    return f"{section.code}{n}"


class QuestionEditView(DashboardAccessMixin, View):
    """Add (no pk) or edit a question."""

    template_name = "dashboard/question_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.required_permission = (
            "questionnaires.change_question" if kwargs.get("pk") else "questionnaires.add_question"
        )
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, pk):
        return get_object_or_404(Question, pk=pk) if pk else None

    def get(self, request, pk=None):
        question = self.get_object(pk)
        initial = {}
        if question is None:
            section = QuestionSection.objects.filter(pk=request.GET.get("section")).first() \
                or QuestionSection.objects.first()
            if section:
                last = section.questions.aggregate(m=Max("display_order"))["m"] or 0
                initial = {"section": section.pk, "code": _next_code(section), "display_order": last + 10}
        form = QuestionForm(instance=question, initial=initial)
        return render(request, self.template_name, {"form": form, "question": question})

    def post(self, request, pk=None):
        question = self.get_object(pk)
        form = QuestionForm(request.POST, instance=question)
        if form.is_valid():
            saved = form.save()
            messages.success(request, f"{saved.code} {'saved' if question else 'added'}.")
            if "_another" in request.POST:
                return redirect(f"{reverse('dashboard:question_new')}?section={saved.section_id}")
            return redirect(f"{reverse('dashboard:question_bank')}#section-{saved.section.code}")
        messages.error(request, "Please correct the highlighted fields.")
        return render(request, self.template_name, {"form": form, "question": question})


class QuestionDeleteView(DashboardAccessMixin, View):
    required_permission = "questionnaires.delete_question"

    def get(self, request, pk):
        question = get_object_or_404(Question, pk=pk)
        answered = sum(
            1 for r in QuestionnaireResponse.objects.only("data")
            if question.is_answered((r.data or {}).get("answers") or {}, {})
        )
        return render(request, "dashboard/question_delete.html", {"question": question, "answered": answered})

    def post(self, request, pk):
        question = get_object_or_404(Question, pk=pk)
        code, section_code = question.code, question.section.code
        question.delete()
        messages.success(
            request,
            f"{code} removed. Answers schools already gave to it stay in their saved responses.",
        )
        return redirect(f"{reverse('dashboard:question_bank')}#section-{section_code}")


class SectionEditView(DashboardAccessMixin, View):
    template_name = "dashboard/question_section_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.required_permission = (
            "questionnaires.change_questionsection" if kwargs.get("pk")
            else "questionnaires.add_questionsection"
        )
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, pk=None):
        section = get_object_or_404(QuestionSection, pk=pk) if pk else None
        initial = {}
        if section is None:
            last = QuestionSection.objects.aggregate(m=Max("display_order"))["m"] or 0
            initial = {"display_order": last + 10}
        return render(request, self.template_name, {
            "form": QuestionSectionForm(instance=section, initial=initial), "section": section,
        })

    def post(self, request, pk=None):
        section = get_object_or_404(QuestionSection, pk=pk) if pk else None
        form = QuestionSectionForm(request.POST, instance=section)
        if form.is_valid():
            saved = form.save()
            messages.success(request, f"Section {saved.code} {'saved' if section else 'added'}.")
            return redirect(f"{reverse('dashboard:question_bank')}#section-{saved.code}")
        messages.error(request, "Please correct the highlighted fields.")
        return render(request, self.template_name, {"form": form, "section": section})


class SectionDeleteView(DashboardAccessMixin, View):
    required_permission = "questionnaires.delete_questionsection"

    def get(self, request, pk):
        section = get_object_or_404(QuestionSection.objects.annotate(n=Count("questions")), pk=pk)
        return render(request, "dashboard/question_section_delete.html", {"section": section})

    def post(self, request, pk):
        section = get_object_or_404(QuestionSection, pk=pk)
        label = str(section)
        section.delete()
        messages.success(request, f"Section {label} and its questions were removed.")
        return redirect("dashboard:question_bank")
