"""Cache invalidation for the site-wide context.

Editors change content in the admin and expect the site to reflect it at once,
so the cached fragments are dropped on save or delete rather than waiting for
the timeout to lapse.
"""
from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import SiteSettings, SocialLink

CACHE_KEYS = (
    SiteSettings.SINGLETON_CACHE_KEY,
    "core:social-links",
    "core:nav",
)


def clear_site_context_cache():
    cache.delete_many(list(CACHE_KEYS))


@receiver(post_save, sender=SiteSettings)
@receiver(post_delete, sender=SiteSettings)
@receiver(post_save, sender=SocialLink)
@receiver(post_delete, sender=SocialLink)
def _invalidate_core(sender, **kwargs):
    clear_site_context_cache()


def register_related_signals():
    """Connected from ``CoreConfig.ready`` to avoid circular imports."""
    from careers.models import JobOpening
    from company.models import Industry, Solution
    from projects.models import Project

    for model in (Project, Solution, Industry, JobOpening):
        label = model._meta.label_lower
        post_save.connect(_invalidate_core, sender=model, dispatch_uid=f"core.{label}.save")
        post_delete.connect(_invalidate_core, sender=model, dispatch_uid=f"core.{label}.delete")
