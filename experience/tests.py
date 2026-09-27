import datetime

from django.test import TestCase
from django.urls import reverse

from .models import Experience, Responsibility


class ExperienceModelTests(TestCase):
    def test_period_for_a_current_role(self):
        role = Experience.objects.create(
            organization="Techmiary Technology Concepts",
            position="Software Engineer",
            start_date=datetime.date(2023, 1, 1),
            is_current=True,
        )
        self.assertEqual(role.period, "Jan 2023 — Present")
        self.assertEqual(str(role), "Software Engineer — Techmiary Technology Concepts")

    def test_period_for_a_finished_role(self):
        role = Experience.objects.create(
            organization="Example Ltd",
            position="Developer",
            start_date=datetime.date(2021, 3, 1),
            end_date=datetime.date(2022, 8, 1),
        )
        self.assertEqual(role.period, "Mar 2021 — Aug 2022")

    def test_technology_list_is_split(self):
        role = Experience.objects.create(
            organization="Example Ltd",
            position="Developer",
            start_date=datetime.date(2021, 3, 1),
            technologies="Python, Django , PostgreSQL",
        )
        self.assertEqual(role.technology_list, ["Python", "Django", "PostgreSQL"])


class ExperienceViewTests(TestCase):
    def test_empty_timeline_shows_an_empty_state(self):
        response = self.client.get(reverse("experience:list"))
        self.assertContains(response, "No experience entries yet")

    def test_active_roles_and_their_responsibilities_are_listed(self):
        role = Experience.objects.create(
            organization="Techmiary Technology Concepts",
            position="Software Engineer",
            start_date=datetime.date(2023, 1, 1),
            is_current=True,
        )
        Responsibility.objects.create(experience=role, text="Built and deployed Django applications.")
        Experience.objects.create(
            organization="Hidden Org",
            position="Hidden Role",
            start_date=datetime.date(2020, 1, 1),
            is_active=False,
        )
        response = self.client.get(reverse("experience:list"))
        self.assertContains(response, "Built and deployed Django applications.")
        self.assertNotContains(response, "Hidden Role")
