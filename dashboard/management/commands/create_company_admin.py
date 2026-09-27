"""
Create a company admin: a staff account that can use the dashboard without
being a superuser.

    python manage.py create_company_admin amina --email amina@techmiary.tech

The account gets ``is_staff`` and joins the "Company Admin" group, which
carries permissions for proposals, enquiries, quote requests and job
applications — and nothing else. Site content stays with superusers.
"""
import getpass

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from dashboard.access import COMPANY_ADMIN_GROUP, sync_company_admin_group


class Command(BaseCommand):
    help = "Create (or promote) a staff account with dashboard access."

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("--email", default="")
        parser.add_argument("--first-name", default="")
        parser.add_argument("--last-name", default="")
        parser.add_argument(
            "--password",
            help="Set non-interactively. Omit to be prompted, which is safer: "
                 "a password passed here is visible in your shell history.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        username = options["username"]

        group, perm_count = sync_company_admin_group()

        user = User.objects.filter(username=username).first()
        created = user is None
        if created:
            password = options["password"]
            if not password:
                password = getpass.getpass("Password: ")
                confirm = getpass.getpass("Password (again): ")
                if password != confirm:
                    raise CommandError("The two passwords did not match.")
            try:
                validate_password(password)
            except ValidationError as exc:
                raise CommandError("Password rejected: " + "; ".join(exc.messages))

            user = User.objects.create_user(
                username=username,
                email=options["email"],
                password=password,
                first_name=options["first_name"],
                last_name=options["last_name"],
            )

        user.is_staff = True          # required for dashboard access
        user.is_superuser = False     # a company admin is not a superuser
        if options["email"]:
            user.email = options["email"]
        if options["first_name"]:
            user.first_name = options["first_name"]
        if options["last_name"]:
            user.last_name = options["last_name"]
        user.save()
        user.groups.add(group)

        verb = "Created" if created else "Promoted existing account"
        self.stdout.write(self.style.SUCCESS(
            f"{verb}: {username} — staff, in “{COMPANY_ADMIN_GROUP}” "
            f"({perm_count} permissions)."
        ))
        self.stdout.write("They can now sign in at /dashboard/login/")
