from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import BlogCategory, BlogPost


class BlogPostModelTests(TestCase):
    def test_slug_and_published_at_are_set_on_publish(self):
        post = BlogPost.objects.create(
            title="Deploying Django on a VPS",
            excerpt="Notes on Nginx and Gunicorn.",
            content="Body text.",
            published=True,
        )
        self.assertEqual(post.slug, "deploying-django-on-a-vps")
        self.assertIsNotNone(post.published_at)

    def test_draft_has_no_publication_date(self):
        post = BlogPost.objects.create(
            title="Draft", excerpt="x", content="y", published=False
        )
        self.assertIsNone(post.published_at)

    def test_reading_time_is_at_least_one_minute(self):
        post = BlogPost.objects.create(title="Short", excerpt="x", content="one two")
        self.assertEqual(post.reading_time, 1)

    def test_category_slug(self):
        category = BlogCategory.objects.create(name="SaaS Development")
        self.assertEqual(category.slug, "saas-development")


class BlogViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.author = User.objects.create_user("samuel", password="not-a-real-password")
        cls.category = BlogCategory.objects.create(name="Django")
        cls.published = BlogPost.objects.create(
            title="Structuring a Django project",
            excerpt="Settings, apps and templates.",
            content="A published article about project structure.",
            category=cls.category,
            author=cls.author,
            published=True,
        )
        cls.draft = BlogPost.objects.create(
            title="Unfinished thoughts",
            excerpt="Not ready.",
            content="Draft body.",
            published=False,
        )
        cls.future = BlogPost.objects.create(
            title="Scheduled article",
            excerpt="Later.",
            content="Future body.",
            published=True,
            published_at=timezone.now() + timezone.timedelta(days=5),
        )

    def test_list_shows_published_posts_only(self):
        response = self.client.get(reverse("blog:list"))
        self.assertContains(response, "Structuring a Django project")
        self.assertNotContains(response, "Unfinished thoughts")

    def test_scheduled_posts_are_not_listed_before_their_date(self):
        response = self.client.get(reverse("blog:list"))
        self.assertNotContains(response, "Scheduled article")

    def test_search_filters_results(self):
        response = self.client.get(reverse("blog:list"), {"q": "structure"})
        self.assertContains(response, "Structuring a Django project")
        response = self.client.get(reverse("blog:list"), {"q": "kubernetes"})
        self.assertContains(response, "No matching articles")

    def test_category_filter(self):
        response = self.client.get(reverse("blog:list"), {"category": self.category.slug})
        self.assertEqual(list(response.context["posts"]), [self.published])

    def test_detail_renders(self):
        response = self.client.get(self.published.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "A published article about project structure.")

    def test_detail_emits_blogposting_json_ld(self):
        body = self.client.get(self.published.get_absolute_url()).content.decode()
        self.assertIn('"@type": "BlogPosting"', body)

    def test_draft_detail_returns_404(self):
        self.assertEqual(self.client.get("/blog/unfinished-thoughts/").status_code, 404)

    def test_unknown_post_returns_404(self):
        self.assertEqual(self.client.get("/blog/no-such-post/").status_code, 404)

    def test_pagination_is_applied(self):
        for index in range(12):
            BlogPost.objects.create(
                title=f"Post number {index}",
                excerpt="x",
                content="y",
                published=True,
            )
        response = self.client.get(reverse("blog:list"))
        self.assertTrue(response.context["is_paginated"])


class CategoryFilterTests(TestCase):
    """Filter chips must only offer categories that actually have live posts."""

    def test_a_category_with_only_a_scheduled_post_is_not_offered(self):
        from datetime import timedelta
        from django.utils import timezone

        future = BlogCategory.objects.create(name="Upcoming")
        BlogPost.objects.create(
            title="Scheduled piece",
            slug="scheduled-piece",
            excerpt="Not live yet.",
            content="Body.",
            category=future,
            published=True,
            published_at=timezone.now() + timedelta(days=5),
        )
        response = self.client.get(reverse("blog:list"))
        self.assertNotContains(response, "Upcoming")
