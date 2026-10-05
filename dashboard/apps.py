from django.apps import AppConfig
from django.db.models.signals import post_migrate


def _sync_group(sender, **kwargs):
    # Re-apply the Company Admin permission set after every migrate, so a new
    # model's permissions reach existing company admins without a manual step.
    # Runs for this app only, by which point every earlier app's permissions
    # (proposals, contact, core...) have been created.
    from .access import sync_company_admin_group

    sync_company_admin_group()


class DashboardConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dashboard"
    verbose_name = "Staff dashboard"

    def ready(self):
        post_migrate.connect(_sync_group, sender=self, dispatch_uid="dashboard.sync_company_admin_group")
