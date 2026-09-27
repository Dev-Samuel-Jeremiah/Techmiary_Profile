"""
Create the standard proposal templates.

These are starting points for the commonest engagements, so a proposal begins
as a few edits rather than a blank page. Prices are placeholders — they are
the first thing to change for a real client.
"""
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from proposals.models import ProposalTemplate, TemplateItem

PLACEHOLDER = "[review price]"

TEMPLATES = [
    {
        "name": "School Management System",
        "summary": "A single system for admissions, academics, fees, attendance and parent communication.",
        "timeline": 12,
        "background": (
            "Most schools we speak to run admissions on paper, results in spreadsheets, "
            "fees in a cash book and parent communication over WhatsApp. Each record is "
            "correct on its own, but nothing reconciles: a question about one pupil means "
            "opening three systems, and a termly report is rebuilt by hand every time.\n\n"
            "This proposal replaces those with one record per pupil, shared by every part "
            "of the school that needs it."
        ),
        "approach": (
            "1. Discovery. We sit with your administrators and walk through a term as it "
            "actually runs — admission to report card — and write down the rules your "
            "school uses, including the exceptions.\n\n"
            "2. Data migration. Existing pupil and staff records are imported and "
            "reconciled. Anything ambiguous goes to a review queue rather than being "
            "guessed at.\n\n"
            "3. Build and review. Modules are delivered in the order above, with a working "
            "system to look at every two weeks. You can change your mind cheaply while it "
            "is still being built.\n\n"
            "4. Training and handover. Administrators and teachers are trained on the live "
            "system with your own data, not a demo.\n\n"
            "5. Support. The system is hosted, backed up and maintained by us."
        ),
        "assumptions": (
            "The school provides existing pupil and staff records in a readable format "
            "(spreadsheet, CSV or database export)\n"
            "One member of staff is available as the point of contact for decisions\n"
            "Internet access is available at the school for administrator use\n"
            "Content such as the school crest and letterhead is supplied by the school"
        ),
        "exclusions": (
            "Hardware — computers, tablets, printers or networking equipment\n"
            "Third-party charges such as SMS credit and payment gateway fees, which are billed at cost\n"
            "Data entry of historical records beyond the agreed migration scope\n"
            "Ongoing internet connectivity at the school"
        ),
        "payment_terms": (
            "A deposit is payable on acceptance to schedule the work and begin discovery. "
            "The balance falls due on delivery of the final module, before handover.\n\n"
            "Hosting, backups and support are billed annually in advance, starting after "
            "the handover date. The first year is included in the figure above."
        ),
        "items": [
            ("Discovery and system design",
             "On-site sessions with your administrators, a written specification and the data model.",
             1, "engagement", "450000"),
            ("Student records and admissions",
             "Admissions intake, pupil profiles, classes, streams and subject allocation.",
             1, "module", "650000"),
            ("Academics and results",
             "Continuous assessment, examinations, automated grading and end-of-term broadsheets.",
             1, "module", "850000"),
            ("Fees and payments",
             "Invoicing, part payments, outstanding balances, receipts and reconciliation.",
             1, "module", "750000"),
            ("Attendance",
             "Daily register capture with per-term and per-pupil summaries.",
             1, "module", "350000"),
            ("Parent and staff portals",
             "Separate logins for staff, parents and pupils over one academic record.",
             1, "module", "550000"),
            ("Data migration",
             "Import and reconciliation of existing pupil and staff records, with a manual review queue.",
             1, "engagement", "300000"),
            ("Training and handover",
             "Two on-site training days and a written administrator guide.",
             2, "day", "125000"),
            ("Hosting, backups and support — year one",
             "Server, daily backups, security updates and support during school hours.",
             1, "year", "420000"),
        ],
        "milestones": [
            ("Discovery and sign-off", "Requirements agreed and specification signed.", 1, 2, "20"),
            ("Core records live", "Admissions, pupil records and classes in use.", 3, 6, "25"),
            ("Academics and fees", "Results and fee management delivered.", 7, 10, "30"),
            ("Portals, training, handover", "Portals live, staff trained, system handed over.", 11, 12, "25"),
        ],
    },
    {
        "name": "Custom Web Application",
        "summary": "A business-specific application built around how your organisation already works.",
        "timeline": 10,
        "background": (
            "Off-the-shelf software fits the average organisation. Where the process is the "
            "differentiator, it usually does not fit at all, and the gap is filled with "
            "spreadsheets that only one person understands."
        ),
        "approach": (
            "Discovery, data model, then iterative delivery with a working system to review "
            "every two weeks. Deployed to infrastructure we run and maintain."
        ),
        "assumptions": (
            "A single decision-maker is available for weekly review\n"
            "Existing data can be exported in a machine-readable format\n"
            "Third-party systems to integrate with expose an API"
        ),
        "exclusions": (
            "Hardware and networking\n"
            "Third-party licence and API charges, billed at cost\n"
            "Mobile applications for app stores, quoted separately"
        ),
        "payment_terms": (
            "Deposit on acceptance, balance on delivery. Hosting and support billed annually "
            "in advance after handover."
        ),
        "items": [
            ("Discovery and specification", "Process mapping, data model and written scope.", 1, "engagement", "400000"),
            ("Application build", "Core application, delivered in reviewable increments.", 1, "engagement", "1800000"),
            ("Integrations", "Connections to the third-party services agreed at discovery.", 1, "engagement", "450000"),
            ("Deployment and hardening", "Server provisioning, TLS, backups and monitoring.", 1, "engagement", "250000"),
            ("Training and handover", "Training session and written documentation.", 1, "day", "125000"),
            ("Hosting and support — year one", "Server, backups, updates and support.", 1, "year", "380000"),
        ],
        "milestones": [
            ("Discovery complete", "Scope and data model signed off.", 1, 2, "20"),
            ("First working increment", "Core workflow usable end to end.", 3, 5, "30"),
            ("Feature complete", "All agreed functionality delivered.", 6, 9, "30"),
            ("Deployment and handover", "Live, trained and handed over.", 10, 10, "20"),
        ],
    },
]


class Command(BaseCommand):
    help = "Create the standard proposal templates. Idempotent."

    @transaction.atomic
    def handle(self, *args, **options):
        for spec in TEMPLATES:
            template, created = ProposalTemplate.objects.get_or_create(
                slug=slugify(spec["name"]),
                defaults={
                    "name": spec["name"],
                    "summary": spec["summary"],
                    "background": spec["background"],
                    "approach": spec["approach"],
                    "assumptions": spec["assumptions"],
                    "exclusions": spec["exclusions"],
                    "payment_terms": spec["payment_terms"],
                    "default_timeline_weeks": spec["timeline"],
                },
            )
            if not created:
                self.stdout.write(f"  = {template.name} (already present)")
                continue

            TemplateItem.objects.bulk_create([
                TemplateItem(
                    template=template, title=t, description=d,
                    quantity=Decimal(str(q)), unit=u, unit_price=Decimal(p),
                    display_order=i,
                )
                for i, (t, d, q, u, p) in enumerate(spec["items"], start=1)
            ])
            self.stdout.write(self.style.SUCCESS(
                f"  + {template.name} ({len(spec['items'])} line items)"
            ))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Proposal templates ready."))
        self.stdout.write(
            "Prices are placeholders. In the admin: Proposals → Add, pick a template,\n"
            "save, then edit the wording and figures for that client and use\n"
            "“Download proposal PDF”."
        )
