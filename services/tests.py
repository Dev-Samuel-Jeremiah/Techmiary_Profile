from django.test import TestCase
from django.urls import reverse

from .models import Service


class ServiceModelTests(TestCase):
    def test_slug_and_deliverable_parsing(self):
        service = Service.objects.create(
            title="SaaS Development",
            summary="Multi-tenant platforms.",
            deliverables="Tenant isolation\nSubscription billing\n\nRole-based access",
        )
        self.assertEqual(service.slug, "saas-development")
        self.assertEqual(
            service.deliverable_list,
            ["Tenant isolation", "Subscription billing", "Role-based access"],
        )
        self.assertEqual(str(service), "SaaS Development")


class ServiceViewTests(TestCase):
    def test_empty_list_shows_an_empty_state(self):
        response = self.client.get(reverse("services:list"))
        self.assertContains(response, "No services listed yet")

    def test_only_active_services_are_shown(self):
        Service.objects.create(title="Custom Software Development", summary="Internal systems.")
        Service.objects.create(title="Retired Service", summary="Gone.", is_active=False)
        response = self.client.get(reverse("services:list"))
        self.assertContains(response, "Custom Software Development")
        self.assertNotContains(response, "Retired Service")
