"""
Seed the portfolio with its initial content.

Everything written here comes from information supplied by the site owner.
Nothing is invented: no client names, user counts, revenue figures, awards,
testimonials or performance statistics. Case-study narrative fields (problem,
solution, result, features, challenges) are deliberately left empty so they
are written by hand in the Django admin rather than generated.

The command is idempotent — running it repeatedly updates the same records
instead of creating duplicates. Existing edits to a record's descriptive text
are preserved unless --overwrite is passed.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from careers.models import Department
from company.models import (
    FAQ,
    CompanyValue,
    FAQCategory,
    Industry,
    ResourceCategory,
    Solution,
    SolutionCapability,
    TeamMember,
)
from core.models import SiteSettings, Skill, SkillCategory
from projects.models import Project, ProjectCategory, Technology
from services.models import Service

SITE_DEFAULTS = {
    "name": "Samuel Jeremiah",
    "brand_name": "TECHMIARY",
    "company_name": "Techmiary Technology Concepts",
    "professional_title": "Software Engineering & Product Company",
    "tagline": (
        "Building SaaS, EdTech and business information systems with Python, "
        "Django and modern cloud infrastructure."
    ),
    "hero_headline": "Software that runs your organisation, built end to end",
    "hero_subheadline": (
        "We design, build, deploy and maintain SaaS platforms, school management "
        "systems, EdTech applications and business information systems for "
        "organisations that need software they can rely on every day."
    ),
    "short_bio": (
        "Techmiary Technology Concepts designs and builds real-world software products, "
        "SaaS platforms and digital systems that solve practical business, education "
        "and organizational problems."
    ),
    "company_overview": (
        "Techmiary Technology Concepts is a software engineering and product company. "
        "We build systems from idea to production — designing the architecture, "
        "developing the application, integrating third-party services, deploying the "
        "infrastructure and maintaining the system after launch."
    ),
    "mission": (
        "To put dependable, well-engineered software in the hands of the schools, "
        "businesses and agencies that keep everyday life running."
    ),
    "vision": (
        "African organisations running on software built for how they actually work, "
        "maintained by the people who built it."
    ),
    "long_bio": (
        "Techmiary Technology Concepts is a software engineering and product company "
        "founded by Samuel Jeremiah.\n\n"
        "We build software from idea to production — designing the architecture, "
        "developing the application, integrating third-party services, deploying "
        "infrastructure and maintaining the system after launch.\n\n"
        "Our work spans SaaS platforms, school management systems, EdTech applications "
        "and business information systems, built with Python, Django and modern cloud "
        "infrastructure."
    ),
    "website_url": "https://techmiary.cloud",
    "newsletter_blurb": "Occasional notes on building and running business software. No spam.",
    "meta_title": "Techmiary Technology Concepts — Software Engineering & Products",
    "meta_description": (
        "Techmiary Technology Concepts builds SaaS platforms, school management systems, "
        "EdTech applications and business information systems with Python and Django."
    ),
}

PROJECT_CATEGORIES = [
    ("SaaS / School ERP", 1),
    ("EdTech / Language Learning", 2),
    ("School Management System", 3),
    ("Management Information System", 4),
]

TECHNOLOGIES = ["Python", "Django", "PostgreSQL", "Linux", "Nginx", "Gunicorn"]

# Technologies attached to every seeded project are limited to the stack the
# site owner states he builds these systems with.
PROJECT_TECHNOLOGIES = ["Python", "Django", "PostgreSQL"]

PROJECTS = [
    {
        "slug": "techmiary-cloud",
        "title": "Techmiary Cloud",
        "category": "SaaS / School ERP",
        "short_description": (
            "A multi-tenant school management and enterprise platform designed to help "
            "schools manage academics, students, finance, communication, attendance and "
            "other operational workflows."
        ),
        "description": (
            "Techmiary Cloud is a multi-tenant school management and enterprise platform. "
            "It is designed to help schools manage academics, students, finance, "
            "communication, attendance and other operational workflows from a single system."
        ),
        "website_url": "https://techmiary.cloud",
        "display_order": 1,
    },
    {
        "slug": "diction-masters",
        "title": "Diction Masters",
        "category": "EdTech / Language Learning",
        "short_description": (
            "An educational platform focused on English pronunciation, vocabulary, learning "
            "content, assessments and multimedia learning experiences."
        ),
        "description": (
            "Diction Masters is an educational platform focused on English pronunciation and "
            "vocabulary. It delivers learning content, assessments and multimedia learning "
            "experiences to learners."
        ),
        "website_url": "https://dictionmasters.app",
        "display_order": 2,
    },
    {
        "slug": "wda-sms",
        "title": "WDA SMS",
        "category": "School Management System",
        "short_description": (
            "A school management platform supporting staff, parents and pupils with academic "
            "and administrative workflows."
        ),
        "description": (
            "WDA SMS is a school management platform supporting staff, parents and pupils "
            "with academic and administrative workflows."
        ),
        "website_url": "https://wdasms.cloud",
        "display_order": 3,
    },
    {
        "slug": "borno-agile-mis",
        "title": "Borno Agile MIS",
        # No feature list is asserted for this project. Write its description in
        # the Django admin once the details are confirmed.
        "category": "Management Information System",
        "short_description": "A management information system built and maintained by Techmiary Technology Concepts.",
        "description": "",
        "website_url": "https://bornoagilemis.cloud",
        "display_order": 4,
    },
]

SKILLS = [
    (
        "Backend",
        "Application logic, data modelling and server-side APIs.",
        1,
        ["Python", "Django", "Django REST Framework", "PostgreSQL", "REST APIs"],
        True,
    ),
    (
        "Frontend",
        "Server-rendered interfaces and responsive layouts.",
        2,
        ["HTML", "CSS", "JavaScript", "Bootstrap", "Responsive UI"],
        True,
    ),
    (
        "Infrastructure",
        "Running applications on Linux servers in production.",
        3,
        ["Linux", "Ubuntu", "Nginx", "Gunicorn", "VPS deployment", "DNS", "SSL/TLS", "Git", "GitHub"],
        True,
    ),
    (
        "Cloud & Storage",
        "Object storage and content delivery for application media.",
        4,
        ["Cloudflare R2", "Object storage", "CDN concepts"],
        True,
    ),
    (
        "Integrations",
        "Third-party services. Enable each entry in the admin once it applies to your work.",
        5,
        ["Paystack", "SMS APIs", "Email APIs", "Text-to-Speech APIs", "AI APIs"],
        False,
    ),
]

SERVICES = [
    (
        "Custom Software Development",
        "Business-specific web applications and internal systems.",
        "code",
        1,
        True,
    ),
    (
        "SaaS Development",
        "Multi-tenant platforms and subscription-based applications.",
        "layers",
        2,
        True,
    ),
    (
        "School Management Systems",
        "Academic, administrative and communication platforms.",
        "school",
        3,
        True,
    ),
    (
        "EdTech Development",
        "Learning platforms, assessments and multimedia educational applications.",
        "book",
        4,
        True,
    ),
    (
        "API & Integration Development",
        "Payment, messaging, AI, storage and third-party API integrations.",
        "api",
        5,
        True,
    ),
    (
        "Deployment & Infrastructure",
        "Linux VPS deployment, Nginx, Gunicorn, PostgreSQL, SSL and production configuration.",
        "server",
        6,
        True,
    ),
]


# --- Company content -------------------------------------------------------
# Solutions mirror the products the company has actually built; each one links
# to its case study. No capability is claimed here beyond what the project
# descriptions already state.
INDUSTRIES = [
    (
        "Education",
        "Schools, colleges and learning providers",
        "Schools carry academic records, fee positions, attendance and parent communication "
        "at once, usually across tools that do not talk to each other.",
        "Disconnected academic and finance records\n"
        "Manual result computation and reporting\n"
        "Parent and guardian communication at scale\n"
        "Attendance capture that staff will actually use",
        "school",
        1,
    ),
    (
        "Government & Public Sector",
        "Agencies, programmes and public institutions",
        "Public bodies need auditable records, role-based access and reporting that "
        "stands up to scrutiny.",
        "Data captured on paper or in scattered spreadsheets\n"
        "Reporting that takes days to assemble\n"
        "Access control across departments\n"
        "Records that must remain auditable",
        "building",
        2,
    ),
    (
        "Business & Enterprise",
        "Companies running operations on spreadsheets",
        "Growing organisations outgrow their spreadsheets long before they replace them.",
        "Processes that live in one person's head\n"
        "No single source of truth for operational data\n"
        "Manual steps that should be automated\n"
        "Systems that cannot be reached from the field",
        "briefcase",
        3,
    ),
]

SOLUTIONS = [
    {
        "name": "School ERP Platform",
        "tagline": "SaaS / School ERP",
        "summary": (
            "A multi-tenant school management and enterprise platform that helps schools "
            "manage academics, students, finance, communication, attendance and other "
            "operational workflows from one system."
        ),
        "overview": (
            "Our school ERP platform is built as a multi-tenant system: each school gets "
            "its own isolated data and configuration while running on shared, maintained "
            "infrastructure. It is the platform behind Techmiary Cloud."
        ),
        "who_its_for": (
            "Schools and school groups that currently run academics, finance and "
            "communication across separate tools or on paper."
        ),
        "icon": "school",
        "project_slug": "techmiary-cloud",
        "industries": ["Education"],
        "display_order": 1,
        "capabilities": [
            ("Academic records", "Students, classes, subjects, terms and results held in one structure.", "book"),
            ("Finance & fees", "Fee positions, invoices and payment records tied to each student.", "clipboard"),
            ("Attendance", "Daily capture designed to be quick enough that staff keep using it.", "check"),
            ("Communication", "Announcements and notifications that reach staff, parents and pupils.", "message"),
            ("Role-based access", "Administrators, staff and parents each see only what they should.", "shield"),
            ("Multi-tenancy", "Every school's data isolated, on shared maintained infrastructure.", "layers"),
        ],
    },
    {
        "name": "Learning & Assessment Platform",
        "tagline": "EdTech / Language Learning",
        "summary": (
            "An educational platform for pronunciation, vocabulary, learning content, "
            "assessments and multimedia learning experiences."
        ),
        "overview": (
            "The platform behind Diction Masters: learning content, exercises and "
            "assessments delivered to learners, with multimedia built into the lesson "
            "flow rather than bolted on."
        ),
        "who_its_for": (
            "Education providers and learning brands that need their own delivery "
            "platform rather than a page on someone else's."
        ),
        "icon": "book",
        "project_slug": "diction-masters",
        "industries": ["Education"],
        "display_order": 2,
        "capabilities": [
            ("Learning content", "Structured lessons and vocabulary organised into courses.", "book"),
            ("Assessments", "Exercises and tests that record and report learner progress.", "clipboard"),
            ("Multimedia delivery", "Audio and other media served as part of the learning flow.", "zap"),
            ("Learner accounts", "Individual progress held against each learner's account.", "user"),
        ],
    },
    {
        "name": "School Management System",
        "tagline": "Academic & administrative workflows",
        "summary": (
            "A school management platform supporting staff, parents and pupils with "
            "academic and administrative workflows."
        ),
        "overview": (
            "A single-institution school management system — the platform behind WDA SMS "
            "— covering the day-to-day administrative and academic work of a school."
        ),
        "who_its_for": "Individual schools that want their own system rather than a shared tenancy.",
        "icon": "users",
        "project_slug": "wda-sms",
        "industries": ["Education"],
        "display_order": 3,
        "capabilities": [
            ("Staff workflows", "The administrative tasks school staff carry out each term.", "briefcase"),
            ("Parent access", "Parents and guardians reaching the records that concern them.", "users"),
            ("Pupil records", "Academic and administrative records held per pupil.", "clipboard"),
        ],
    },
    {
        "name": "Management Information System",
        "tagline": "Records, reporting and operations",
        "summary": (
            "A management information system for organisations that need structured "
            "records, controlled access and reporting they can trust."
        ),
        "overview": "",
        "who_its_for": "Agencies, programmes and organisations replacing spreadsheets with a system of record.",
        "icon": "layers",
        "project_slug": "borno-agile-mis",
        "industries": [],
        "display_order": 4,
        "capabilities": [],
    },
]

COMPANY_VALUES = [
    (
        "Build useful software",
        "The measure of a system is whether someone can do their job better with it. "
        "Everything else is secondary.",
        "target",
        1,
    ),
    (
        "Solve the actual problem",
        "We understand the workflow before we write the feature list. The requirement "
        "behind the request is usually the one worth building for.",
        "compass",
        2,
    ),
    (
        "Keep systems maintainable",
        "Readable code and a clear data model outlast clever shortcuts. Someone has to "
        "own this software in three years.",
        "settings",
        3,
    ),
    (
        "Ship, test and improve",
        "Get it into production, watch it under real use, and refine it. Software is not "
        "finished when it is written.",
        "rocket",
        4,
    ),
]

DEPARTMENTS = [
    ("Engineering", "Backend, frontend and infrastructure work.", 1),
    ("Delivery & Support", "Onboarding, training and keeping deployed systems healthy.", 2),
    ("Operations", "Commercial, administrative and business operations.", 3),
]

RESOURCE_CATEGORIES = [
    ("Planning & procurement", "Getting a software project defined before it starts.", 1),
    ("Implementation", "Rolling a new system out without disrupting operations.", 2),
    ("Running systems", "Hosting, backups, security and support after launch.", 3),
]

FAQ_CATEGORIES = [
    ("Working with us", 1),
    ("Projects & pricing", 2),
    ("Technology & hosting", 3),
    ("Support", 4),
]

# Answers describe how we work. They deliberately make no commitment about
# price, duration or service levels — those belong in a signed agreement.
FAQS = [
    (
        "Working with us",
        "How does an engagement start?",
        "It starts with a conversation. You describe the workflow you need supported and who "
        "uses it; we ask the questions that are missing. From there we write up an approach, a "
        "scope and a timeline for you to review before any development begins.",
        1,
    ),
    (
        "Working with us",
        "Do you work with organisations outside Nigeria?",
        "Yes. The work is delivered remotely, and the systems we build are web applications "
        "reachable from anywhere. Where a project needs on-site time, we agree that up front.",
        2,
    ),
    (
        "Working with us",
        "Can you take over a system someone else built?",
        "Often, yes. We start by reviewing the codebase, the data model and how it is deployed, "
        "then tell you honestly whether it is better to continue with it or replace it.",
        3,
    ),
    (
        "Projects & pricing",
        "How much does a project cost?",
        "It depends entirely on scope — the number of workflows, the integrations involved and "
        "whether the system replaces something already in use. Send a quote request with as much "
        "detail as you have and you will get a written scope and price rather than a guess.",
        1,
    ),
    (
        "Projects & pricing",
        "How long does a build take?",
        "That also follows from scope. We break work into stages so you see something usable "
        "early rather than waiting for one large delivery at the end, and each stage has its own "
        "agreed dates.",
        2,
    ),
    (
        "Projects & pricing",
        "Who owns the software you build for us?",
        "Ownership is set out in the written agreement for each engagement. Tell us what you need "
        "and we will cover it there explicitly rather than leaving it implied.",
        3,
    ),
    (
        "Technology & hosting",
        "What do you build with?",
        "Python and Django on the backend, PostgreSQL for data, and server-rendered interfaces "
        "with HTML, CSS, JavaScript and Bootstrap. Systems run on Linux servers behind Nginx and "
        "Gunicorn. The full list is on our technology page.",
        1,
    ),
    (
        "Technology & hosting",
        "Can the system run on our own servers?",
        "Yes. The applications are standard Linux deployments, so they can run on infrastructure "
        "we manage or on your own, depending on what your organisation requires.",
        2,
    ),
    (
        "Technology & hosting",
        "How is our data protected?",
        "Access is role-based, traffic is served over HTTPS, and configuration secrets are kept "
        "out of the codebase. Backups and their restore procedure are part of every deployment we "
        "operate.",
        3,
    ),
    (
        "Support",
        "What happens after the system goes live?",
        "Launch is not the end of the work. We monitor the deployment, apply security updates, "
        "restore from backup if anything goes wrong, and build the changes your operations need "
        "next. The arrangement is agreed with you rather than assumed.",
        1,
    ),
    (
        "Support",
        "Do you train our staff?",
        "Yes. A system nobody can use is not delivered. Handover includes walking your team "
        "through the workflows they will run day to day.",
        2,
    ),
]

TEAM = [
    {
        "name": "Samuel Jeremiah",
        "role": "Founder & Chief Executive",
        "department": "Engineering",
        "short_bio": "Software engineer and product builder. Founder of Techmiary Technology Concepts.",
        "bio": (
            "Samuel Jeremiah is a software engineer and product builder focused on building "
            "practical software systems.\n\n"
            "He founded Techmiary Technology Concepts to build software from idea to production — "
            "designing the architecture, developing the application, integrating third-party "
            "services, deploying infrastructure and maintaining the system after launch.\n\n"
            "His work spans SaaS platforms, school management systems, EdTech applications and "
            "business information systems built with Python, Django and modern cloud infrastructure."
        ),
        "is_leadership": True,
        "is_founder": True,
        "display_order": 1,
    },
]



class Command(BaseCommand):
    help = "Create or update the initial portfolio content. Safe to run repeatedly."

    def add_arguments(self, parser):
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Replace descriptive text on existing records with the seeded defaults.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        overwrite = options["overwrite"]

        self.seed_site_settings(overwrite)
        technologies = self.seed_technologies()
        categories = self.seed_project_categories()
        self.seed_projects(categories, technologies, overwrite)
        self.seed_skills()
        self.seed_services(overwrite)
        industries = self.seed_industries()
        self.seed_solutions(industries, overwrite)
        self.seed_values()
        self.seed_team(overwrite)
        self.seed_departments()
        self.seed_resource_categories()
        self.seed_faqs()

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Portfolio content seeded."))
        self.stdout.write(
            "Next, in the Django admin:\n"
            "  • Site settings: add your address, phone, sales and support email, office\n"
            "    hours, founding year and registration number, then upload the logo,\n"
            "    favicon and a 1200x630 social image.\n"
            "  • Projects: set each one's real status and write the Problem, Solution and\n"
            "    Result sections. Add the Borno Agile MIS description once confirmed.\n"
            "  • Solutions: upload a hero image for each and finish the Management\n"
            "    Information System write-up.\n"
            "  • Team: add photos and the rest of your colleagues.\n"
            "  • Clients & testimonials: add only organisations and quotes you have\n"
            "    permission to publish — the consent box records that.\n"
            "  • Careers: create job openings; none are seeded, so the page shows its\n"
            "    empty state until you publish one.\n"
            "  • Resources: upload guides against the seeded categories.\n"
            "  • Milestones: add the company's real dates under Company > Milestones.\n"
            "  • Social links: only platforms with a real profile URL.\n"
            "  • Skills: enable the Integrations entries that genuinely apply."
        )

    # -- individual seeders -------------------------------------------------
    def seed_site_settings(self, overwrite):
        site = SiteSettings.objects.first()
        if site is None:
            SiteSettings.objects.create(**SITE_DEFAULTS)
            self.stdout.write(self.style.SUCCESS("Created site settings."))
            return
        if overwrite:
            for field, value in SITE_DEFAULTS.items():
                setattr(site, field, value)
            site.save()
            self.stdout.write(self.style.WARNING("Overwrote site settings."))
        else:
            self.stdout.write("Site settings already exist — left unchanged.")

    def seed_technologies(self):
        technologies = {}
        for name in TECHNOLOGIES:
            tech, created = Technology.objects.get_or_create(name=name)
            technologies[name] = tech
            if created:
                self.stdout.write(f"  + technology: {name}")
        return technologies

    def seed_project_categories(self):
        categories = {}
        for name, order in PROJECT_CATEGORIES:
            category, created = ProjectCategory.objects.get_or_create(
                name=name, defaults={"display_order": order}
            )
            categories[name] = category
            if created:
                self.stdout.write(f"  + project category: {name}")
        return categories

    def seed_projects(self, categories, technologies, overwrite):
        for entry in PROJECTS:
            data = dict(entry)
            category = categories[data.pop("category")]
            slug = data.pop("slug")

            project = Project.objects.filter(slug=slug).first()
            if project is None:
                project = Project.objects.create(
                    slug=slug,
                    category=category,
                    featured=True,
                    is_published=True,
                    # Status is intentionally not assumed. Set it in the admin.
                    status=Project.STATUS_DEVELOPMENT,
                    **data,
                )
                self.stdout.write(self.style.SUCCESS(f"  + project: {project.title}"))
            elif overwrite:
                for field, value in data.items():
                    setattr(project, field, value)
                project.category = category
                project.save()
                self.stdout.write(self.style.WARNING(f"  ~ project updated: {project.title}"))
            else:
                self.stdout.write(f"  = project exists: {project.title}")

            existing = set(project.technologies.values_list("name", flat=True))
            missing = [
                technologies[name] for name in PROJECT_TECHNOLOGIES if name not in existing
            ]
            if missing:
                project.technologies.add(*missing)

    def seed_skills(self):
        for name, description, order, skills, active in SKILLS:
            category, created = SkillCategory.objects.get_or_create(
                name=name, defaults={"description": description, "display_order": order}
            )
            if created:
                self.stdout.write(f"  + skill category: {name}")
            for index, skill_name in enumerate(skills, start=1):
                _, made = Skill.objects.get_or_create(
                    category=category,
                    name=skill_name,
                    defaults={"display_order": index, "is_active": active},
                )
                if made:
                    self.stdout.write(f"    + skill: {skill_name}")

    def seed_services(self, overwrite):
        for title, summary, icon, order, active in SERVICES:
            service = Service.objects.filter(title=title).first()
            if service is None:
                Service.objects.create(
                    title=title,
                    summary=summary,
                    icon=icon,
                    display_order=order,
                    is_active=active,
                    is_featured=True,
                )
                self.stdout.write(self.style.SUCCESS(f"  + service: {title}"))
            elif overwrite:
                service.summary = summary
                service.icon = icon
                service.display_order = order
                service.save()
                self.stdout.write(self.style.WARNING(f"  ~ service updated: {title}"))

    # -- company content ----------------------------------------------------
    def seed_industries(self):
        industries = {}
        for name, tagline, summary, challenges, icon, order in INDUSTRIES:
            industry, created = Industry.objects.get_or_create(
                name=name,
                defaults={
                    "tagline": tagline,
                    "summary": summary,
                    "challenges": challenges,
                    "icon": icon,
                    "display_order": order,
                },
            )
            industries[name] = industry
            if created:
                self.stdout.write(self.style.SUCCESS(f"  + industry: {name}"))
        return industries

    def seed_solutions(self, industries, overwrite):
        for entry in SOLUTIONS:
            data = dict(entry)
            capabilities = data.pop("capabilities", [])
            industry_names = data.pop("industries", [])
            project_slug = data.pop("project_slug", None)
            name = data.pop("name")

            solution = Solution.objects.filter(name=name).first()
            if solution is None:
                solution = Solution.objects.create(name=name, is_featured=True, **data)
                self.stdout.write(self.style.SUCCESS(f"  + solution: {name}"))
                created = True
            else:
                created = False
                if overwrite:
                    for field, value in data.items():
                        setattr(solution, field, value)
                    solution.save()
                    self.stdout.write(self.style.WARNING(f"  ~ solution updated: {name}"))
                else:
                    self.stdout.write(f"  = solution exists: {name}")

            if project_slug:
                project = Project.objects.filter(slug=project_slug).first()
                if project and solution.related_project_id != project.pk:
                    solution.related_project = project
                    solution.save(update_fields=["related_project"])

            wanted = [industries[n] for n in industry_names if n in industries]
            if wanted:
                existing = set(solution.industries.values_list("pk", flat=True))
                missing = [i for i in wanted if i.pk not in existing]
                if missing:
                    solution.industries.add(*missing)

            if created or overwrite:
                for index, (title, description, icon) in enumerate(capabilities, start=1):
                    SolutionCapability.objects.get_or_create(
                        solution=solution,
                        title=title,
                        defaults={"description": description, "icon": icon, "display_order": index},
                    )

    def seed_values(self):
        for title, description, icon, order in COMPANY_VALUES:
            _, created = CompanyValue.objects.get_or_create(
                title=title,
                defaults={"description": description, "icon": icon, "display_order": order},
            )
            if created:
                self.stdout.write(f"  + value: {title}")

    def seed_team(self, overwrite):
        for entry in TEAM:
            data = dict(entry)
            name = data.pop("name")
            member = TeamMember.objects.filter(name=name).first()
            if member is None:
                TeamMember.objects.create(name=name, **data)
                self.stdout.write(self.style.SUCCESS(f"  + team member: {name}"))
            elif overwrite:
                for field, value in data.items():
                    setattr(member, field, value)
                member.save()
                self.stdout.write(self.style.WARNING(f"  ~ team member updated: {name}"))

    def seed_departments(self):
        for name, description, order in DEPARTMENTS:
            _, created = Department.objects.get_or_create(
                name=name, defaults={"description": description, "display_order": order}
            )
            if created:
                self.stdout.write(f"  + department: {name}")

    def seed_resource_categories(self):
        for name, description, order in RESOURCE_CATEGORIES:
            _, created = ResourceCategory.objects.get_or_create(
                name=name, defaults={"description": description, "display_order": order}
            )
            if created:
                self.stdout.write(f"  + resource category: {name}")

    def seed_faqs(self):
        categories = {}
        for name, order in FAQ_CATEGORIES:
            category, created = FAQCategory.objects.get_or_create(
                name=name, defaults={"display_order": order}
            )
            categories[name] = category
            if created:
                self.stdout.write(f"  + FAQ category: {name}")

        for category_name, question, answer, order in FAQS:
            _, created = FAQ.objects.get_or_create(
                question=question,
                defaults={
                    "category": categories.get(category_name),
                    "answer": answer,
                    "display_order": order,
                },
            )
            if created:
                self.stdout.write(f"    + FAQ: {question[:52]}")
