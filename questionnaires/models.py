"""
School requirements questionnaires.

The question bank lives in the database so a company admin can add, edit and
remove questions. Each school's answers are one ``QuestionnaireResponse``: the
page's own state (answers, notes, per-section "answered by") stored as JSON,
exactly as the questionnaire front end reads and writes it. Uploaded files and
voice notes are rows of their own, kept in private storage.
"""
import os
import uuid
from pathlib import Path

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.urls import reverse

# Each "per section" question is asked once for each of these, keyed by code.
PER_SECTIONS = [("NP", "Nursery & Primary"), ("SEC", "Secondary"), ("ISL", "Islamic")]


class PrivateFileSystemStorage(FileSystemStorage):
    """
    Files outside MEDIA_ROOT. The web server serves MEDIA_ROOT publicly, and a
    school's documents (letterheads, fee schedules, payslips) must only be
    reachable through the staff-only download view. The location is read from
    settings each time, so it follows PRIVATE_MEDIA_ROOT wherever it points.
    """

    def __init__(self, **kwargs):
        kwargs.setdefault("base_url", None)
        super().__init__(**kwargs)

    @property
    def base_location(self):
        return self._value_or_setting(self._location, settings.PRIVATE_MEDIA_ROOT)

    @property
    def location(self):
        return os.path.abspath(self.base_location)


def private_storage():
    """Referenced by name from migrations, so no path is frozen into them."""
    return PrivateFileSystemStorage()


class QuestionSection(models.Model):
    code = models.CharField(max_length=4, unique=True, help_text="Letter shown on the tab, e.g. A.")
    title = models.CharField(max_length=160)
    handled_by = models.CharField(max_length=200, blank=True, help_text="Who at the school answers this section.")
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "code"]
        verbose_name = "Question section"

    def __str__(self):
        return f"{self.code}. {self.title}"


class Question(models.Model):
    TYPE_YN = "yn"
    TYPE_ONE = "one"
    TYPE_MANY = "many"
    TYPE_NUM = "num"
    TYPE_TEXT = "text"
    TYPE_TIME = "time"
    TYPE_GRID = "grid"
    TYPE_FILE = "file"
    TYPE_CHOICES = [
        (TYPE_YN, "Yes / No / Not sure"),
        (TYPE_ONE, "Pick one"),
        (TYPE_MANY, "Pick any"),
        (TYPE_NUM, "Number"),
        (TYPE_TEXT, "Text"),
        (TYPE_TIME, "Time"),
        (TYPE_GRID, "Table (rows × columns)"),
        (TYPE_FILE, "File upload"),
    ]
    CHOICE_TYPES = {TYPE_ONE, TYPE_MANY}
    GRID_COLUMN_TYPES = {TYPE_YN, TYPE_ONE, TYPE_MANY, TYPE_NUM, TYPE_TEXT}

    section = models.ForeignKey(QuestionSection, on_delete=models.CASCADE, related_name="questions")
    code = models.CharField(
        max_length=12, unique=True,
        help_text="Unique, e.g. A22. Answers are stored against it, so avoid changing it once schools have answered.",
    )
    qtype = models.CharField("Type", max_length=6, choices=TYPE_CHOICES, default=TYPE_YN)
    text = models.CharField(max_length=300)
    options = models.JSONField(default=list, blank=True, help_text="For pick-one / pick-any questions.")
    per_section = models.BooleanField(
        default=False, help_text="Ask once for each of Nursery & Primary, Secondary and Islamic.",
    )
    long_answer = models.BooleanField(default=False, help_text="Text questions: a large box.")
    no_other = models.BooleanField(default=False, help_text="Choice questions: hide the “Other” option.")
    ask_who = models.CharField(max_length=160, blank=True, help_text="Shown as “Ask: …” under the question.")
    accept = models.CharField(max_length=200, blank=True, help_text="File questions: e.g. image/* for images only.")
    single_file = models.BooleanField(default=False, help_text="File questions: a new upload replaces the old one.")
    grid_rows = models.JSONField(default=list, blank=True)
    grid_columns = models.JSONField(
        default=list, blank=True,
        help_text="List of {k, label, type, o, noOther}. Edited as lines in the control panel.",
    )
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["section__display_order", "display_order", "id"]

    def __str__(self):
        return f"{self.code} — {self.text}"

    def as_bank(self):
        """The question in the shape the questionnaire page expects."""
        q = {"code": self.code, "type": self.qtype, "text": self.text}
        if self.qtype in self.CHOICE_TYPES:
            q["o"] = list(self.options or [])
        if self.per_section:
            q["per"] = True
        if self.long_answer:
            q["long"] = True
        if self.no_other:
            q["noOther"] = True
        if self.ask_who:
            q["who"] = self.ask_who
        if self.qtype == self.TYPE_FILE:
            if self.accept:
                q["accept"] = self.accept
            if self.single_file:
                q["single"] = True
        if self.qtype == self.TYPE_GRID:
            q["rows"] = list(self.grid_rows or [])
            q["cols"] = list(self.grid_columns or [])
        return q

    def is_answered(self, answers, files):
        """Mirrors qAnswered() in the page script, so progress matches."""
        def filled(v):
            if isinstance(v, list):
                return len(v) > 0
            return v is not None and str(v).strip() != ""

        if filled(answers.get(self.code)) or files.get(self.code):
            return True
        prefix = self.code + "|"
        return any(
            k.startswith(prefix) and not k.endswith("|other") and filled(v)
            for k, v in answers.items()
        )


def bank():
    """Every active section with its active questions, ready for the page."""
    sections = QuestionSection.objects.filter(is_active=True).prefetch_related(
        models.Prefetch("questions", queryset=Question.objects.filter(is_active=True))
    )
    out = []
    for s in sections:
        qs = [q.as_bank() for q in s.questions.all()]
        if qs:
            out.append({"id": s.code, "title": s.title, "by": s.handled_by, "qs": qs})
    return out


class QuestionnaireResponse(models.Model):
    """One school's answers."""

    STATUS_IN_PROGRESS = "in_progress"
    STATUS_COMPLETE = "complete"
    STATUS_CHOICES = [(STATUS_IN_PROGRESS, "In progress"), (STATUS_COMPLETE, "Complete")]

    school_name = models.CharField(
        max_length=200, blank=True, help_text="Taken from question A1 when answered.",
    )
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_IN_PROGRESS)
    data = models.JSONField(default=dict, blank=True)
    answered_count = models.PositiveIntegerField(default=0)
    question_count = models.PositiveIntegerField(default=0)
    quotation = models.ForeignKey(
        "proposals.SchoolQuotation", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="questionnaires",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="questionnaire_responses",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "Questionnaire response"

    def __str__(self):
        return self.display_name

    @property
    def display_name(self):
        return self.school_name or f"Untitled school #{self.pk}"

    @property
    def percent(self):
        return round(self.answered_count * 100 / self.question_count) if self.question_count else 0

    def files_by_question(self):
        """{question code: [file dicts]} in the shape the page expects."""
        out = {}
        for f in self.files.all():
            out.setdefault(f.question_code, []).append(f.as_dict())
        return out

    def page_state(self):
        state = dict(self.data or {})
        for key in ("answers", "notes", "meta"):
            state.setdefault(key, {})
        state.setdefault("updatedAt", 0)
        state["files"] = self.files_by_question()
        return state

    def store_state(self, incoming):
        """Save the page's state. Files are owned by the server, never the client."""
        clean = {k: incoming.get(k) or {} for k in ("answers", "notes", "meta")}
        for key in clean:
            if not isinstance(clean[key], dict):
                clean[key] = {}
        try:
            clean["updatedAt"] = int(incoming.get("updatedAt") or 0)
        except (TypeError, ValueError):
            clean["updatedAt"] = 0
        self.data = clean
        self.refresh_summary(save=False)
        self.save()

    def refresh_summary(self, save=True):
        answers = (self.data or {}).get("answers") or {}
        files = {code: True for code in self.files.values_list("question_code", flat=True)}
        questions = Question.objects.filter(is_active=True, section__is_active=True)
        self.question_count = questions.count()
        self.answered_count = sum(1 for q in questions if q.is_answered(answers, files))
        name = str(answers.get("A1") or "").strip()
        if name:
            self.school_name = name[:200]
        if save:
            self.save(update_fields=["question_count", "answered_count", "school_name", "updated_at"])

    def get_absolute_url(self):
        return reverse("dashboard:questionnaire_fill", kwargs={"pk": self.pk})

    def students_by_section(self):
        answers = (self.data or {}).get("answers") or {}
        out = {}
        for key, label in PER_SECTIONS:
            try:
                out[label] = int(float(answers.get(f"A12|{key}") or 0))
            except (TypeError, ValueError):
                out[label] = 0
        return out


def _upload_to(instance, filename):
    ext = Path(filename).suffix.lower()[:10]
    return f"questionnaires/{instance.response_id}/{uuid.uuid4().hex}{ext}"


class ResponseFile(models.Model):
    KIND_FILE = "file"
    KIND_VOICE = "voice"

    response = models.ForeignKey(QuestionnaireResponse, on_delete=models.CASCADE, related_name="files")
    question_code = models.CharField(max_length=12)
    kind = models.CharField(max_length=6, choices=[(KIND_FILE, "File"), (KIND_VOICE, "Voice note")], default=KIND_FILE)
    file = models.FileField(upload_to=_upload_to, storage=private_storage)
    name = models.CharField(max_length=255)
    label = models.CharField(max_length=120, blank=True)
    content_type = models.CharField(max_length=120, blank=True)
    size = models.PositiveIntegerField(default=0)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("dashboard:questionnaire_file", kwargs={"pk": self.response_id, "file_id": self.pk})

    def as_dict(self):
        return {
            "id": self.pk, "name": self.name, "label": self.label, "type": self.content_type,
            "size": self.size, "kind": self.kind, "url": self.get_absolute_url(),
        }

    def delete(self, *args, **kwargs):
        stored = self.file
        super().delete(*args, **kwargs)
        if stored:
            stored.delete(save=False)
