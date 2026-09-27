from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Site & Skills"

    def ready(self):
        from . import signals  # noqa: F401  (registers cache invalidation)

        signals.register_related_signals()
