"""
Create the school price list.

The items are the modules and services the company actually delivers — the
modules of its school platforms (Techmiary Cloud, WDA SMS), the offline result
manager and the mobile apps. Prices are deliberately left at zero: a price is
a business decision, so they are set in the control panel (Price list) before
a quotation can be issued.

Idempotent: existing items, and any prices already set, are left untouched.
"""
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from proposals.models import PriceListItem as P

ITEMS = [
    # name, group, billing, unit, default qty, selected by default, description
    ("System setup & configuration", P.GROUP_MODULE, P.BILL_ONE_OFF, "", 1, True,
     "Your school configured on the platform: sessions, terms, classes, arms, subjects, grading and branding."),
    ("Student records & admissions", P.GROUP_MODULE, P.BILL_ONE_OFF, "", 1, True,
     "Admissions, student profiles with photos, guardians, class allocation and end-of-session promotion."),
    ("Academics & timetable", P.GROUP_MODULE, P.BILL_ONE_OFF, "", 1, True,
     "Subjects, teacher allocation and a timetable builder."),
    ("Results & report cards", P.GROUP_MODULE, P.BILL_ONE_OFF, "", 1, True,
     "Score entry, automatic totals, grades and positions, broadsheets and printable report cards."),
    ("Computer-based testing (CBT)", P.GROUP_MODULE, P.BILL_ONE_OFF, "", 1, False,
     "Online examinations and tests, with scores feeding the results module."),
    ("Fees, wallets & online payments", P.GROUP_MODULE, P.BILL_ONE_OFF, "", 1, True,
     "Fee structures, student wallets, Paystack online payments, payment approval and PDF receipts."),
    ("Parent & student portals", P.GROUP_MODULE, P.BILL_ONE_OFF, "", 1, True,
     "Separate sign-ins for parents and students to see results, fees and announcements."),
    ("Communications: email & SMS", P.GROUP_MODULE, P.BILL_ONE_OFF, "", 1, False,
     "Announcements, fee reminders and result notifications by email and SMS."),
    ("Staff & payroll", P.GROUP_MODULE, P.BILL_ONE_OFF, "", 1, False,
     "Staff records and salary processing."),
    ("Hostel & boarding", P.GROUP_MODULE, P.BILL_ONE_OFF, "", 1, False,
     "Rooms and beds, boarder profiles, exeats, visitors, incidents and hostel billing."),
    ("Inventory & assets", P.GROUP_MODULE, P.BILL_ONE_OFF, "", 1, False,
     "Asset tracking, stock movements and maintenance records."),
    ("ID cards", P.GROUP_MODULE, P.BILL_ONE_OFF, "", 1, False,
     "Student identity cards generated from the student record."),
    ("Online admission portal", P.GROUP_MODULE, P.BILL_ONE_OFF, "", 1, False,
     "A public application form with online payment of the admission fee."),

    ("Data migration", P.GROUP_SERVICE, P.BILL_ONE_OFF, "", 1, True,
     "Existing student and staff records imported from your spreadsheets and checked with you."),
    ("Staff training", P.GROUP_SERVICE, P.BILL_ONE_OFF, "day", 1, True,
     "Hands-on training for administrators and teachers, on your own data."),
    ("Offline result manager (desktop)", P.GROUP_SERVICE, P.BILL_ONE_OFF, "installation", 1, False,
     "Desktop software for Windows and Linux that computes and prints term results without the internet."),
    ("Android & iOS app", P.GROUP_SERVICE, P.BILL_ONE_OFF, "", 1, False,
     "Your school's own app for Android and iPhone, built on the platform."),
    ("School website", P.GROUP_SERVICE, P.BILL_ONE_OFF, "", 1, False,
     "A public website for the school, linked to the admission portal."),
    ("SMS credit", P.GROUP_SERVICE, P.BILL_ONE_OFF, "unit", 1000, False,
     "Prepaid SMS units for notifications and reminders."),

    ("Platform licence", P.GROUP_RECURRING, P.BILL_PER_STUDENT_TERM, "", 1, True,
     "Use of the platform for each enrolled student, billed at the start of each term."),
    ("Hosting, backups & support", P.GROUP_RECURRING, P.BILL_PER_YEAR, "year", 1, True,
     "Secure hosting, daily backups, updates and support during school hours."),
]


class Command(BaseCommand):
    help = "Create the school price list (prices start at zero). Idempotent."

    @transaction.atomic
    def handle(self, *args, **options):
        created = 0
        for order, (name, group, billing, unit, qty, default, desc) in enumerate(ITEMS, start=1):
            _, was_created = P.objects.get_or_create(
                name=name,
                defaults={
                    "group": group, "billing": billing, "unit": unit,
                    "default_quantity": Decimal(str(qty)),
                    "selected_by_default": default, "description": desc,
                    "display_order": order, "unit_price": Decimal("0"),
                },
            )
            created += was_created
        unpriced = P.objects.filter(is_active=True, unit_price__lte=0).count()
        self.stdout.write(self.style.SUCCESS(f"Price list ready: {created} new item(s)."))
        if unpriced:
            self.stdout.write(
                f"{unpriced} item(s) have no price yet. Set them in the control panel "
                "under Company → Price list before issuing quotations."
            )
