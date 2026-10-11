"""
Load the school system questionnaire into the question bank.

The questions come from ``questionnaires/data/school_questionnaire.json``,
extracted from the original questionnaire page. Idempotent: sections and
questions that already exist are left as the admin edited them, and only
missing ones are added. ``--reset`` restores the original wording and order of
every bundled question (questions the admin added are kept).
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from questionnaires.models import Question, QuestionSection

DATA = Path(__file__).resolve().parents[2] / "data" / "school_questionnaire.json"


def question_fields(q, order):
    return {
        "qtype": q["type"],
        "text": q["text"],
        "options": q.get("o", []),
        "per_section": bool(q.get("per")),
        "long_answer": bool(q.get("long")),
        "no_other": bool(q.get("noOther")),
        "ask_who": q.get("who", ""),
        "accept": q.get("accept", ""),
        "single_file": bool(q.get("single")),
        "grid_rows": q.get("rows", []),
        "grid_columns": q.get("cols", []),
        "display_order": order,
        "is_active": True,
    }


class Command(BaseCommand):
    help = "Load the school system questionnaire into the question bank."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true",
                            help="Restore the original wording of every bundled question.")

    @transaction.atomic
    def handle(self, *args, reset=False, **options):
        sections = json.loads(DATA.read_text(encoding="utf-8"))
        added_s = added_q = restored = 0
        for s_order, sec in enumerate(sections, start=1):
            section, created = QuestionSection.objects.get_or_create(
                code=sec["id"],
                defaults={"title": sec["title"], "handled_by": sec["by"], "display_order": s_order * 10},
            )
            added_s += created
            if reset and not created:
                section.title, section.handled_by = sec["title"], sec["by"]
                section.display_order, section.is_active = s_order * 10, True
                section.save()
            for q_order, q in enumerate(sec["qs"], start=1):
                fields = question_fields(q, q_order * 10)
                existing = Question.objects.filter(code=q["code"]).first()
                if existing is None:
                    Question.objects.create(section=section, code=q["code"], **fields)
                    added_q += 1
                elif reset:
                    for k, v in fields.items():
                        setattr(existing, k, v)
                    existing.section = section
                    existing.save()
                    restored += 1
        self.stdout.write(self.style.SUCCESS(
            f"Questionnaire ready: {added_s} section(s) and {added_q} question(s) added"
            + (f", {restored} restored to the original wording." if reset else ".")
        ))
        self.stdout.write(f"Bank now holds {Question.objects.count()} questions in "
                          f"{QuestionSection.objects.count()} sections.")
