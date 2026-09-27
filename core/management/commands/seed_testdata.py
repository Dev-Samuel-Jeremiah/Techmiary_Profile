"""
Fill every model with sample data so the whole site can be exercised locally.

This is NOT the content seeder. ``seed_portfolio`` writes the owner's real
information and deliberately invents nothing; this command layers plausible
but fabricated test content on top of it — case-study narrative, blog posts,
employment history, enquiries, social links and generated placeholder images —
so that every template, filter, pagination path and admin list has something
to render.

Nothing written here should be treated as fact. Run ``--flush`` to remove it
again before putting real content in, and never run it against production.

    python manage.py seed_testdata              # base content + sample data
    python manage.py seed_testdata --flush      # delete sample data, then reseed
    python manage.py seed_testdata --no-images  # skip generated placeholder images
"""
import random
from datetime import date, timedelta
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from blog.models import BlogCategory, BlogPost
from careers.models import Department, JobApplication, JobOpening
from company.models import (
    Client,
    Milestone,
    Resource,
    ResourceCategory,
    Solution,
    TeamMember,
    Testimonial,
)
from contact.models import ContactMessage, NewsletterSubscriber, QuoteRequest
from core.models import Partner, SiteSettings, SocialLink
from experience.models import Experience, Responsibility
from projects.models import Project, ProjectChallenge, ProjectFeature, ProjectImage
from services.models import Service

# Every generated string carries this so fabricated rows are obvious in the
# admin and easy to find again.
MARKER = "[sample]"

# Placeholder images are tinted from the site palette so generated art does
# not clash with the design while it stands in for real photography.
SAMPLE_HUES = [
    (27, 77, 255),
    (10, 37, 64),
    (0, 184, 169),
    (18, 59, 208),
    (51, 66, 91),
    (13, 42, 160),
]


def sample_hue(index):
    """Deterministic colour for a generated placeholder."""
    return SAMPLE_HUES[index % len(SAMPLE_HUES)]

TEST_USER = {
    "username": "testadmin",
    "email": "testadmin@example.com",
    "first_name": "Samuel",
    "last_name": "Jeremiah",
}
TEST_PASSWORD = "testpass123"

SITE_CONTACT = {
    "email": "hello@example.com",
    "phone": "+234 800 000 0000",
    "location": "Maiduguri, Borno State, Nigeria",
    "show_email_publicly": True,
    "github_url": "https://github.com/example",
    "linkedin_url": "https://www.linkedin.com/in/example/",
    "twitter_url": "https://x.com/example",
    "whatsapp_url": "https://wa.me/2348000000000",
    "twitter_handle": "example",
}

SOCIAL_LINKS = [
    ("GitHub", "https://github.com/example", "github", 1, True),
    ("LinkedIn", "https://www.linkedin.com/in/example/", "linkedin", 2, True),
    ("X", "https://x.com/example", "x", 3, True),
    ("WhatsApp", "https://wa.me/2348000000000", "whatsapp", 4, True),
    ("YouTube", "https://www.youtube.com/@example", "youtube", 5, False),
    ("Company site", "https://example.com", "link", 6, True),
]

# Per-project case-study body, keyed by the slugs seed_portfolio creates.
PROJECT_DETAIL = {
    "techmiary-cloud": {
        "status": Project.STATUS_LIVE,
        "year": 2024,
        "client": f"{MARKER} Sample Education Group",
        "github_url": "https://github.com/example/techmiary-cloud",
        "problem": (
            f"{MARKER} Schools in the region ran admissions, results, fee collection and "
            "parent communication across paper registers, spreadsheets and WhatsApp groups. "
            "Reconciling a term's fees against the register took days, and no one could "
            "answer a question about a pupil without opening three systems."
        ),
        "solution": (
            f"{MARKER} A multi-tenant Django platform where each school gets an isolated "
            "dataset behind one deployment. Academics, finance, attendance and messaging "
            "share a single student record, and role-based permissions separate what an "
            "administrator, a class teacher and a parent can each see."
        ),
        "result": (
            f"{MARKER} Term-end result compilation moved from a manual spreadsheet merge to "
            "a single generated broadsheet, and fee reconciliation now runs against the same "
            "record as the register."
        ),
        "architecture_description": (
            f"{MARKER} Nginx terminates TLS and serves hashed static files via WhiteNoise. "
            "Gunicorn runs the Django application behind it on an Ubuntu VPS. PostgreSQL "
            "holds tenant data with a schema-per-tenant layout; uploaded media goes to "
            "Cloudflare R2 and is served through the CDN."
        ),
        "features": [
            ("Multi-tenant school isolation", "Each school has its own data, branding and subdomain behind a single deployment."),
            ("Academic records", "Class lists, subject allocation, continuous assessment and end-of-term broadsheets."),
            ("Fee management", "Invoicing, part payments, outstanding balances and Paystack reconciliation."),
            ("Attendance", "Daily register capture with per-term and per-pupil summaries."),
            ("Parent communication", "Announcements, result release notifications and direct messages to guardians."),
            ("Role-based access", "Separate permission sets for proprietors, administrators, teachers and parents."),
        ],
        "challenges": [
            ("Tenant isolation without duplicating deployments", "Routing every query through a tenant-scoped manager, with a test suite that fails any queryset touching the base manager directly."),
            ("Result computation under load", "Broadsheet generation ran N+1 queries per pupil; restructuring around prefetched assessment rows cut it to a fixed number of queries per class."),
            ("Offline-tolerant attendance", "Registers are often taken where connectivity drops, so capture is queued client-side and reconciled on reconnect."),
        ],
    },
    "diction-masters": {
        "status": Project.STATUS_LIVE,
        "year": 2023,
        "github_url": "https://github.com/example/diction-masters",
        "problem": (
            f"{MARKER} Pronunciation practice needs immediate feedback, but the material "
            "available to learners was static text and recorded audio with no way to check "
            "whether an attempt was actually correct."
        ),
        "solution": (
            f"{MARKER} A lesson platform pairing a graded vocabulary corpus with "
            "text-to-speech playback, per-word phonetic breakdowns and scored assessments "
            "that track which sounds a learner keeps missing."
        ),
        "result": (
            f"{MARKER} Learners work through structured units instead of loose word lists, "
            "and their weak phonemes surface in the progress view rather than being lost."
        ),
        "architecture_description": (
            f"{MARKER} Django serves lessons and assessments; generated audio is cached in "
            "object storage so a given word is synthesised once and reused across learners."
        ),
        "features": [
            ("Graded vocabulary units", "Words grouped by difficulty with definitions, usage examples and phonetic transcription."),
            ("Text-to-speech playback", "Synthesised reference audio for every entry, cached after first generation."),
            ("Scored assessments", "Multiple-choice and listening exercises with per-attempt scoring."),
            ("Progress tracking", "Per-learner history showing mastered units and recurring problem sounds."),
        ],
        "challenges": [
            ("Text-to-speech cost and latency", "Synthesising on every request was slow and expensive; audio is now generated once per word and served from cached object storage."),
            ("Phonetic accuracy", "Reconciling dictionary transcriptions against the synthesised output required a manual review pass over the seed corpus."),
        ],
    },
    "wda-sms": {
        "status": Project.STATUS_MAINTENANCE,
        "year": 2023,
        "problem": (
            f"{MARKER} Staff kept academic records in one place and parents were told results "
            "in person, so a parent had no way to see a child's standing between terms."
        ),
        "solution": (
            f"{MARKER} A school management platform with separate portals for staff, parents "
            "and pupils over one academic record, so a result entered once is visible "
            "everywhere it is needed."
        ),
        "result": (
            f"{MARKER} Parents check results and attendance themselves, and administrative "
            "staff stopped re-keying the same records into separate documents."
        ),
        "features": [
            ("Staff portal", "Class registers, assessment entry and report card generation."),
            ("Parent portal", "Results, attendance and school announcements per child."),
            ("Pupil portal", "Timetable, assignments and published results."),
        ],
        "challenges": [
            ("Migrating historical records", "Several years of spreadsheet records had inconsistent pupil identifiers; import ran through a reconciliation step with a manual review queue."),
        ],
    },
    "borno-agile-mis": {
        "status": Project.STATUS_DEVELOPMENT,
        "year": 2025,
        "problem": (
            f"{MARKER} Programme data arrived from field officers as separate workbooks with "
            "no shared schema, making any aggregate figure a manual exercise."
        ),
        "solution": (
            f"{MARKER} A management information system with structured intake forms, "
            "validation at entry and dashboards that aggregate across sites and reporting "
            "periods."
        ),
        "result": f"{MARKER} In development. No outcomes are claimed yet.",
        "features": [
            ("Structured data intake", "Validated forms replacing free-form workbooks."),
            ("Aggregate dashboards", "Figures rolled up across sites and reporting periods."),
            ("Export", "Report generation in the formats partners already use."),
        ],
        "challenges": [
            ("Inconsistent legacy submissions", "Historic workbooks are mapped through a per-source adapter rather than a single import path."),
        ],
    },
}

BLOG_CATEGORIES = [
    ("Django", "Notes on building and running Django applications."),
    ("Architecture", "System design decisions and the trade-offs behind them."),
    ("DevOps", "Deployment, servers and keeping things running."),
    ("Product", "Building software people actually use."),
]

# (title, category, days_ago, published, featured). A negative days_ago is a
# future publish date, which exercises the scheduled-post path.
BLOG_POSTS = [
    ("Why I build multi-tenant systems on a single Django deployment", "Architecture", 3, True, True),
    ("Cutting N+1 queries out of a report generator", "Django", 9, True, True),
    ("Deploying Django to a Linux VPS without Docker", "DevOps", 17, True, False),
    ("Choosing PostgreSQL row-level isolation over separate databases", "Architecture", 24, True, False),
    ("Serving user media from Cloudflare R2", "DevOps", 31, True, False),
    ("Writing admin interfaces the client can actually use", "Django", 40, True, False),
    ("What school administrators asked for that I did not expect", "Product", 52, True, False),
    ("Testing a payment integration you cannot call in CI", "Django", 63, True, False),
    ("Database indexes I add before the first deploy", "Django", 74, True, False),
    ("Scoping a build when the requirements are still moving", "Product", 88, True, False),
    ("Structured logging on a single-server deployment", "DevOps", 101, True, False),
    ("A draft about background jobs", "Django", 0, False, False),
    ("Scheduled: notes on caching strategy", "Architecture", -5, True, False),
]

EXPERIENCE = [
    {
        "organization": "Techmiary Technology Concepts",
        "organization_url": "https://techmiary.cloud",
        "position": "Founder & Software Engineer",
        "location": "Maiduguri, Nigeria",
        "start_date": date(2021, 3, 1),
        "end_date": None,
        "is_current": True,
        "description": (
            f"{MARKER} Build and operate SaaS platforms, school management systems and "
            "business information systems end to end — architecture, development, "
            "deployment and ongoing maintenance."
        ),
        "technologies": "Python, Django, PostgreSQL, Linux, Nginx, Gunicorn, Cloudflare R2",
        "responsibilities": [
            "Design and build multi-tenant Django applications from requirements through to production.",
            "Deploy and maintain Linux VPS infrastructure with Nginx, Gunicorn and PostgreSQL.",
            "Integrate payment, messaging, storage and text-to-speech APIs.",
            "Run client discovery, scoping and handover directly with school administrators.",
        ],
    },
    {
        "organization": f"{MARKER} Sample Systems Ltd",
        "organization_url": "https://example.com",
        "position": "Backend Developer",
        "location": "Remote",
        "start_date": date(2019, 6, 1),
        "end_date": date(2021, 2, 28),
        "is_current": False,
        "description": (
            f"{MARKER} Worked on internal business applications and reporting tools for a "
            "distributed team."
        ),
        "technologies": "Python, Django, Django REST Framework, PostgreSQL, Git",
        "responsibilities": [
            "Built and maintained REST APIs consumed by internal web and mobile clients.",
            "Migrated a reporting pipeline off nightly spreadsheet exports onto queryable tables.",
            "Reviewed pull requests and wrote the team's deployment runbook.",
        ],
    },
    {
        "organization": f"{MARKER} Sample Tech Academy",
        "organization_url": "",
        "position": "Web Development Instructor (part-time)",
        "location": "Maiduguri, Nigeria",
        "start_date": date(2018, 9, 1),
        "end_date": date(2019, 5, 31),
        "is_current": False,
        "description": f"{MARKER} Taught introductory Python and web development to cohorts of beginners.",
        "technologies": "Python, HTML, CSS, JavaScript, Git",
        "responsibilities": [
            "Delivered a twelve-week introductory Python and web development curriculum.",
            "Mentored students through their first deployed project.",
        ],
        "is_active": False,
    },
]

# Deliverables per service, one per line — the seeder writes them into the
# Service.deliverables text field so the service cards have a body.
SERVICE_DELIVERABLES = {
    "Custom Software Development": [
        "Requirements workshop and written scope",
        "Data model and system architecture",
        "Working application deployed to your infrastructure",
        "Handover documentation and admin training",
    ],
    "SaaS Development": [
        "Multi-tenant architecture and tenant isolation",
        "Subscription billing and plan management",
        "Role-based access control",
        "Usage reporting and admin dashboards",
    ],
    "School Management Systems": [
        "Student records, classes and subject allocation",
        "Assessment entry and automated report cards",
        "Fee invoicing, payments and outstanding balances",
        "Parent and staff portals",
    ],
    "EdTech Development": [
        "Structured lesson and curriculum modelling",
        "Assessments with automated scoring",
        "Audio, video and interactive content delivery",
        "Learner progress tracking",
    ],
    "API & Integration Development": [
        "REST API design and documentation",
        "Payment gateway integration",
        "SMS, email and notification delivery",
        "Third-party service and webhook integration",
    ],
    "Deployment & Infrastructure": [
        "Linux VPS provisioning and hardening",
        "Nginx, Gunicorn and PostgreSQL configuration",
        "SSL certificates and automated renewal",
        "Backups, monitoring and deployment runbook",
    ],
}

# (name, kind, relationship, order). Fabricated, like everything else here:
# replace with organisations that have actually agreed to be named.
PARTNERS = [
    (f"{MARKER} Northwind Cloud", Partner.KIND_PARTNER, "Infrastructure partner", 1),
    (f"{MARKER} Ladder Design Co", Partner.KIND_PARTNER, "Product design", 2),
    (f"{MARKER} Rivet Payments", Partner.KIND_PARTNER, "Payments integration", 3),
    (f"{MARKER} Sahel Data Labs", Partner.KIND_PARTNER, "Data engineering", 4),
    (f"{MARKER} Sample Education Group", Partner.KIND_TRUSTED, "School ERP rollout", 1),
    (f"{MARKER} Bright Future Academy", Partner.KIND_TRUSTED, "Results and fees", 2),
    (f"{MARKER} Sample NGO", Partner.KIND_TRUSTED, "Field reporting MIS", 3),
    (f"{MARKER} Sample Logistics", Partner.KIND_TRUSTED, "Internal tooling", 4),
    (f"{MARKER} Maiduguri Tech Hub", Partner.KIND_TRUSTED, "Training platform", 5),
]

CONTACT_MESSAGES = [
    ("Adaobi Nwosu", "adaobi@example.com", "+234 801 000 0001", "Sample Schools Ltd",
     "School management system for three campuses",
     "We run three campuses and currently keep results in spreadsheets. Could you walk us "
     "through what a rollout would look like and roughly what it costs?",
     ContactMessage.STATUS_NEW, 1),
    ("Ibrahim Musa", "ibrahim@example.com", "", "",
     "Question about Diction Masters",
     "Is there a way to add a custom word list for a class, or is the corpus fixed?",
     ContactMessage.STATUS_NEW, 2),
    ("Grace Okonkwo", "grace@example.com", "+234 802 000 0002", "Sample NGO",
     "MIS for a field reporting programme",
     "We collect monthly field reports from twelve sites in workbooks. We would like to "
     "discuss replacing that with a proper system.",
     ContactMessage.STATUS_READ, 4),
    ("Tunde Bakare", "tunde@example.com", "", "Sample Logistics",
     "Paystack integration help",
     "We have an existing Django app and need help wiring up subscription billing. Are you "
     "taking on short engagements?",
     ContactMessage.STATUS_READ, 8),
    ("Fatima Abubakar", "fatima@example.com", "+234 803 000 0003", "",
     "Availability for a six-week build",
     "Following up on our call — are you free to start in the first week of next month?",
     ContactMessage.STATUS_REPLIED, 15),
    ("Chinedu Eze", "chinedu@example.com", "", "Sample Consulting",
     "Speaking at a developer meetup",
     "Would you be interested in giving a talk on deploying Django without containers?",
     ContactMessage.STATUS_REPLIED, 23),
    ("SEO Growth Partners", "noreply@example.net", "", "",
     "Boost your website ranking guaranteed!!!",
     "Dear sir/madam, we can get your website to page one of Google in 7 days. Reply for "
     "our package list.",
     ContactMessage.STATUS_SPAM, 6),
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Linux; Android 13; SM-A536B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0 Mobile Safari/537.36",
]

PARAGRAPHS = [
    "The constraint that shaped this was not the code. It was that the people using the "
    "system do not have time to learn it, and the machine they use it on is whatever was "
    "already on the desk.",
    "Every decision below follows from that. Where a simpler approach cost a little "
    "performance but removed a step from someone's day, it won.",
    "The first version did the obvious thing, and the obvious thing was wrong in a way that "
    "only showed up under real data. That is the interesting part, so it is what this post "
    "is mostly about.",
    "Measuring before changing anything is the boring advice everyone gives, and it is "
    "boring because it keeps being right. The query count told a different story from the "
    "one I had assumed.",
    "What I would do differently: decide the data model's ownership boundaries before "
    "writing the first view, not after the second feature forces the question.",
    "None of this is novel. It is written down because I had to work it out twice, and the "
    "second time was avoidable.",
]


class Command(BaseCommand):
    help = "Fill every model with sample data for local testing. Never run on production."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete sample rows (blog, experience, enquiries, social links, project children) before seeding.",
        )
        parser.add_argument(
            "--no-images",
            action="store_true",
            help="Skip generating placeholder images for image fields.",
        )
        parser.add_argument(
            "--no-base",
            action="store_true",
            help="Do not run seed_portfolio first; only layer sample data onto existing records.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        from django.conf import settings as django_settings

        if not django_settings.DEBUG and not options["no_base"]:
            self.stdout.write(
                self.style.WARNING("DEBUG is off — this looks like a production settings module.")
            )
        random.seed(20260919)
        self.with_images = not options["no_images"]

        if options["flush"]:
            self.flush()

        if not options["no_base"]:
            self.stdout.write(self.style.MIGRATE_HEADING("Base content (seed_portfolio)"))
            call_command("seed_portfolio", verbosity=0)
            self.stdout.write("  base content ensured.")

        user = self.seed_user()
        self.seed_site_settings()
        self.seed_social_links()
        self.seed_partners()
        self.seed_projects()
        self.seed_services()
        self.seed_blog(user)
        self.seed_experience()
        self.seed_contact_messages()
        self.seed_team()
        self.seed_clients_and_testimonials()
        self.seed_resources()
        self.seed_milestones()
        self.seed_careers()
        self.seed_quotes_and_subscribers()
        self.seed_solution_images()

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Sample data seeded."))
        self.stdout.write(
            f"  Admin login: {TEST_USER['username']} / {TEST_PASSWORD}\n"
            f"  Fabricated text is tagged {MARKER} so it is easy to find and remove.\n"
            "  Run 'python manage.py seed_testdata --flush --no-base' to clear it again."
        )

    # -- flush --------------------------------------------------------------
    def flush(self):
        self.stdout.write(self.style.MIGRATE_HEADING("Flushing sample data"))
        for model in (
            JobApplication,
            JobOpening,
            QuoteRequest,
            NewsletterSubscriber,
            Testimonial,
            Client,
            Resource,
            Milestone,
            ContactMessage,
            Responsibility,
            Experience,
            BlogPost,
            BlogCategory,
            ProjectImage,
            ProjectFeature,
            ProjectChallenge,
            Partner,
            SocialLink,
        ):
            deleted, _ = model.objects.all().delete()
            self.stdout.write(f"  - {model.__name__}: {deleted} row(s)")
        # Team members beyond the founder are sample rows; the founder's
        # record comes from seed_portfolio and stays.
        deleted, _ = TeamMember.objects.filter(is_founder=False).delete()
        self.stdout.write(f"  - TeamMember (non-founder): {deleted} row(s)")
        get_user_model().objects.filter(username=TEST_USER["username"]).delete()

    # -- images -------------------------------------------------------------
    # Fonts are looked up once; any missing path just falls through.
    FONT_PATHS = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]

    def _font(self, size):
        from PIL import ImageFont

        for path in self.FONT_PATHS:
            try:
                return ImageFont.truetype(path, size)
            except (OSError, ImportError):
                # OSError: the font file is not on this machine.
                # ImportError: Pillow was built without FreeType, so no
                # TrueType font can be loaded at all. Either way, fall through
                # to the bitmap default rather than failing the seed.
                continue
        return ImageFont.load_default()

    def image_file(self, label, width, height, hue, transparent=False):
        """
        A placeholder PNG: a diagonal gradient, a faint grid and the label.

        Type is scaled to the canvas so a 64px favicon and a 1200px cover are
        both legible — a placeholder nobody can read is worse than none.
        """
        from PIL import Image, ImageDraw

        base = tuple(int(c) for c in hue)
        mode = "RGBA" if transparent else "RGB"
        image = Image.new(mode, (width, height), (0, 0, 0, 0) if transparent else base)
        draw = ImageDraw.Draw(image)

        if not transparent:
            # Diagonal wash from the base colour toward near-black.
            for y in range(height):
                t = y / max(height - 1, 1)
                draw.line(
                    [(0, y), (width, y)],
                    fill=tuple(int(c * (1 - 0.55 * t)) for c in base),
                )
            step = max(width // 14, 24)
            for x in range(0, width, step):
                draw.line([(x, 0), (x, height)], fill=(255, 255, 255), width=1)
            for y in range(0, height, step):
                draw.line([(0, y), (width, y)], fill=(255, 255, 255), width=1)
            # Re-blend the grid down so it reads as texture, not a table.
            image = Image.blend(Image.new("RGB", (width, height), base), image, 0.92)
            draw = ImageDraw.Draw(image)

        # Fit the type to the canvas: grow until it would exceed either the
        # width or the height budget. Keying off the short edge alone leaves a
        # wide banner like a logo with unreadably small text.
        max_w, max_h = width * 0.82, height * 0.6
        size = max(int(min(width, height) * 0.1), 10)
        font = self._font(size)
        for _ in range(40):
            trial = self._font(size + 2)
            b = draw.multiline_textbbox((0, 0), label, font=trial, align="center", spacing=6)
            if (b[2] - b[0]) > max_w or (b[3] - b[1]) > max_h:
                break
            size += 2
            font = trial

        box = draw.multiline_textbbox((0, 0), label, font=font, align="center", spacing=6)
        draw.multiline_text(
            ((width - (box[2] - box[0])) / 2 - box[0], (height - (box[3] - box[1])) / 2 - box[1]),
            label,
            font=font,
            # Transparent placeholders sit on the page background, which is
            # light, so they are drawn dark. Opaque ones sit on their own
            # coloured field and stay light.
            fill=(18, 36, 60) if transparent else (243, 243, 245),
            align="center",
            spacing=6,
        )

        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return ContentFile(buffer.getvalue())

    def attach_image(self, instance, field, filename, label, width, height, hue, transparent=False):
        if not self.with_images or getattr(instance, field):
            return False
        getattr(instance, field).save(
            filename, self.image_file(label, width, height, hue, transparent), save=False
        )
        return True

    # -- seeders ------------------------------------------------------------
    def seed_user(self):
        User = get_user_model()
        user, created = User.objects.get_or_create(
            username=TEST_USER["username"], defaults=TEST_USER
        )
        if created or not user.is_superuser:
            user.is_staff = True
            user.is_superuser = True
            user.set_password(TEST_PASSWORD)
            user.save()
        self.stdout.write(
            self.style.SUCCESS(f"  {'+' if created else '='} user: {user.username}")
        )
        return user

    def seed_site_settings(self):
        site = SiteSettings.load()
        if site is None:
            raise CommandError(
                "No SiteSettings record. Run without --no-base, or run seed_portfolio first."
            )
        self.stdout.write(self.style.MIGRATE_HEADING("Site settings"))
        for field, value in SITE_CONTACT.items():
            if not getattr(site, field):
                setattr(site, field, value)
        changed = [
            self.attach_image(site, "profile_image", "profile.png", "Profile", 600, 600, (30, 58, 95)),
            self.attach_image(site, "og_image", "og.png", "Open Graph", 1200, 630, (17, 24, 39)),
            self.attach_image(site, "logo", "logo.png", "TECHMIARY", 512, 110, (15, 23, 42), transparent=True),
            self.attach_image(site, "favicon", "favicon.png", "T", 64, 64, (156, 127, 69)),
        ]
        if self.with_images and not site.resume_file:
            site.resume_file.save(
                "sample-resume.txt",
                ContentFile(
                    f"{MARKER} Placeholder resume file. Replace with a real PDF in the "
                    "admin.\n".encode()
                ),
                save=False,
            )
        site.save()
        self.stdout.write(f"  contact details and {sum(1 for c in changed if c)} image(s) set.")

    def seed_social_links(self):
        self.stdout.write(self.style.MIGRATE_HEADING("Social links"))
        for name, url, icon, order, active in SOCIAL_LINKS:
            _, created = SocialLink.objects.get_or_create(
                name=name,
                defaults={"url": url, "icon": icon, "display_order": order, "is_active": active},
            )
            self.stdout.write(f"  {'+' if created else '='} {name}")

    def seed_partners(self):
        self.stdout.write(self.style.MIGRATE_HEADING("Partners / trusted by"))
        for name, kind, relationship, order in PARTNERS:
            partner, created = Partner.objects.get_or_create(
                kind=kind,
                name=name,
                defaults={
                    "relationship": relationship,
                    "display_order": order,
                    "is_active": True,
                    # Half get a link, so both the linked and plain tile
                    # variants are exercised locally.
                    "url": "https://example.com" if order % 2 == 0 else "",
                    # Sample rows, so consent is explicitly not claimed.
                    "consent_on_file": False,
                },
            )
            # A wordmark reads better than a placeholder image for a logo row,
            # so only half of them get one — enough to exercise both paths.
            # Attached on every run, not just creation, so a logo that was
            # cleared comes back without recreating the row.
            if order % 2 == 1 and self.attach_image(
                partner, "logo", f"partner-{order}-{kind}.png",
                name.replace(MARKER, "").strip(), 320, 90, (15, 23, 42),
                transparent=True,
            ):
                partner.save()
        self.stdout.write(
            f"  {Partner.objects.filter(kind=Partner.KIND_PARTNER).count()} partner(s), "
            f"{Partner.objects.filter(kind=Partner.KIND_TRUSTED).count()} trusted-by entr(ies)."
        )

    def seed_projects(self):
        self.stdout.write(self.style.MIGRATE_HEADING("Project case studies"))
        for slug, detail in PROJECT_DETAIL.items():
            project = Project.objects.filter(slug=slug).first()
            if project is None:
                self.stdout.write(self.style.WARNING(f"  ! no project with slug '{slug}' — skipped"))
                continue

            for field in (
                "problem", "solution", "result", "architecture_description",
                "client", "github_url",
            ):
                if field in detail and not getattr(project, field):
                    setattr(project, field, detail[field])
            if project.year is None and "year" in detail:
                project.year = detail["year"]
            project.status = detail.get("status", project.status)
            if not project.cover_image_alt:
                project.cover_image_alt = f"{project.title} dashboard screenshot"

            self.attach_image(
                project, "cover_image", f"{slug}-cover.png",
                project.title, 1200, 675, (30, 41, 59),
            )
            self.attach_image(
                project, "architecture_diagram", f"{slug}-architecture.png",
                f"{project.title} architecture", 1000, 600, (7, 89, 133),
            )
            project.save()

            for order, (title, description) in enumerate(detail.get("features", []), start=1):
                ProjectFeature.objects.get_or_create(
                    project=project, title=title,
                    defaults={"description": description, "display_order": order},
                )
            for order, (title, description) in enumerate(detail.get("challenges", []), start=1):
                ProjectChallenge.objects.get_or_create(
                    project=project, title=title,
                    defaults={"description": description, "display_order": order},
                )

            if self.with_images and not project.images.exists():
                for index, view in enumerate(["Dashboard", "Records", "Reports"], start=1):
                    gallery = ProjectImage(
                        project=project,
                        alt_text=f"{project.title} {view.lower()} view",
                        caption=f"{MARKER} {view} view",
                        display_order=index,
                    )
                    gallery.image.save(
                        f"{slug}-{view.lower()}.png",
                        self.image_file(f"{project.title}\n{view}", 1280, 800, (24, 48, 80)),
                        save=False,
                    )
                    gallery.save()

            self.stdout.write(
                f"  = {project.title}: {project.features.count()} feature(s), "
                f"{project.challenges.count()} challenge(s), {project.images.count()} image(s)"
            )

    def seed_services(self):
        self.stdout.write(self.style.MIGRATE_HEADING("Service deliverables"))
        filled = 0
        for title, items in SERVICE_DELIVERABLES.items():
            service = Service.objects.filter(title=title).first()
            if service is None or service.deliverables:
                continue
            service.deliverables = "\n".join(items)
            service.save()
            filled += 1
        self.stdout.write(f"  {filled} service(s) given a deliverable list.")

    def seed_blog(self, user):
        self.stdout.write(self.style.MIGRATE_HEADING("Blog"))
        categories = {}
        for name, description in BLOG_CATEGORIES:
            category, _ = BlogCategory.objects.get_or_create(
                name=name, defaults={"description": description}
            )
            categories[name] = category

        now = timezone.now()
        for title, category_name, days_ago, published, featured in BLOG_POSTS:
            paragraphs = random.sample(PARAGRAPHS, k=4)
            body = "\n\n".join(paragraphs)
            # First full sentence of the opening paragraph, so the card copy
            # reads as a real standfirst rather than a clipped fragment.
            opener = paragraphs[0].split(". ")[0].rstrip(".") + "."
            post, created = BlogPost.objects.get_or_create(
                title=title,
                defaults={
                    "excerpt": f"{MARKER} {opener}",
                    "content": f"{MARKER} Sample post body.\n\n{body}",
                    "category": categories[category_name],
                    "author": user,
                    "published": published,
                    "is_featured": featured,
                    "published_at": now - timedelta(days=days_ago) if published else None,
                },
            )
            # Attach on every run, not just creation: a post whose image was
            # cleared should get one back without recreating the row.
            if self.attach_image(
                post, "featured_image", f"{post.slug}.png", category_name, 1200, 630, (51, 65, 85)
            ):
                post.featured_image_alt = f"Illustration for {title}"
                post.save()
        live = BlogPost.live.count()
        self.stdout.write(
            f"  {BlogPost.objects.count()} post(s): {live} live, "
            f"{BlogPost.objects.filter(published=False).count()} draft, "
            f"{BlogPost.objects.filter(published=True).count() - live} scheduled"
        )

    def seed_experience(self):
        self.stdout.write(self.style.MIGRATE_HEADING("Experience"))
        for order, entry in enumerate(EXPERIENCE, start=1):
            data = dict(entry)
            responsibilities = data.pop("responsibilities")
            experience, created = Experience.objects.get_or_create(
                organization=data.pop("organization"),
                position=data.pop("position"),
                defaults={**data, "display_order": order},
            )
            for index, text in enumerate(responsibilities, start=1):
                Responsibility.objects.get_or_create(
                    experience=experience, text=text, defaults={"display_order": index}
                )
            self.stdout.write(
                f"  {'+' if created else '='} {experience} "
                f"({experience.responsibilities.count()} bullet(s))"
            )

    def seed_contact_messages(self):
        self.stdout.write(self.style.MIGRATE_HEADING("Contact messages"))
        now = timezone.now()
        for name, email, phone, company, subject, message, status, days_ago in CONTACT_MESSAGES:
            existing = ContactMessage.objects.filter(email=email, subject=subject).first()
            if existing:
                continue
            created = ContactMessage.objects.create(
                name=name, email=email, phone=phone, company=company,
                subject=subject, message=f"{MARKER} {message}", status=status,
                ip_address=f"197.210.{random.randint(1, 254)}.{random.randint(1, 254)}",
                user_agent=random.choice(USER_AGENTS),
            )
            # created_at is auto_now_add, so backdate it after the fact.
            ContactMessage.objects.filter(pk=created.pk).update(
                created_at=now - timedelta(days=days_ago, hours=random.randint(0, 23))
            )
        by_status = {
            status: ContactMessage.objects.filter(status=status).count()
            for status, _ in ContactMessage.STATUS_CHOICES
        }
        self.stdout.write(f"  {ContactMessage.objects.count()} message(s): {by_status}")

    # -- company & careers sample data --------------------------------------
    def seed_team(self):
        """Colleagues beyond the founder, so the team grid has something to lay out."""
        people = [
            ("Amina Bello", "Lead Backend Engineer", "Engineering", False),
            ("Tunde Adeyemi", "Delivery Manager", "Delivery & Support", True),
            ("Ngozi Eze", "Frontend Engineer", "Engineering", False),
            ("Ibrahim Sule", "Infrastructure Engineer", "Engineering", False),
        ]
        created = 0
        for index, (name, role, department, leadership) in enumerate(people, start=2):
            member, made = TeamMember.objects.get_or_create(
                name=name,
                defaults={
                    "role": role,
                    "department": department,
                    "is_leadership": leadership,
                    "display_order": index,
                    "short_bio": f"{MARKER} Sample team member used to exercise the team pages.",
                    "bio": (
                        f"{MARKER} Placeholder biography. Replace this with the real "
                        "background of the person who holds this role."
                    ),
                },
            )
            if made:
                created += 1
            if self.attach_image(
                member, "photo", f"{member.slug}.png", member.initials, 400, 400, sample_hue(index)
            ):
                member.save()
        self.stdout.write(f"  team members: {created} added")

    def seed_clients_and_testimonials(self):
        """
        Fabricated clients and quotes for layout testing only.

        ``consent_on_file`` is left False on purpose: these are not real
        organisations and must never be published.
        """
        from company.models import Industry

        industries = list(Industry.objects.all())
        names = [
            ("Northwind Academy", "School ERP deployment across two campuses"),
            ("Harmattan Foods", "Internal operations and stock system"),
            ("Plateau Health Trust", "Records and reporting platform"),
            ("Sahel Learning Centre", "Learning platform rollout"),
            ("Ridgeway Group", "Business information system"),
            ("Kaduna Agro Works", "Field data capture application"),
        ]
        created = 0
        for index, (name, engagement) in enumerate(names, start=1):
            client, made = Client.objects.get_or_create(
                name=f"{name}",
                defaults={
                    "engagement": f"{MARKER} {engagement}",
                    "industry": industries[index % len(industries)] if industries else None,
                    "display_order": index,
                    "consent_on_file": False,
                },
            )
            if made:
                created += 1
            if self.attach_image(
                client,
                "logo",
                f"{client.slug}.png",
                name.split()[0].upper(),
                320,
                120,
                sample_hue(index),
                True,
            ):
                client.save()

        quotes = [
            (
                "It replaced four spreadsheets and a WhatsApp group. Staff stopped asking "
                "where the current numbers were.",
                "A. Okafor",
                "Head of Administration",
                "Northwind Academy",
            ),
            (
                "They asked how we actually work before proposing anything. The system "
                "matches our process instead of fighting it.",
                "B. Danjuma",
                "Operations Director",
                "Harmattan Foods",
            ),
            (
                "Deployment was handled end to end, and someone answers when we call.",
                "C. Mohammed",
                "Programme Lead",
                "Plateau Health Trust",
            ),
        ]
        made_quotes = 0
        for index, (quote, author, role, organisation) in enumerate(quotes, start=1):
            _, made = Testimonial.objects.get_or_create(
                author_name=author,
                defaults={
                    "quote": f"{MARKER} {quote}",
                    "author_role": role,
                    "organisation": organisation,
                    "client": Client.objects.filter(name=organisation).first(),
                    "display_order": index,
                    "consent_on_file": False,
                },
            )
            if made:
                made_quotes += 1
        self.stdout.write(f"  clients: {created} added, testimonials: {made_quotes} added")

    def seed_resources(self):
        categories = list(ResourceCategory.objects.all())
        if not categories:
            return
        items = [
            ("Software procurement checklist", "checklist", 6,
             "What to settle with a supplier before any code is written."),
            ("Planning a school management rollout", "guide", 14,
             "Sequencing a rollout across terms so nothing is lost mid-session."),
            ("Choosing between hosted and on-premise", "whitepaper", 11,
             "The trade-offs in cost, control and maintenance between the two."),
            ("Data migration readiness", "checklist", 5,
             "Getting existing records into a shape a new system can accept."),
            ("Capability statement", "brochure", 8,
             "An overview of what the company builds and how engagements run."),
        ]
        created = 0
        today = timezone.localdate()
        for index, (title, kind, pages, summary) in enumerate(items, start=1):
            resource, made = Resource.objects.get_or_create(
                title=title,
                defaults={
                    "summary": f"{MARKER} {summary}",
                    "kind": kind,
                    "pages": pages,
                    "category": categories[index % len(categories)],
                    "published_at": today - timedelta(days=30 * index),
                    "display_order": index,
                },
            )
            if made:
                created += 1
                resource.file.save(
                    f"{resource.slug}.txt",
                    ContentFile(
                        f"{MARKER} Placeholder resource file for {title}. "
                        "Replace it with the real PDF in the Django admin.".encode()
                    ),
                    save=False,
                )
                resource.save()
            if self.attach_image(
                resource, "cover_image", f"{resource.slug}.png", kind.upper(), 800, 450, sample_hue(index)
            ):
                resource.save()
        self.stdout.write(f"  resources: {created} added")

    def seed_milestones(self):
        entries = [
            (2021, "Company founded", "Techmiary Technology Concepts starts trading."),
            (2022, "First school platform deployed", "The school ERP goes live with its first institution."),
            (2023, "Learning platform launched", "The pronunciation and vocabulary platform opens to learners."),
            (2024, "Infrastructure brought in house", "Hosting, backups and monitoring managed directly."),
        ]
        created = 0
        for index, (year, title, description) in enumerate(entries, start=1):
            _, made = Milestone.objects.get_or_create(
                year=year,
                title=title,
                defaults={"description": f"{MARKER} {description}", "display_order": index},
            )
            if made:
                created += 1
        self.stdout.write(f"  milestones: {created} added")

    def seed_careers(self):
        departments = {d.name: d for d in Department.objects.all()}
        if not departments:
            return
        roles = [
            {
                "title": "Backend Engineer (Django)",
                "department": "Engineering",
                "summary": "Own backend features on the platforms schools and businesses run on.",
                "description": (
                    "You will design data models, build APIs and ship features into systems "
                    "that are already in daily use."
                ),
                "responsibilities": "Design and build Django applications\nReview colleagues' code\nSupport what you ship in production",
                "requirements": "Solid Python\nProduction Django experience\nComfortable with PostgreSQL\nClear written communication",
                "nice_to_have": "Multi-tenant application experience\nLinux server administration",
                "benefits": "Real ownership of systems\nDirect contact with the people using your work\nCode review and mentorship",
                "experience_level": "mid",
                "location_type": "hybrid",
                "location": "Jos, Nigeria",
                "status": JobOpening.STATUS_OPEN,
            },
            {
                "title": "Frontend Engineer",
                "department": "Engineering",
                "summary": "Build accessible, fast interfaces on top of Django templates.",
                "description": (
                    "You will turn workflows into interfaces that staff can use quickly, on "
                    "whatever device they have."
                ),
                "responsibilities": "Build responsive interfaces\nKeep pages fast and accessible\nWork directly with backend engineers",
                "requirements": "Strong HTML, CSS and JavaScript\nAn eye for accessible markup\nComfortable in a server-rendered codebase",
                "benefits": "Design input, not just implementation\nFlexible working",
                "experience_level": "mid",
                "location_type": "remote",
                "status": JobOpening.STATUS_OPEN,
            },
            {
                "title": "Implementation & Support Specialist",
                "department": "Delivery & Support",
                "summary": "Onboard new organisations and keep deployed systems healthy.",
                "description": (
                    "You will run rollouts, train staff and be the first responder when "
                    "something needs attention."
                ),
                "responsibilities": "Run onboarding and training\nTriage support requests\nFeed real usage back to engineering",
                "requirements": "Patience with non-technical users\nStructured, written follow-up\nComfortable learning a system deeply",
                "experience_level": "entry",
                "location_type": "onsite",
                "location": "Jos, Nigeria",
                "status": JobOpening.STATUS_OPEN,
            },
            {
                "title": "Business Development Lead",
                "department": "Operations",
                "summary": "Closed — kept as sample data so the admin has a non-open role.",
                "description": "A closed role, used to check that closed listings stay off the careers page.",
                "experience_level": "senior",
                "location_type": "hybrid",
                "status": JobOpening.STATUS_CLOSED,
            },
        ]

        created = 0
        for index, role in enumerate(roles, start=1):
            data = dict(role)
            department = departments.get(data.pop("department"))
            if department is None:
                continue
            title = data.pop("title")
            job, made = JobOpening.objects.get_or_create(
                title=title,
                defaults={
                    "department": department,
                    "is_published": True,
                    "display_order": index,
                    **data,
                },
            )
            if made:
                created += 1

        # A couple of applications so the admin list and inline are populated.
        open_job = JobOpening.open_roles.first()
        applications = 0
        if open_job:
            for name, email in [("Ada Nwosu", "ada@example.com"), ("Femi Balogun", "femi@example.com")]:
                application, made = JobApplication.objects.get_or_create(
                    job=open_job,
                    email=email,
                    defaults={
                        "full_name": name,
                        "phone": "+2348000000000",
                        "location": "Jos, Nigeria",
                        "cover_letter": f"{MARKER} Sample application used to populate the admin.",
                    },
                )
                if made:
                    application.cv.save(
                        f"{MARKER.strip('[]')}-{application.pk}-cv.txt",
                        ContentFile(f"{MARKER} Placeholder CV file.".encode()),
                        save=True,
                    )
                    applications += 1
        self.stdout.write(f"  job openings: {created} added, applications: {applications} added")

    def seed_quotes_and_subscribers(self):
        solutions = list(Solution.objects.all())
        services = list(Service.objects.all())
        samples = [
            ("Student records for three campuses", "school", "1m_5m", "1_3_months", QuoteRequest.STATUS_NEW),
            ("Stock and operations system", "business", "under_1m", "asap", QuoteRequest.STATUS_REVIEWING),
            ("Programme reporting platform", "government", "5m_15m", "3_6_months", QuoteRequest.STATUS_QUOTED),
        ]
        created = 0
        for index, (title, org_type, budget, timeline, status) in enumerate(samples, start=1):
            _, made = QuoteRequest.objects.get_or_create(
                project_title=title,
                defaults={
                    "description": (
                        f"{MARKER} Sample quote request used to populate the admin queue. "
                        "It describes a system in enough detail to be scoped."
                    ),
                    "solution": solutions[index % len(solutions)] if solutions else None,
                    "service": services[index % len(services)] if services else None,
                    "budget_range": budget,
                    "timeline": timeline,
                    "organisation_type": org_type,
                    "contact_name": f"Sample Requester {index}",
                    "email": f"requester{index}@example.com",
                    "organisation": f"Sample Organisation {index}",
                    "country": "Nigeria",
                    "status": status,
                },
            )
            if made:
                created += 1

        subscribers = 0
        for index in range(1, 7):
            _, made = NewsletterSubscriber.objects.get_or_create(
                email=f"subscriber{index}@example.com",
                defaults={"name": f"Sample Subscriber {index}", "source": "footer"},
            )
            if made:
                subscribers += 1
        self.stdout.write(f"  quote requests: {created} added, subscribers: {subscribers} added")

    def seed_solution_images(self):
        updated = 0
        for index, solution in enumerate(Solution.objects.all(), start=1):
            if self.attach_image(
                solution,
                "hero_image",
                f"{solution.slug}.png",
                solution.name.upper(),
                1200,
                675,
                sample_hue(index),
            ):
                solution.hero_image_alt = f"{solution.name} interface"
                solution.save()
                updated += 1
        self.stdout.write(f"  solution images: {updated} generated")
