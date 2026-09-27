"""
Fill every remaining blank field so each feature can be exercised end to end.

``seed_testdata`` creates the rows; this tops up the optional fields it leaves
empty. It is additive — a field that already has content is never overwritten,
so it is safe to run after editing content by hand.

Some blanks are deliberately kept, because they *are* the state under test:

    Experience.end_date is None          -> the role shows as "Present"
    BlogPost.published_at is None        -> the post is a draft
    Partner.logo empty                   -> the name renders as a wordmark
    Partner.url empty                    -> the tile is not a link
    TeamMember.photo empty               -> initials fallback
    JobOpening.closes_at is None         -> the opening has no closing date
    NewsletterSubscriber.unsubscribed_at -> the subscriber is still active
    ContactMessage.phone / company       -> optional fields left empty

Filling those would remove the only coverage of those paths, so a proportion
of each is preserved. Run with --all to override that and fill everything.
"""
import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

MARKER = "[sample]"


def ip():
    return f"197.210.{random.randint(1, 254)}.{random.randint(1, 254)}"


class Command(BaseCommand):
    help = "Populate every blank optional field left by seed_testdata."

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            help="Also fill the blanks that intentionally represent a state (drafts, current roles, wordmark partners).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        random.seed(20260927)
        self.fill_everything = options["all"]
        self.changed = 0

        self.site_settings()
        self.skills()
        self.partners()
        self.solutions()
        self.industries()
        self.team()
        self.clients_and_testimonials()
        self.resources()
        self.projects()
        self.services()
        self.blog()
        self.experience()
        self.careers()
        self.enquiries()

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Filled {self.changed} field(s)."))
        if not self.fill_everything:
            self.stdout.write(
                "Blanks that represent a state (drafts, current roles, logo-less\n"
                "partners, open-ended vacancies) were preserved so those paths stay\n"
                "testable. Use --all to fill those too."
            )

    # -- helpers -----------------------------------------------------------
    def set_if_blank(self, obj, **values):
        """Assign only the fields that are currently empty. Returns True if changed."""
        touched = False
        for field, value in values.items():
            current = getattr(obj, field, None)
            empty = current in ("", None) or (hasattr(current, "name") and not current.name)
            if empty and value not in ("", None):
                setattr(obj, field, value)
                touched = True
                self.changed += 1
        if touched:
            obj.save()
        return touched

    def report(self, label, n):
        self.stdout.write(f"  {label:34} {n}")

    # -- core --------------------------------------------------------------
    def site_settings(self):
        from core.models import SiteSettings

        site = SiteSettings.load()
        if site is None:
            self.stdout.write(self.style.WARNING("  no SiteSettings — run seed_testdata first"))
            return
        self.set_if_blank(
            site,
            legal_name="Techmiary Technology Concepts",
            founded_year=2021,
            address=f"{MARKER} 14 Baga Road, Maiduguri, Borno State, Nigeria",
            office_hours="Mon–Fri, 09:00–17:00 WAT",
            support_email="support@techmiary.tech",
            sales_email="sales@techmiary.tech",
            secondary_phone="+234 800 000 0001",
            registration_number=f"{MARKER} RC-0000000",
            meta_title="Samuel Jeremiah — Software Engineer & Product Builder",
            meta_description=(
                "Techmiary Technology Concepts builds SaaS platforms, school management "
                "systems and EdTech applications with Python and Django."
            ),
            twitter_handle="techmiary",
        )
        self.report("site settings", "topped up")

    def skills(self):
        from core.models import Skill

        NOTES = {
            "Python": ("The language everything here is written in.", "primary"),
            "Django": ("Application framework for every product on this site.", "primary"),
            "PostgreSQL": ("Primary datastore in production.", "primary"),
            "Django REST Framework": ("APIs consumed by web and mobile clients.", "proficient"),
            "REST APIs": ("Design, versioning and documentation.", "proficient"),
            "Linux": ("Ubuntu servers, day to day.", "proficient"),
            "Nginx": ("Reverse proxy, TLS termination, static delivery.", "proficient"),
            "Gunicorn": ("WSGI app server behind Nginx.", "proficient"),
        }
        n = 0
        levels = ["working", "proficient", "primary"]
        for skill in Skill.objects.all():
            note, level = NOTES.get(
                skill.name,
                (f"Used in production work at Techmiary.", random.choice(levels)),
            )
            if self.set_if_blank(skill, description=note, proficiency=level):
                n += 1
        self.report("skills given a note and level", n)

    def partners(self):
        from core.models import Partner

        n = 0
        for p in Partner.objects.all():
            if self.set_if_blank(p, logo_alt=f"{p.name} logo"):
                n += 1
            # Consent is what gates naming an organisation, so record it on the
            # sample rows to exercise the "consented" state in the admin.
            if not p.consent_on_file:
                p.consent_on_file = True
                p.save(update_fields=["consent_on_file"])
                self.changed += 1
        if self.fill_everything:
            for p in Partner.objects.filter(url=""):
                p.url = "https://example.com"
                p.save(update_fields=["url"])
                self.changed += 1
        self.report("partners: alt text + consent", n)

    # -- company -----------------------------------------------------------
    def solutions(self):
        from company.models import Industry, Solution

        industries = list(Industry.objects.all())
        n = 0
        for s in Solution.objects.all():
            self.set_if_blank(
                s,
                overview=(
                    f"{MARKER} {s.name} is delivered as a working system rather than a "
                    "template: the data model, the workflows and the reporting are shaped "
                    "around how the organisation already operates, then deployed and "
                    "maintained on infrastructure we run."
                ),
                who_its_for=(
                    f"{MARKER} Organisations that already run this process on spreadsheets "
                    "and paper, and have reached the point where reconciling them costs "
                    "more than replacing them."
                ),
                outcome=(
                    f"{MARKER} Teams using {s.name} keep one record per person or case, "
                    "produce their periodic reports from that record rather than "
                    "re-keying, and give each role only the access it needs."
                ),
                hero_image_alt=f"{s.name} interface",
                meta_title=f"{s.name} — Techmiary"[:70],
                meta_description=(
                    (s.summary or f"{s.name} built and operated by Techmiary.")[:180]
                ),
            )
            if not s.hero_image:
                self._attach(s, "hero_image", f"solution-{s.slug}.png", s.name,
                             1200, 675, (26, 44, 78))
            if industries and not s.industries.exists():
                s.industries.add(*random.sample(industries, k=min(2, len(industries))))
                self.changed += 1
            n += 1
        self.report("solutions", n)

    def industries(self):
        from company.models import Industry

        n = 0
        for i in Industry.objects.all():
            self.set_if_blank(
                i,
                overview=(
                    f"{MARKER} Work in {i.name.lower()} tends to start with records that "
                    "already exist in spreadsheets and paper, so the first job is usually "
                    "migration and validation rather than new features."
                ),
                challenges=(
                    f"{MARKER} Records spread across workbooks and paper\n"
                    f"{MARKER} Reporting rebuilt by hand every period\n"
                    f"{MARKER} No single view of a person or case"
                ),
                image_alt=f"{i.name} illustration",
            )
            if not i.image:
                self._attach(i, "image", f"industry-{i.pk}.png", i.name, 1200, 675, (24, 40, 72))
            n += 1
        self.report("industries", n)

    def team(self):
        from company.models import TeamMember

        n = 0
        for idx, t in enumerate(TeamMember.objects.all(), start=1):
            handle = "".join(ch for ch in t.name.lower().replace(MARKER, "") if ch.isalnum())[:18]
            self.set_if_blank(
                t,
                photo_alt=f"Portrait of {t.name}",
                email=f"{handle}@techmiary.tech",
                linkedin_url=f"https://www.linkedin.com/in/{handle}/",
                github_url=f"https://github.com/{handle}" if idx % 2 else "",
                twitter_url=f"https://x.com/{handle}" if idx % 3 == 0 else "",
            )
            # One member keeps no photo, to exercise the initials fallback.
            if not t.photo and (self.fill_everything or idx > 1):
                self._attach(t, "photo", f"team-{t.pk}.png", t.name.replace(MARKER, "").strip(),
                             600, 600, (32, 48, 84))
            n += 1
        self.report("team members", n)

    def clients_and_testimonials(self):
        from company.models import Client, Testimonial

        n = 0
        for c in Client.objects.all():
            self.set_if_blank(
                c,
                logo_alt=f"{c.name} logo",
                website_url="https://example.com",
                engagement=f"{MARKER} Platform build and ongoing maintenance",
            )
            if not c.consent_on_file:
                c.consent_on_file = True
                c.save(update_fields=["consent_on_file"])
                self.changed += 1
            if not getattr(c, "logo", None):
                self._attach(c, "logo", f"client-{c.pk}.png",
                             c.name.replace(MARKER, "").strip(), 320, 90, (18, 36, 60),
                             transparent=True)
            n += 1
        self.report("clients", n)

        m = 0
        for t in Testimonial.objects.all():
            if not t.consent_on_file:
                t.consent_on_file = True
                t.save(update_fields=["consent_on_file"])
                self.changed += 1
            if not t.author_photo:
                self._attach(t, "author_photo", f"testimonial-{t.pk}.png",
                             t.author_name.replace(MARKER, "").strip(),
                             400, 400, (40, 30, 70))
            m += 1
        self.report("testimonials (author photos)", m)

    def resources(self):
        from company.models import Resource

        n = 0
        for idx, r in enumerate(Resource.objects.all(), start=1):
            # Half link out, half keep a file — both paths get exercised.
            if idx % 2 == 0:
                if self.set_if_blank(r, external_url="https://example.com/resource"):
                    n += 1
            if not r.cover_image:
                self._attach(r, "cover_image", f"resource-{r.slug}.png", r.title,
                             800, 1000, (30, 34, 72))
        self.report("resources given an external link", n)

    # -- projects / services ----------------------------------------------
    def projects(self):
        from projects.models import Project

        n = 0
        for p in Project.objects.all():
            self.set_if_blank(
                p,
                description=(
                    f"{MARKER} {p.title} is a production system: designed, built, deployed "
                    "and maintained rather than prototyped."
                ),
                architecture_description=(
                    f"{MARKER} Nginx terminates TLS and serves hashed static files. "
                    "Gunicorn runs the Django application on an Ubuntu VPS. PostgreSQL "
                    "holds the data; uploaded media goes to object storage behind a CDN."
                ),
                client=f"{MARKER} Sample Client {p.pk}",
                github_url=f"https://github.com/example/{p.slug}",
                meta_title=p.resolved_meta_title[:70],
                meta_description=p.resolved_meta_description[:180],
                cover_image_alt=f"{p.title} interface screenshot",
            )
            if not p.architecture_diagram:
                self._attach(p, "architecture_diagram", f"{p.slug}-arch.png",
                             f"{p.title}\narchitecture", 1000, 600, (14, 52, 96))
            n += 1
        self.report("projects", n)

    def services(self):
        from services.models import Service

        n = 0
        for s in Service.objects.all():
            self.set_if_blank(
                s,
                description=(
                    f"{MARKER} {s.summary} Engagements start with a written scope and end "
                    "with the system running in production, with handover documentation "
                    "and a maintenance arrangement."
                ),
            )
            n += 1
        self.report("services given a description", n)

    def blog(self):
        from blog.models import BlogPost

        n = 0
        for post in BlogPost.objects.all():
            if self.set_if_blank(
                post,
                meta_title=post.resolved_meta_title[:70],
                meta_description=post.resolved_meta_description[:180],
                featured_image_alt=f"Illustration for {post.title}",
            ):
                n += 1
            if self.fill_everything and post.published_at is None:
                post.published_at = timezone.now() - timedelta(days=1)
                post.save(update_fields=["published_at"])
                self.changed += 1
        self.report("blog posts given SEO fields", n)

    def experience(self):
        from experience.models import Experience

        n = 0
        for e in Experience.objects.all():
            if self.set_if_blank(e, organization_url="https://example.com"):
                n += 1
        self.report("experience org links", n)

    # -- careers -----------------------------------------------------------
    def careers(self):
        from careers.models import JobApplication, JobOpening

        RESP = ("Build and ship features end to end\n"
                "Review pull requests and keep the deployment runbook current\n"
                "Work directly with the people who will use what you build\n"
                "Take part in on-call for the systems you own")
        REQS = ("Commercial experience shipping and maintaining a web application\n"
                "Comfortable with SQL and relational data modelling\n"
                "Able to write clearly — we work asynchronously\n"
                "Based in, or able to work overlapping hours with, West Africa")
        NICE = ("Experience with Django or another batteries-included framework\n"
                "Exposure to multi-tenant systems\n"
                "Has run something in production that other people depended on")
        BENS = ("Remote-first, with a Maiduguri office you can use\n"
                "Hardware of your choice\n"
                "Annual learning budget\n"
                "Paid time off, taken seriously")

        n = 0
        for idx, job in enumerate(JobOpening.objects.all(), start=1):
            self.set_if_blank(
                job,
                responsibilities=RESP,
                requirements=REQS,
                nice_to_have=NICE,
                benefits=BENS,
                location="Maiduguri, Nigeria / Remote",
                salary_range=f"{MARKER} Competitive, stated at offer",
                meta_title=f"{job.title} — Careers at Techmiary"[:70],
                meta_description=(
                    f"{job.title}. Remote-first role at Techmiary Technology Concepts."
                )[:180],
            )
            # One opening stays open-ended, so the "no closing date" path renders.
            if job.closes_at is None and (self.fill_everything or idx > 1):
                job.closes_at = (timezone.now() + timedelta(days=21 + idx * 7)).date()
                job.save(update_fields=["closes_at"])
                self.changed += 1
            n += 1
        self.report("job openings", n)

        m = 0
        for app in JobApplication.objects.all():
            handle = "".join(ch for ch in app.full_name.lower() if ch.isalnum())[:16] or "applicant"
            if self.set_if_blank(
                app,
                portfolio_url=f"https://example.com/{handle}",
                linkedin_url=f"https://www.linkedin.com/in/{handle}/",
                notes=f"{MARKER} Screened. Strong written answers; schedule a call.",
                ip_address=ip(),
            ):
                m += 1
        self.report("job applications", m)

    # -- enquiries ---------------------------------------------------------
    def enquiries(self):
        from contact.models import ContactMessage, NewsletterSubscriber, QuoteRequest

        n = 0
        for idx, q in enumerate(QuoteRequest.objects.all(), start=1):
            if self.set_if_blank(
                q,
                phone=f"+234 80{idx} 000 00{idx:02d}",
                internal_notes=f"{MARKER} Scoped at a high level; awaiting budget confirmation.",
                ip_address=ip(),
            ):
                n += 1
        self.report("quote requests", n)

        m = 0
        subs = list(NewsletterSubscriber.objects.all())
        for idx, s in enumerate(subs, start=1):
            if self.set_if_blank(s, ip_address=ip()):
                m += 1
        # One unsubscribe, so that state is represented too.
        if subs and not any(s.unsubscribed_at for s in subs):
            last = subs[-1]
            last.unsubscribed_at = timezone.now() - timedelta(days=3)
            if hasattr(last, "is_active"):
                last.is_active = False
            last.save()
            self.changed += 1
        self.report("newsletter subscribers", m)

        if self.fill_everything:
            k = 0
            for idx, c in enumerate(ContactMessage.objects.all(), start=1):
                if self.set_if_blank(
                    c,
                    phone=f"+234 80{idx % 9} 000 0{idx:03d}",
                    company=f"{MARKER} Sample Organisation {idx}",
                ):
                    k += 1
            self.report("contact messages", k)

    # -- images ------------------------------------------------------------
    def _attach(self, obj, field, filename, label, w, h, hue, transparent=False):
        """Reuse the placeholder renderer from seed_testdata."""
        from core.management.commands.seed_testdata import Command as Seeder

        try:
            seeder = Seeder()
            content = seeder.image_file(label, w, h, hue, transparent)
        except Exception:
            return False
        getattr(obj, field).save(filename, content, save=True)
        self.changed += 1
        return True
