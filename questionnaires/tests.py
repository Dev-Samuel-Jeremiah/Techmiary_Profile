"""School questionnaires: the bank, saving answers and files, and editing questions."""
import json
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from dashboard.access import sync_company_admin_group

from .models import Question, QuestionnaireResponse, QuestionSection, ResponseFile, bank

PRIVATE = tempfile.mkdtemp(prefix="questionnaire-tests-")


@override_settings(PRIVATE_MEDIA_ROOT=PRIVATE)
class QuestionnaireTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_questionnaire", verbosity=0)
        group, _ = sync_company_admin_group()
        cls.admin = get_user_model().objects.create_user("qadmin", "q@example.com", "pw-Q-2026!", is_staff=True)
        cls.admin.groups.add(group)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(PRIVATE, ignore_errors=True)

    def setUp(self):
        self.client.force_login(self.admin)

    def new_response(self, name=""):
        self.client.post(reverse("dashboard:questionnaire_new"), {"school_name": name})
        return QuestionnaireResponse.objects.latest("pk")

    def api(self, r, path):
        return reverse("dashboard:questionnaire_api_root", kwargs={"pk": r.pk}).rstrip("/") + path

    # -- The bank ----------------------------------------------------------
    def test_seeded_bank_is_the_original_questionnaire(self):
        original = json.loads(
            (QuestionSection._meta.app_config.path and open(
                f"{QuestionSection._meta.app_config.path}/data/school_questionnaire.json", encoding="utf-8"
            ).read())
        )
        self.assertEqual(bank(), original)
        self.assertEqual(Question.objects.count(), 401)
        self.assertEqual(QuestionSection.objects.count(), 24)

    def test_seeding_twice_keeps_admin_edits(self):
        q = Question.objects.get(code="A1")
        q.text = "School's registered name?"
        q.save()
        call_command("seed_questionnaire", verbosity=0)
        self.assertEqual(Question.objects.get(code="A1").text, "School's registered name?")
        call_command("seed_questionnaire", "--reset", verbosity=0)
        self.assertEqual(Question.objects.get(code="A1").text, "What is the full name of the school?")

    # -- Pages -----------------------------------------------------------------
    def test_fill_page_carries_the_bank_and_save_settings(self):
        r = self.new_response("Hillside Academy")
        page = self.client.get(r.get_absolute_url())
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, 'id="sq-bank"')
        self.assertContains(page, 'id="sq-config"')
        self.assertContains(page, "js/questionnaire.js")
        self.assertContains(page, "School System Questionnaire")
        self.assertContains(page, "What is the full name of the school?")
        # Voice notes need the microphone, which the rest of the site blocks.
        self.assertIn("microphone=(self)", page["Permissions-Policy"])

    def test_microphone_stays_blocked_elsewhere(self):
        page = self.client.get(reverse("dashboard:questionnaire_list"))
        self.assertIn("microphone=()", page["Permissions-Policy"])

    def test_list_shows_progress(self):
        self.new_response("Hillside Academy")
        page = self.client.get(reverse("dashboard:questionnaire_list"))
        self.assertContains(page, "Hillside Academy")
        self.assertContains(page, "1 of 401 answered")

    # -- Saving answers -------------------------------------------------------
    def test_state_round_trip_and_progress(self):
        r = self.new_response()
        state = {
            "answers": {"A1": "Unity College", "A3": "Yes", "A12|NP": "240", "A12|SEC": "180",
                        "B0|r0|login": "Yes", "A5": [], "A6": ""},
            "notes": {"A3": "Two campuses planned"}, "meta": {"A": {"by": "Mrs Bello, Proprietor"}},
            "files": {"A0": [{"id": 999, "url": "/evil"}]},  # must be ignored
            "updatedAt": 1760000000000,
        }
        res = self.client.post(self.api(r, "/state/"), json.dumps(state), content_type="application/json")
        self.assertEqual(res.status_code, 200)
        r.refresh_from_db()
        self.assertEqual(r.school_name, "Unity College")
        self.assertEqual(r.answered_count, 4)  # A1, A3, A12, B0 — empty A5/A6 do not count
        got = self.client.get(self.api(r, "/state/")).json()
        self.assertEqual(got["answers"]["A12|SEC"], "180")
        self.assertEqual(got["notes"]["A3"], "Two campuses planned")
        self.assertEqual(got["updatedAt"], 1760000000000)
        self.assertEqual(got["files"], {})  # the client cannot inject files
        self.assertEqual(r.students_by_section()["Nursery & Primary"], 240)

    def test_api_answers_json_not_a_redirect_when_signed_out(self):
        r = self.new_response()
        self.client.logout()
        res = self.client.get(self.api(r, "/state/"))
        self.assertEqual(res.status_code, 403)
        self.assertEqual(res["Content-Type"], "application/json")

    def test_rejects_bad_json(self):
        r = self.new_response()
        res = self.client.post(self.api(r, "/state/"), "not json", content_type="application/json")
        self.assertEqual(res.status_code, 400)

    # -- Files -------------------------------------------------------------------
    def upload(self, r, name="letterhead.pdf", data=b"%PDF-1.4 test", ctype="application/pdf", code="A21", **extra):
        return self.client.post(self.api(r, "/files/"), {
            "file": SimpleUploadedFile(name, data, content_type=ctype), "question": code, **extra,
        })

    def test_upload_download_and_remove_a_file(self):
        r = self.new_response()
        res = self.upload(r)
        self.assertEqual(res.status_code, 201)
        f = res.json()
        self.assertEqual(f["name"], "letterhead.pdf")
        record = ResponseFile.objects.get(pk=f["id"])
        self.assertTrue(record.file.path.startswith(PRIVATE))  # never under the public media root
        r.refresh_from_db()
        self.assertEqual(r.answered_count, 1)

        dl = self.client.get(f["url"])
        self.assertEqual(dl.status_code, 200)
        self.assertEqual(b"".join(dl.streaming_content), b"%PDF-1.4 test")

        self.client.logout()
        self.assertEqual(self.client.get(f["url"]).status_code, 302)
        self.client.force_login(self.admin)

        res = self.client.delete(self.api(r, f"/files/{f['id']}/"))
        self.assertEqual(res.status_code, 200)
        self.assertFalse(ResponseFile.objects.filter(pk=f["id"]).exists())

    def test_voice_note_is_kept_as_a_voice_note(self):
        r = self.new_response()
        res = self.upload(r, "voice-note-A3-0m12s.webm", b"\x1aE\xdf\xa3", "audio/webm", "A3",
                          kind="voice", label="Voice note (0:12)")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()["kind"], "voice")
        self.assertEqual(res.json()["label"], "Voice note (0:12)")

    def test_rejects_unsafe_file_types(self):
        r = self.new_response()
        for name, ctype in [("x.html", "text/html"), ("logo.svg", "image/svg+xml"), ("run.exe", "application/octet-stream")]:
            res = self.upload(r, name, b"<script>", ctype)
            self.assertEqual(res.status_code, 415, name)
        self.assertFalse(ResponseFile.objects.exists())

    def test_delete_response_removes_files_from_storage(self):
        r = self.new_response("Gone School")
        record = ResponseFile.objects.get(pk=self.upload(r).json()["id"])
        path = record.file.path
        self.assertContains(self.client.get(reverse("dashboard:questionnaire_delete", args=[r.pk])), "Yes, delete it")
        self.client.post(reverse("dashboard:questionnaire_delete", args=[r.pk]))
        self.assertFalse(QuestionnaireResponse.objects.filter(pk=r.pk).exists())
        import os
        self.assertFalse(os.path.exists(path))

    # -- Editing the bank --------------------------------------------------------
    def test_add_a_choice_question_and_it_reaches_the_page(self):
        section = QuestionSection.objects.get(code="A")
        form = self.client.get(reverse("dashboard:question_new") + f"?section={section.pk}")
        self.assertEqual(form.context["form"].initial["code"], "A22")
        res = self.client.post(reverse("dashboard:question_new"), {
            "section": section.pk, "code": "A22", "qtype": "many", "text": "Which uniforms do you have?",
            "options_text": "Day wear\nSports wear\n\nFriday wear", "display_order": 220, "is_active": "on",
        })
        self.assertEqual(res.status_code, 302)
        q = Question.objects.get(code="A22")
        self.assertEqual(q.options, ["Day wear", "Sports wear", "Friday wear"])
        a = next(s for s in bank() if s["id"] == "A")
        self.assertEqual(a["qs"][-1], {"code": "A22", "type": "many", "text": "Which uniforms do you have?",
                                       "o": ["Day wear", "Sports wear", "Friday wear"]})

    def test_add_a_table_question(self):
        section = QuestionSection.objects.get(code="J")
        res = self.client.post(reverse("dashboard:question_new"), {
            "section": section.pk, "code": "J18", "qtype": "grid", "text": "Which buses do you have?",
            "grid_rows_text": "Bus 1\nBus 2",
            "grid_columns_text": "Seats | num\nCondition | one | Good, Fair, Poor | no other",
            "display_order": 180, "is_active": "on",
        })
        self.assertEqual(res.status_code, 302)
        q = Question.objects.get(code="J18")
        self.assertEqual(q.grid_rows, ["Bus 1", "Bus 2"])
        self.assertEqual(q.grid_columns, [
            {"k": "seats", "label": "Seats", "type": "num"},
            {"k": "condition", "label": "Condition", "type": "one", "o": ["Good", "Fair", "Poor"], "noOther": True},
        ])

    def test_editing_a_table_keeps_column_keys_so_answers_stay(self):
        q = Question.objects.get(code="B0")
        form = self.client.get(reverse("dashboard:question_edit", args=[q.pk])).context["form"]
        self.assertIn("Needs a login? | yn", form.fields["grid_columns_text"].initial)
        res = self.client.post(reverse("dashboard:question_edit", args=[q.pk]), {
            "section": q.section_id, "code": "B0", "qtype": "grid", "text": q.text,
            "grid_rows_text": "\n".join(q.grid_rows),
            "grid_columns_text": form.fields["grid_columns_text"].initial,
            "display_order": q.display_order, "is_active": "on",
        })
        self.assertEqual(res.status_code, 302)
        self.assertEqual([c["k"] for c in Question.objects.get(code="B0").grid_columns], ["login", "secs", "tasks"])

    def test_choice_question_needs_options_and_codes_are_checked(self):
        section = QuestionSection.objects.get(code="A")
        res = self.client.post(reverse("dashboard:question_new"), {
            "section": section.pk, "code": "A 23", "qtype": "one", "text": "Pick?", "options_text": "",
            "display_order": 1,
        })
        self.assertEqual(res.status_code, 200)
        errors = res.context["form"].errors
        self.assertIn("options_text", errors)
        self.assertIn("code", errors)

    def test_remove_a_question_keeps_existing_answers(self):
        r = self.new_response()
        self.client.post(self.api(r, "/state/"), json.dumps({"answers": {"A3": "Yes"}, "updatedAt": 1}),
                         content_type="application/json")
        q = Question.objects.get(code="A3")
        page = self.client.get(reverse("dashboard:question_delete", args=[q.pk]))
        self.assertContains(page, "1 school has already answered it")
        self.client.post(reverse("dashboard:question_delete", args=[q.pk]))
        self.assertFalse(Question.objects.filter(code="A3").exists())
        r.refresh_from_db()
        self.assertEqual(r.data["answers"]["A3"], "Yes")
        self.assertNotIn("A3", [q["code"] for s in bank() for q in s["qs"]])

    def test_hidden_question_leaves_the_page_but_not_the_bank(self):
        Question.objects.filter(code="A2").update(is_active=False)
        self.assertNotIn("A2", [q["code"] for s in bank() for q in s["qs"]])
        self.assertContains(self.client.get(reverse("dashboard:question_bank")), "1 hidden")

    def test_add_and_remove_a_section(self):
        res = self.client.post(reverse("dashboard:section_new"), {
            "code": "y", "title": "Transport routes", "handled_by": "Transport officer",
            "display_order": 250, "is_active": "on",
        })
        self.assertEqual(res.status_code, 302)
        section = QuestionSection.objects.get(code="Y")
        Question.objects.create(section=section, code="Y1", qtype="text", text="Which routes?")
        self.assertEqual(bank()[-1]["id"], "Y")
        self.client.post(reverse("dashboard:section_delete", args=[section.pk]))
        self.assertFalse(QuestionSection.objects.filter(code="Y").exists())

    # -- Into a quotation ----------------------------------------------------------
    def test_start_a_quotation_from_a_questionnaire(self):
        r = self.new_response()
        self.client.post(self.api(r, "/state/"), json.dumps({
            "answers": {"A1": "Unity College", "A2": "4 Ring Road, Jos", "A12|NP": "240", "A12|SEC": "180", "A12|ISL": "60"},
            "meta": {"A": {"by": "Mrs Bello"}}, "updatedAt": 1,
        }), content_type="application/json")
        page = self.client.get(reverse("dashboard:quotation_new") + f"?from_questionnaire={r.pk}")
        initial = page.context["form"].initial
        self.assertEqual((initial["school_name"], initial["student_count"], initial["contact_name"]),
                         ("Unity College", 480, "Mrs Bello"))
        self.client.post(reverse("dashboard:quotation_new"), {
            "school_name": "Unity College", "contact_name": "Mrs Bello", "school_type": "combined",
            "student_count": 480, "campus_count": 1, "deployment": "online", "from_questionnaire": r.pk,
        })
        r.refresh_from_db()
        self.assertIsNotNone(r.quotation)
        self.assertEqual(r.quotation.student_count, 480)
