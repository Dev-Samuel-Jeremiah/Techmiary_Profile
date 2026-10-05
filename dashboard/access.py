"""
Who may use the dashboard.

Access is granted by ``is_staff``, not ``is_superuser``: a company admin is a
member of staff with the permissions their job needs, and nobody should have
to hand out superuser rights to let someone write a proposal.

Superusers implicitly hold every permission, so the per-section checks below
let a superuser through without any special-casing.
"""
from django.contrib.auth.mixins import AccessMixin
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse

COMPANY_ADMIN_GROUP = "Company Admin"

# The permissions a company admin holds. Kept here rather than in a migration
# so the set can be re-applied after new models are added.
COMPANY_ADMIN_PERMISSIONS = [
    ("proposals", "proposal", ["add", "change", "delete", "view"]),
    ("proposals", "proposalitem", ["add", "change", "delete", "view"]),
    ("proposals", "proposalmilestone", ["add", "change", "delete", "view"]),
    ("proposals", "proposaltemplate", ["view"]),
    ("proposals", "schoolquotation", ["add", "change", "delete", "view"]),
    ("proposals", "schoolquotationline", ["add", "change", "delete", "view"]),
    # Setting prices is a company admin's job; retiring an item is done by
    # unticking Active, so delete is not granted.
    ("proposals", "pricelistitem", ["add", "change", "view"]),
    # The company's own profile: name, contact details, logo, favicon. These
    # feed the public site and every proposal letterhead, so a company admin
    # needs them. Content models (solutions, blog, team) stay excluded.
    ("core", "sitesettings", ["change", "view"]),
    ("contact", "contactmessage", ["change", "view"]),
    ("contact", "quoterequest", ["change", "view"]),
    ("contact", "newslettersubscriber", ["view"]),
    ("careers", "jobapplication", ["change", "view"]),
]


def sync_company_admin_group():
    """Create the group and (re)apply its permission set. Idempotent."""
    group, _ = Group.objects.get_or_create(name=COMPANY_ADMIN_GROUP)
    wanted = []
    for app_label, model, actions in COMPANY_ADMIN_PERMISSIONS:
        for action in actions:
            perm = Permission.objects.filter(
                content_type__app_label=app_label,
                content_type__model=model,
                codename=f"{action}_{model}",
            ).first()
            if perm:
                wanted.append(perm)
    group.permissions.set(wanted)
    return group, len(wanted)


class DashboardAccessMixin(AccessMixin):
    """
    Base for every dashboard view.

    Unauthenticated visitors are sent to the dashboard's own login page, not
    Django's admin login, so staff never see two different sign-in screens.
    A signed-in user without staff access gets 403 rather than a redirect
    loop.
    """

    required_permission = None

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            login_url = f"{reverse('dashboard:login')}?next={request.get_full_path()}"
            return redirect(login_url)
        if not user.is_active or not user.is_staff:
            raise PermissionDenied(
                "This area is for staff accounts. Ask an administrator for access."
            )
        if self.required_permission and not user.has_perm(self.required_permission):
            raise PermissionDenied(
                f"Your account does not have the “{self.required_permission}” permission."
            )
        return super().dispatch(request, *args, **kwargs)
