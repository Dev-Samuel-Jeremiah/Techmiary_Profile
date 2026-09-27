"""
Replace the sample content with real, sourced content.

Every statement written here traces to one of Samuel Jeremiah's own sources:
the public GitHub profile README, the project READMEs, or the project code
itself (model names, installed apps, settings). Where no source exists — a
client's consent, a testimonial, a date of employment — nothing is invented:
the sample row is removed and the gap is reported, so the page either shows
real content or hides the section.

    python manage.py load_real_content            # apply
    python manage.py load_real_content --dry-run  # report only, change nothing

Idempotent: re-running updates the same records rather than duplicating them.
"""
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify

MARKER = "[sample]"

# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------
GITHUB = "https://github.com/Dev-Samuel-Jeremiah"
BUSINESS_EMAIL = "techmiarytechnology@gmail.com"   # Techmiary-Technology README
PERSONAL_EMAIL = "devsamueljeremiah@gmail.com"     # GitHub profile README
PHONE = "+234 701 099 6154"                        # Techmiary-Technology README
WHATSAPP = "https://wa.me/2347010996154"           # Techmiary-Technology README

# Values this assistant wrote into the live record as placeholders during
# earlier testing. They are cleared only if still unchanged, so anything the
# owner has since typed in is left alone.
MY_PLACEHOLDERS = {
    "address": {
        "7 Circular Road\nMaiduguri, Borno State, Nigeria",
        "[sample] 14 Baga Road, Maiduguri, Borno State, Nigeria",
    },
    "secondary_phone": {"+234 800 000 0001"},
    "office_hours": {"Mon-Fri, 08:30-17:30 WAT", "Mon–Fri, 09:00–17:00 WAT"},
    "support_email": {"support@techmiary.tech"},
    "sales_email": {"sales@techmiary.tech"},
    "email": {"hello@techmiary.tech", "hello@example.com"},
    "twitter_handle": {"techmiary", "example"},
    "founded_year": {2021},
    "linkedin_url": {"https://www.linkedin.com/in/example/"},
    "twitter_url": {"https://x.com/example"},
    "github_url": {"https://github.com/example"},
    "whatsapp_url": {"https://wa.me/2348000000000"},
}

COMPANY_OVERVIEW = (
    "Techmiary Technology Concepts is a Nigerian software company that designs, "
    "builds, deploys and maintains software for schools, training institutions "
    "and organisations — web platforms, desktop programs and Android and iOS "
    "apps, for places that are always online and places that are not. Our "
    "work covers the whole path from "
    "requirements to a running system: data modelling, backend development, "
    "integrations such as payments and SMS, deployment on Linux servers, and "
    "support after launch.\n\n"
    "To date we have developed and maintained around 10 client platforms and "
    "around 15 websites and web applications, including multi-tenant school "
    "ERPs, a multi-school management information system, examination and "
    "registration portals, reporting dashboards and learning platforms. We "
    "also build desktop software that runs fully offline, such as a result "
    "manager for a school's own computers, and mobile apps for Android and "
    "iPhone."
)
LONG_BIO = (
    "Samuel Jeremiah is a Python and Django software engineer and the founder of "
    "Techmiary Technology Concepts. He builds and deploys practical web "
    "applications, business management systems and REST APIs, covering backend "
    "development, database design, authentication, frontend integration and "
    "deployment.\n\n"
    "His background in ICT education and technical infrastructure — as an ICT "
    "instructor and computer lab administrator — shapes how he works: "
    "troubleshooting real systems, explaining technical concepts plainly, and "
    "turning the requirements of administrators and teachers into software they "
    "can rely on.\n\n"
    "Alongside client work he has supported more than 20 university students "
    "with their final-year software projects, from requirements gathering "
    "through development, debugging and deployment."
)
SHORT_BIO = (
    "Python and Django software engineer building school management systems, "
    "ERPs, learning platforms and REST APIs — from requirements to production."
)
HERO_SUBHEADLINE = (
    "We design, build, deploy and maintain school management systems, SaaS "
    "platforms, EdTech applications and business systems — on the web, on "
    "the desktop and on Android and iOS, online or fully offline."
)

# ---------------------------------------------------------------------------
# Projects — facts from each project's README and installed apps
# ---------------------------------------------------------------------------
PROJECTS = [
    {
        "slug": "techmiary-cloud",
        "title": "Techmiary Cloud",
        "category": "SaaS / School ERP",
        "year": 2026,
        "website_url": "https://techmiary.cloud",
        "github_url": "",
        "short_description": (
            "A multi-tenant school ERP covering academics, CBT, results, "
            "finance, hostel, communications and inventory for every school "
            "on one platform."
        ),
        "description": (
            "Techmiary Cloud is the institutional ERP behind Techmiary "
            "Institute of Technology and the platform we offer to schools. "
            "It is built with Django 5.2 on PostgreSQL and serves several "
            "schools from one deployment, each with its own data and users."
        ),
        "problem": (
            "A school's work is spread across separate tools: admissions and "
            "results in spreadsheets, fees in a ledger, parent contact over "
            "phone and chat. Nothing shares a record, so every termly report "
            "and every fee query means reconciling by hand."
        ),
        "solution": (
            "One platform where every module works from the same student "
            "record. Staff, students and parents each sign in to the parts "
            "their role allows. Fees are paid online through Paystack and "
            "posted to the student's wallet; results are entered once and "
            "published in batches; parents are reached by email and SMS from "
            "the same system that holds their child's record."
        ),
        "result": (
            "In production at techmiary.cloud, used by Techmiary Institute "
            "of Technology and offered to other schools as a hosted service."
        ),
        "architecture_description": (
            "Django 5.2 on Python 3.12, served by Gunicorn behind Nginx, with "
            "PostgreSQL for data. A tenants app isolates each school. Email is "
            "sent through Gmail SMTP; SMS goes through Termii with Africa's "
            "Talking as fallback. Receipts and reports are generated as PDF "
            "with ReportLab and as Excel with openpyxl. Scheduled "
            "communication campaigns run from a management command on cron."
        ),
        "technologies": ["Python", "Django", "PostgreSQL", "Gunicorn", "Nginx",
                         "Bootstrap", "Paystack", "Termii", "ReportLab", "openpyxl"],
        "features": [
            ("Multi-tenant schools", "Each school runs on the shared platform with its own data, staff and students."),
            ("Role-based access", "Separate access for administrators, teachers, accounts staff, parents and students."),
            ("Academics and timetable", "Sessions, terms, classes, student promotion and a timetable builder."),
            ("Computer-based testing", "Online examinations with results feeding the results module."),
            ("Results", "Score entry, term results and batch publishing."),
            ("Finance", "Fee structures, a wallet per student, Paystack payments, PDF receipts and payroll."),
            ("Hostel", "Buildings, beds, boarder profiles, exeats, a visitor log and incident records."),
            ("Communications", "Email and SMS campaigns, fee reminders and automatic notifications."),
            ("Inventory", "Asset tracking, stock movements and maintenance records."),
            ("ID cards and announcements", "Student ID cards, and announcements targeted to the whole school or a class."),
            ("Online registration", "A public registration flow with online payment and confirmation pages."),
        ],
        "challenges": [
            ("SMS that still arrives when a provider fails",
             "Messages go through Termii first and fall back to Africa's Talking, so a single provider outage does not stop fee reminders or result notifications."),
            ("Campaigns that send on schedule",
             "Scheduled email and SMS campaigns are dispatched by a management command run from cron, rather than depending on someone being logged in."),
        ],
    },
    {
        "slug": "wda-sms",
        "title": "WDA SMS",
        "category": "School Management System",
        "year": 2026,
        "website_url": "https://www.wdasms.cloud",
        "github_url": "",
        "short_description": (
            "A full school management system for a private school in Jos — "
            "academics, CBT, results, fee wallets, hostel and parent "
            "communication."
        ),
        "description": (
            "WDA SMS is a production school ERP built with Django 5.2 for a "
            "private school in Jos, Plateau State. It runs the school's "
            "academic, financial and boarding administration and gives "
            "parents and students their own portal."
        ),
        "problem": (
            "A school with day students and boarders needs fees, hostel "
            "billing, results and parent communication to agree with each "
            "other, and payments must be checked before they change what a "
            "family owes."
        ),
        "solution": (
            "A single system with student, parent and staff accounts. Each "
            "student has a wallet that parents fund; payments go through an "
            "approval workflow before they are applied; hostel fees bill "
            "alongside school fees. Parents receive their portal login details, fee "
            "reminders and result notifications by email and SMS."
        ),
        "result": "Live at wdasms.cloud and used for the school's day-to-day administration.",
        "architecture_description": (
            "Django 5.2.7 on Python 3.12 with PostgreSQL, served by Gunicorn "
            "behind Nginx. Paystack for online payments, Termii with Africa's "
            "Talking fallback for SMS, Gmail SMTP for email, ReportLab for PDF "
            "receipts and openpyxl for Excel billing exports."
        ),
        "technologies": ["Python", "Django", "PostgreSQL", "Gunicorn", "Nginx",
                         "Bootstrap", "Paystack", "Termii", "ReportLab", "openpyxl"],
        "features": [
            ("Student, parent and staff accounts", "Students sign in with their admission number and parents with their email; staff have role-based permissions."),
            ("Student wallets", "Each student has a wallet that parents top up, with every credit and debit recorded as a transaction."),
            ("Payment approval workflow", "Payments move from pending to approved before they are applied, with PDF receipts."),
            ("Real-time billing report", "Administrators see every student's fee status at once, exportable to Excel."),
            ("Hostel management", "Rooms and beds, boarder profiles with medical details, exeats, visitors, incidents and meal plans."),
            ("CBT and results", "Online examinations, score entry and term results."),
            ("Timetable and promotion", "A timetable builder and end-of-session student promotion."),
            ("Parent communication", "Campaigns to all parents, a class, boarders or debtors, plus login-detail notifications."),
            ("Payroll", "Staff salary processing."),
            ("Security monitoring", "A dedicated app for monitoring access to the system."),
        ],
        "challenges": [
            ("Payments that cannot half-apply",
             "Approving a payment updates the payment, the wallet and the ledger inside one database transaction, so an approval either completes fully or not at all."),
        ],
    },
    {
        "slug": "school-result-manager",
        "title": "School Result Manager",
        "category": "Desktop Application",
        "year": 2026,
        "website_url": "",
        "github_url": "",
        "short_description": (
            "Offline desktop software for a school: register students, enter "
            "CA and exam scores, and print term result sheets — no internet "
            "needed, on Windows and Linux."
        ),
        "description": (
            "School Result Manager is desktop software we built for a school "
            "that needed to produce term results on its own computers, without "
            "depending on an internet connection. It works for both primary "
            "and secondary sections and installs as an ordinary program on "
            "Windows and Linux."
        ),
        "problem": (
            "Result time is when a school can least afford to wait on a "
            "network. Scores arrive from many teachers, positions and averages "
            "have to be worked out correctly — including ties — and every "
            "student needs a printed sheet, often on a deadline and in a "
            "building where the internet is unreliable or absent."
        ),
        "solution": (
            "A self-contained program that keeps everything on the school's "
            "computer. The admin sets up classes, subjects and teacher "
            "accounts; each teacher sees only the subjects assigned to them "
            "and types CA 1, CA 2 and exam scores into a grid that works out "
            "totals and grades as they type. Class teachers add attendance and "
            "comments, the head adds the principal's comment, and the school "
            "prints one A4 sheet per student, a whole class to PDF, or a class "
            "broadsheet."
        ),
        "result": "Delivered to a school and used to produce its term result sheets offline.",
        "architecture_description": (
            "Python with PySide6 (Qt) for the interface and SQLite for storage, "
            "kept in one database file plus a photos folder in the user's "
            "application-data directory. Passwords are stored as PBKDF2 "
            "hashes. Result sheets are rendered from HTML through Qt's print "
            "system, which also produces the PDFs. PyInstaller packages the "
            "program into a folder that runs on a PC without Python installed."
        ),
        "technologies": ["Python", "PySide6", "SQLite", "PyInstaller"],
        "features": [
            ("Works fully offline", "No internet connection is needed to enter scores, compute results or print."),
            ("Windows and Linux", "Packaged as an ordinary program; the target PC does not need Python installed."),
            ("Student records", "Passport photo, class, guardian details, state and LGA; promote, move, or mark as graduated or left."),
            ("Teacher accounts", "Each teacher sees only the subjects assigned to them."),
            ("Fast score entry", "CA 1, CA 2 and exam in a grid, with totals and grades as you type — or paste a column straight from Excel."),
            ("Positions and averages", "Subject and class positions with ties sharing a place, class averages, and highest and lowest per subject."),
            ("Cumulative results", "Second and third term sheets carry earlier term totals and a cumulative average."),
            ("Printing and PDF", "One A4 sheet per student, selected students or a whole class, a class PDF, or a broadsheet."),
            ("Configurable grading", "School details and logo, score maximums, and editable grading scales for primary and secondary."),
            ("Backup and restore", "Copy the whole database to a flash drive from the File menu, and restore it when needed."),
        ],
        "challenges": [
            ("Positions that treat ties fairly",
             "Students with the same score share a position and the next position is skipped — 1st, 2nd, 2nd, 4th — as schools expect on a result sheet."),
            ("Backups that are safe while the program is running",
             "Backups use SQLite's own backup mechanism rather than copying the file, and a restore checks that the file really is a School Result Manager database before replacing anything."),
        ],
    },
    {
        "slug": "borno-agile-mis",
        "title": "Borno Agile MIS",
        "category": "Management Information System",
        "year": 2026,
        "website_url": "https://www.bornoagilemis.org",
        "github_url": "",
        "short_description": (
            "A multi-school management information system with bulk import "
            "of beneficiary records exported from Agile MIS and KoboToolbox."
        ),
        "description": (
            "Borno Agile MIS is a Django management information system that "
            "brings the administration of many schools into one platform — "
            "schools, students, cohorts, enrolments, payments and attendance "
            "— and can take in field data collected with KoboToolbox."
        ),
        "problem": (
            "Programme data is collected in the field and exported as "
            "spreadsheets. Turning those exports into usable school and "
            "student records by hand is slow, and re-importing an updated "
            "export easily creates duplicates."
        ),
        "solution": (
            "An import tool that reads Agile MIS and KoboToolbox CSV or Excel "
            "exports, recognises their column headers, and creates or updates "
            "schools, students and enrolments without duplicating them. The "
            "rest of the MIS then works from those records: approvals, "
            "payments, attendance and reports."
        ),
        "result": "Deployed at bornoagilemis.org.",
        "architecture_description": (
            "Django on PostgreSQL with Bootstrap and JavaScript on the front "
            "end. The import engine parses CSV and .xlsx files and stores "
            "fields that have no dedicated column — identifiers, cohort, "
            "caregiver details — alongside the student record."
        ),
        "technologies": ["Python", "Django", "PostgreSQL", "Bootstrap", "JavaScript", "openpyxl"],
        "features": [
            ("Bulk import from field exports", "Upload CSV or Excel exported from Agile MIS or KoboToolbox; headers are detected automatically."),
            ("No-duplicate re-imports", "Existing schools and students are matched and updated rather than created again."),
            ("School management", "Schools by name, LGA, type and status, with generated school IDs."),
            ("Students and cohorts", "Student records, cohorts, and a history of promotions."),
            ("Enrolment approvals", "An approve-or-reject queue for enrolments."),
            ("Payments", "Payment schedules, recorded payments and printable receipts."),
            ("Attendance", "Attendance sessions taken per cohort."),
            ("Reports and activity log", "Attendance, performance and revenue reports, plus an audit trail of actions."),
            ("Import template", "A downloadable CSV template with every supported header."),
        ],
        "challenges": [
            ("Matching records that were typed by hand",
             "Field exports spell the same school differently, so schools are matched case-insensitively and cached for the length of an import, and students are matched by email in one bulk query rather than row by row."),
        ],
    },
    {
        "slug": "diction-masters",
        "title": "Diction Masters",
        "category": "EdTech / Language Learning",
        "year": 2026,
        "website_url": "https://www.dictionmasters.app",
        "github_url": f"{GITHUB}/dictionmasters",
        "short_description": (
            "A British English pronunciation tutor for Nigerian school "
            "children — video lessons, audio drills and speaking practice "
            "behind school-controlled access codes."
        ),
        "description": (
            "Diction Masters gives every Nigerian school child a private "
            "British English tutor: video lessons, audio drills, speaking "
            "practice and teacher feedback. Schools control who gets in, and "
            "the platform ships as a website and as Android and iPhone apps."
        ),
        "problem": (
            "Pronunciation is learned by hearing and repeating, but most "
            "learners have no model speaker to hear and no structured way to "
            "practise each sound. Schools also need to control access "
            "rather than leave it open to anyone."
        ),
        "solution": (
            "The 44 Academy teaches the 44 sounds of English, one lesson per "
            "sound, each with an articulation video, a word bank, sentence "
            "practice, passages, conversations, tongue twisters and minimal "
            "pairs. Schools register, then issue single-use access codes to "
            "their teachers and students."
        ),
        "result": "Public landing page, registration for schools and individuals, code-based joining and the 44 Academy are built.",
        "architecture_description": (
            "Django with a custom email-login user model and roles for school "
            "admins, teachers, students and individuals. Lesson media can be "
            "uploaded or served from a CDN such as Cloudflare R2. The native "
            "mobile apps open the website, so anything deployed appears in "
            "the apps automatically. The Android and iPhone apps are built with "
            "Capacitor and ship their own loading and offline screens."
        ),
        "technologies": ["Python", "Django", "SQLite", "Cloudflare R2", "JavaScript", "Capacitor"],
        "features": [
            ("44 Academy", "A lesson for each of the 44 sounds of English, grouped into vowels, diphthongs and consonants."),
            ("Tabbed lessons", "Articulation video, word bank, sentences, passages, conversations, tongue twisters and minimal pairs."),
            ("School access codes", "School admins generate single-use codes that create a teacher or student account already linked to the school."),
            ("Three ways to register", "As a school, as an individual, or by joining with a code."),
            ("Admin-managed content", "Every lesson tab is edited from the admin as inline forms — no code changes to add a lesson."),
            ("Android and iPhone apps", "Native Capacitor apps that open the live site with phone features on top — haptics, network awareness and a built-in offline screen — so updates reach them without a new release."),
        ],
        "challenges": [
            ("Access that schools control",
             "A single-use code both creates the account and ties it to the right school and role, so a school admin decides exactly who joins."),
        ],
    },
    {
        "slug": "livequiz",
        "title": "LiveQuiz",
        "category": "EdTech / Assessment",
        "year": 2026,
        "website_url": "",
        "github_url": "",
        "short_description": (
            "Real-time multiplayer quiz rooms over WebSockets, with a live "
            "countdown, live scores and a final leaderboard."
        ),
        "description": (
            "LiveQuiz runs quiz rooms where every player answers the same "
            "question at the same time. It is built on Django Channels, with "
            "subjects and topics by education level, a story mode, culture "
            "quiz packs, certificates and paid plans."
        ),
        "problem": (
            "A quiz played together only works if everyone sees the same "
            "question and the same clock. Polling a server for updates makes "
            "players drift apart and makes the leaderboard lag behind."
        ),
        "solution": (
            "Each room is a WebSocket group. The server holds the room's "
            "state, runs the countdown and pushes each question, score "
            "update and the final leaderboard to every player at once."
        ),
        "result": "",
        "architecture_description": (
            "Django with Channels on the Daphne ASGI server and Redis as the "
            "channel layer. Questions are drawn at random for the host's "
            "chosen level, field, subject and topic. Background jobs — "
            "subscription expiry reminders and clean-up of old guest "
            "submissions — run on APScheduler. A JWT-authenticated REST API "
            "and social login sit alongside the web interface."
        ),
        "technologies": ["Python", "Django", "Django Channels", "Redis", "Daphne",
                         "Django REST Framework", "JavaScript"],
        "features": [
            ("Live rooms", "Players join a room by code and play the same questions in step."),
            ("Server-run countdown", "The clock runs on the server, so every player sees the same time remaining."),
            ("Live scores and leaderboard", "Scores update as answers arrive, ending with a final leaderboard."),
            ("Battle mode", "Rooms can be grouped into a battle for team-against-team play."),
            ("Question bank by level", "Education levels, fields of study, subjects and topics."),
            ("Story mode and culture packs", "Story levels with slides and quizzes, and culture quiz packs that can be unlocked."),
            ("Certificates and plans", "Certificates for players, and paid plans that raise question limits and duration."),
            ("Guest play", "Guests can take part; old guest submissions are cleaned up automatically."),
        ],
        "challenges": [
            ("Keeping every player on the same clock",
             "The countdown runs server-side and is broadcast to the room's group, rather than trusting each browser's timer."),
        ],
    },
    {
        "slug": "techmiary-institute-website",
        "title": "Techmiary Institute of Technology Website",
        "category": "Website",
        "year": 2026,
        "website_url": "",
        "github_url": f"{GITHUB}/Techmiary-Technology",
        "short_description": (
            "The website of Techmiary Institute of Technology, a coding "
            "academy offering hands-on tech training for kids, youths and "
            "professionals."
        ),
        "description": (
            "A Django website for Techmiary Institute of Technology with "
            "programme pages, course listings and enrolment, and a contact "
            "page with an FAQ."
        ),
        "problem": "",
        "solution": (
            "A fast, content-led site where prospective learners can browse "
            "courses and enrol, backed by small JSON endpoints for the "
            "enrolment and contact forms."
        ),
        "result": "",
        "architecture_description": "",
        "technologies": ["Python", "Django", "JavaScript", "Bootstrap"],
        "features": [
            ("Courses and enrolment", "Course listings with an enrolment form."),
            ("Contact and FAQ", "A contact form and an FAQ accordion."),
            ("Form APIs", "Enrolment and contact submissions handled by JSON endpoints."),
        ],
        "challenges": [],
    },
    {
        "slug": "techmiary-erp",
        "title": "Techmiary ERP",
        "category": "Business Management",
        "year": 2026,
        "website_url": "",
        "github_url": f"{GITHUB}/Techmiary_ERP",
        "short_description": (
            "A business management platform built with Django to support "
            "structured administrative and organisational workflows."
        ),
        "description": (
            "Techmiary ERP is a Django, database-driven platform for running "
            "an organisation's administrative workflows in one place."
        ),
        "problem": "",
        "solution": "",
        "result": "",
        "architecture_description": "",
        "technologies": ["Python", "Django"],
        "features": [],
        "challenges": [],
    },
]

# Stated in the GitHub profile README ("Live Application").
LIVE_PER_PROFILE = {"wda-sms", "borno-agile-mis"}
# Delivered, as stated by the owner on 2026-09-27.
LIVE_PER_OWNER = {"school-result-manager"}

SERVICES = [
    # (existing title to update, new title, icon, summary, deliverables)
    ("Custom Software Development", "Django Web Applications", "code",
     "Database-driven web applications built with Python and Django around how your organisation already works.",
     ["Requirements and data model", "Authentication and role-based access",
      "Administrative dashboards and reporting", "Deployed and maintained on our servers"]),
    ("SaaS Development", "SaaS & Multi-tenant Platforms", "layers",
     "One deployment serving many organisations, each with its own data — the model behind Techmiary Cloud.",
     ["Tenant isolation", "Per-organisation users and roles",
      "Online payments with Paystack", "Hosting, backups and updates"]),
    ("School Management Systems", "School Management Systems", "school",
     "Academics, results, fees, hostel and parent communication in one system, as used by the schools on our platforms.",
     ["Admissions, classes and promotion", "CBT, score entry and result publishing",
      "Fees, student wallets and receipts", "Parent and student portals"]),
    ("EdTech Development", "EdTech & Assessment Platforms", "book",
     "Learning and assessment platforms — pronunciation lessons, computer-based tests and live quizzes.",
     ["Structured lessons with audio and video", "Computer-based examinations",
      "Real-time quizzes over WebSockets", "Access codes and learner accounts"]),
    ("API & Integration Development", "REST APIs & Integrations", "api",
     "REST APIs with Django REST Framework, and the integrations real systems depend on.",
     ["REST APIs with JWT authentication", "Paystack payments",
      "SMS through Termii and Africa's Talking", "Email, PDF and Excel generation"]),
    ("Deployment & Infrastructure", "Deployment & Infrastructure", "server",
     "Production deployment on Linux with Nginx and Gunicorn, and the upkeep after launch.",
     ["Linux server setup", "Nginx, Gunicorn and PostgreSQL or SQLite",
      "HTTPS certificates", "Backups, monitoring and updates"]),
    (None, "Desktop & Offline Software", "monitor",
     "Programs that install on your own computers and keep working without the internet — like the result manager we built for a school.",
     ["Windows and Linux desktop applications", "Local database with backup and restore",
      "Printing and PDF generation", "Packaged installers — no Python needed on site"]),
    (None, "Android & iOS Apps", "smartphone",
     "Mobile apps for Android and iPhone built on your platform, so every update you deploy reaches users' phones.",
     ["Android and iPhone apps with Capacitor", "Phone features: haptics, network awareness, files",
      "Offline and loading screens", "App icons, splash screens and store builds"]),
    (None, "Data Migration & Bulk Import", "cloud",
     "Moving existing spreadsheets and field-collected data into a working system without duplicates.",
     ["CSV and Excel import tools", "KoboToolbox and Agile MIS exports",
      "Matching and de-duplication", "Downloadable import templates"]),
    (None, "Technical Training & Project Mentoring", "users",
     "Hands-on coding training through Techmiary Institute of Technology, and mentoring for final-year software projects.",
     ["Coding training for kids, youths and professionals", "Final-year project supervision",
      "Requirements through to deployment", "Debugging and code review"]),
]

SKILLS = {
    # category -> [(name, note)]   notes say where the skill is used
    "Backend": [
        ("Python", "Every product on this site is written in it."),
        ("Django", "The framework behind Techmiary Cloud, WDA SMS, Borno Agile MIS and Diction Masters."),
        ("Django REST Framework", "REST APIs, including LiveQuiz's JWT-authenticated API."),
        ("Django Channels", "Real-time WebSocket quiz rooms in LiveQuiz."),
        ("REST APIs", "Designed for web and mobile clients."),
    ],
    "Frontend": [
        ("JavaScript", "Interactive dashboards and real-time quiz screens."),
        ("HTML5", ""),
        ("CSS3", ""),
        ("Bootstrap", "The UI base for the school and MIS platforms."),
    ],
    "Infrastructure": [
        ("Linux", "Ubuntu servers in production."),
        ("Nginx", "Reverse proxy and TLS in front of every deployment."),
        ("Gunicorn", "WSGI server for the Django platforms."),
        ("Daphne", "ASGI server for LiveQuiz."),
        ("Redis", "Channel layer for LiveQuiz."),
        ("Git", ""),
        ("GitHub", ""),
        ("Bash", ""),
    ],
    "Cloud & Storage": [
        ("PostgreSQL", "Primary database for the school ERPs and the MIS."),
        ("MySQL", ""),
        ("SQLite", "Diction Masters and this website."),
        ("Cloudflare R2", "Object storage for lesson media."),
    ],
    "Desktop & Mobile": [
        ("PySide6", "Qt desktop interfaces, as in School Result Manager."),
        ("PyInstaller", "Packaging desktop programs for Windows and Linux."),
        ("Capacitor", "The Android and iPhone apps for Diction Masters."),
    ],
    "Integrations": [
        ("Paystack", "Online fee payments in Techmiary Cloud and WDA SMS."),
        ("Termii", "Primary SMS provider for the school platforms."),
        ("Africa's Talking", "SMS fallback when the primary provider fails."),
        ("ReportLab", "PDF receipts and reports."),
        ("openpyxl", "Excel exports and imports."),
        ("KoboToolbox", "Importing field-collected data into Borno Agile MIS."),
    ],
}
SKILL_CATEGORY_RENAME = {"Cloud & Storage": "Data & Storage"}
SKILL_CATEGORY_DESCRIPTIONS = {
    "Backend": "Application logic, data modelling and server-side APIs.",
    "Frontend": "Server-rendered interfaces and responsive layouts.",
    "Infrastructure": "Running applications on Linux servers in production.",
    "Data & Storage": "Databases and object storage behind our systems.",
    "Integrations": "Payments, SMS, documents and data imports our systems depend on.",
    "Desktop & Mobile": "Offline desktop programs and Android and iOS apps.",
}

SOLUTIONS = {
    "school-erp-platform": {
        "name": "School ERP Platform",
        "tagline": "Every school on one platform, each with its own data.",
        "summary": "The multi-tenant ERP behind Techmiary Cloud: academics, CBT, results, finance, hostel and communication.",
        "overview": (
            "A hosted, multi-tenant school ERP. Each school gets its own "
            "users and data on a shared, maintained platform, with every "
            "module working from one student record."
        ),
        "who_its_for": "Schools and groups of schools that want a complete system without running their own servers.",
        "outcome": "Fees, results and parent communication all come from the same record, so termly work stops being a reconciliation exercise.",
        "related": "techmiary-cloud",
        "capabilities": [
            ("Multi-tenant isolation", "Each school's data and users are kept separate."),
            ("Finance and Paystack", "Fee structures, student wallets, online payments and receipts."),
            ("CBT and results", "Online exams, score entry and batch publishing."),
            ("Email and SMS", "Campaigns, reminders and automatic notifications."),
        ],
    },
    "learning-assessment-platform": {
        "name": "Learning & Assessment Platform",
        "tagline": "Lessons, tests and live quizzes learners actually use.",
        "summary": "Structured lessons with audio and video, computer-based tests and real-time quizzes.",
        "overview": (
            "The learning products we build: Diction Masters' pronunciation "
            "lessons, computer-based examinations in our school platforms, "
            "and LiveQuiz's real-time quiz rooms."
        ),
        "who_its_for": "Schools, academies and education programmes delivering lessons or assessments online.",
        "outcome": "Learners practise and are assessed in one place, and schools control who has access.",
        "related": "diction-masters",
        "capabilities": [
            ("Media-rich lessons", "Video, audio and practice content, managed from the admin."),
            ("Computer-based testing", "Online examinations with results."),
            ("Live quizzes", "Real-time rooms with a shared clock and live leaderboard."),
            ("Access codes", "Schools issue single-use codes to their learners."),
        ],
    },
    "school-management-system": {
        "name": "School Management System",
        "tagline": "A complete system for a single school.",
        "summary": "A dedicated deployment for one school, as with WDA SMS: academics, fees, hostel and parent portals.",
        "overview": (
            "A school management system deployed for one school, with its "
            "own server and configuration — suited to schools that want "
            "their system run separately from any shared platform."
        ),
        "who_its_for": "Individual schools, including those with boarding facilities.",
        "outcome": "Parents see their child's fees, results and announcements in one portal.",
        "related": "wda-sms",
        "capabilities": [
            ("Student wallets", "Parents fund a wallet; fees are paid from it."),
            ("Hostel management", "Beds, boarders, exeats, visitors and incidents."),
            ("Parent and student portals", "Each sees their own results, fees and announcements."),
            ("Payroll", "Staff salary processing."),
        ],
    },
    "offline-result-management": {
        "name": "Offline Result Management",
        "tagline": "Term results without the internet.",
        "summary": "Desktop software that registers students, takes CA and exam scores and prints result sheets on the school's own computers — as with School Result Manager.",
        "overview": (
            "A result system that installs on the school's computers and runs "
            "without an internet connection. Teachers enter scores, the "
            "program works out totals, grades, positions and averages, and the "
            "school prints or saves every result sheet as PDF."
        ),
        "who_its_for": "Primary and secondary schools that need dependable results where the internet is slow, costly or unavailable.",
        "outcome": "Results are computed and printed on time, on site, whether or not the network is up.",
        "related": "school-result-manager",
        "icon": "printer",
        "industries": ["education"],
        "capabilities": [
            ("Runs offline", "Everything stays on the school's computer."),
            ("Score entry", "CA and exam grid with instant totals and grades."),
            ("Positions and averages", "Ties share a place; cumulative averages across terms."),
            ("Print and PDF", "Per student, per class, or a class broadsheet."),
        ],
    },
    "management-information-system": {
        "name": "Management Information System",
        "tagline": "Many schools, one view.",
        "summary": "A multi-school MIS with bulk import from KoboToolbox and Agile MIS exports, as with Borno Agile MIS.",
        "overview": (
            "A management information system for administering many schools "
            "centrally — schools, students, cohorts, enrolments, payments and "
            "attendance — fed by data collected in the field."
        ),
        "who_its_for": "Programmes and organisations that oversee many schools and collect data in the field.",
        "outcome": "Field exports become clean school and student records, and re-importing an update does not create duplicates.",
        "related": "borno-agile-mis",
        "capabilities": [
            ("Bulk import", "CSV and Excel from KoboToolbox and Agile MIS."),
            ("No duplicates", "Existing records are matched and updated."),
            ("Enrolment approvals", "An approve-or-reject queue."),
            ("Reports", "Attendance, performance and revenue."),
        ],
    },
}

INDUSTRIES = {
    "education": {
        "name": "Education",
        "tagline": "Schools, academies and learning programmes.",
        "summary": "School ERPs, school management systems, CBT and learning platforms for primary and secondary schools and training institutions.",
        "overview": (
            "Most of our work is for education: the school platforms at "
            "techmiary.cloud and wdasms.cloud, Diction Masters for "
            "pronunciation, and the systems behind Techmiary Institute of "
            "Technology."
        ),
        "challenges": "Records split across spreadsheets and paper\nFees reconciled by hand\nParents hard to reach reliably",
    },
    "government-public-sector": {
        "name": "Programmes & Public Sector",
        "tagline": "Oversight across many schools and sites.",
        "summary": "Management information systems that administer many schools centrally and take in field-collected data.",
        "overview": (
            "Borno Agile MIS brings the administration of many schools into "
            "one platform and imports beneficiary records exported from "
            "KoboToolbox and Agile MIS."
        ),
        "challenges": "Data collected in the field on different forms\nDuplicates when exports are re-imported\nNo single view across schools",
    },
    "business-enterprise": {
        "name": "Business & Enterprise",
        "tagline": "Administrative workflows in one system.",
        "summary": "Business management platforms and custom web applications for organisations outside education.",
        "overview": (
            "Techmiary ERP and our custom web applications bring an "
            "organisation's administrative workflows into one "
            "database-driven system."
        ),
        "challenges": "Processes held in spreadsheets\nNo shared record across teams\nReporting assembled by hand",
    },
}

BLOG = [
    {
        "title": "Building a result manager that works without the internet",
        "category": "Architecture",
        "excerpt": "Why we built a school's result software as an offline desktop program, and the details that matter when every student needs a correct, printed sheet on time.",
        "content": (
            "Most of what we build lives on the web. But a school recently needed something different: term results produced on its own computers, on deadline, whether or not the internet was working. So we built School Result Manager as a desktop program that runs completely offline on Windows and Linux.\n\n"
            "The program is written in Python with PySide6, the Qt toolkit, and keeps everything in a single SQLite database file plus a folder of passport photos. There is no server to reach and nothing to sign up for. PyInstaller packages it into a folder that runs on a PC without Python installed, so installing it at the school is a matter of copying that folder across.\n\n"
            "Score entry is where teachers spend their time, so it had to be quick. CA 1, CA 2 and the exam go into a grid; the total and grade appear as they type, and Enter moves to the next student. Many teachers already keep scores in Excel, so a column copied from a spreadsheet can be pasted straight in. Each teacher sees only the subjects the admin has assigned to them.\n\n"
            "Positions are the detail parents read first, and they have to follow the convention schools use: students with the same score share a place, and the next place is skipped — 1st, 2nd, 2nd, 4th. The program ranks subject and class positions that way, and in the second and third terms each sheet also carries earlier term totals and a cumulative average.\n\n"
            "Printing is the whole point, so result sheets are laid out as HTML and sent through Qt's print system. The same path produces a PDF of a whole class, one A4 page per student, and a class broadsheet.\n\n"
            "Offline software has one risk the web does not: the data lives on one machine. Backup and restore sit in the File menu. Backups use SQLite's own backup mechanism rather than copying a file that may be in use, and a restore first checks that the chosen file really is a School Result Manager database before it replaces anything. Our advice to the school is simple — back up often, and keep the copies on a flash drive."
        ),
    },
    {
        "title": "One record per pupil: how our school platforms are structured",
        "category": "Architecture",
        "excerpt": "Why fees, results, hostel billing and parent messages in our school systems all hang off a single student record — and what that changes for a school.",
        "content": (
            "The first thing most schools tell us is that their information is correct — it is just in the wrong places. Admissions live in one spreadsheet, results in another, fees in a ledger and parent contact in a phone. Each is accurate on its own; none of them agree with each other.\n\n"
            "Our school platforms, Techmiary Cloud and WDA SMS, are built around a different rule: every module works from the same student record. Results are entered against it. Fees are billed against it. Hostel charges, exeats and incidents attach to it. When a parent receives an SMS, it is about that record.\n\n"
            "Fees are where this matters most. Each student has a wallet that parents fund, and fees are paid from it. Every credit and debit is recorded as a transaction against the wallet, so a balance can always be explained line by line.\n\n"
            "Payments are not applied the moment they are recorded. They move through an approval step — pending, then approved — so the accounts office confirms a payment before it changes what a parent owes. Approval updates the payment, the wallet and the ledger inside a single database transaction: it completes fully or not at all. Receipts are generated as PDFs, and the billing report shows every student's status at once.\n\n"
            "The same principle carries into communication. Because contact details, fees and results share a record, a fee reminder goes only to parents with an outstanding balance, and result notifications go out when results are published — without anyone building a mailing list by hand.\n\n"
            "None of this is exotic engineering. It is the decision to model the school once, correctly, and let every feature read from that model."
        ),
    },
    {
        "title": "Importing field data without creating duplicates",
        "category": "Django",
        "excerpt": "How Borno Agile MIS turns KoboToolbox and Agile MIS exports into school and student records — and why re-importing an updated export must not double them.",
        "content": (
            "Data for education programmes is often collected in the field with tools such as KoboToolbox, then exported as a spreadsheet. Borno Agile MIS has to turn those exports into usable records: schools, students and the enrolments that link them.\n\n"
            "The obvious import creates a row for every line in the file. That works exactly once. The moment an updated export arrives — a few new pupils, some corrected details — the same schools and students are created again, and every report built on them is wrong.\n\n"
            "So the import treats each file as a set of facts about records that may already exist. For every row it looks for the school first. Field forms spell the same school in different ways, so the match is case-insensitive, and a school already seen during the import is taken from an in-memory cache rather than queried again. Only when no match exists is a new school created, with an ID built from its LGA, such as AGILE/JERE/00001.\n\n"
            "Students are matched by email, in bulk: the import collects every email in the file and fetches the existing students in a single query instead of one query per row. A student created earlier in the same file is remembered too, so a duplicated line in the export does not create a second record. Existing records are updated; new ones are created; the result page reports how many of each, and how many rows were skipped.\n\n"
            "Exports also carry fields the MIS has no dedicated column for — identity numbers, cohort, caregiver details. Rather than discarding them, the import keeps them alongside the student record, so nothing collected in the field is lost.\n\n"
            "Finally, there is a downloadable template with every supported header. The cheapest import bug to fix is the one prevented by giving people the right file to fill in."
        ),
    },
    {
        "title": "Keeping every player on the same clock with Django Channels",
        "category": "Architecture",
        "excerpt": "LiveQuiz runs multiplayer quiz rooms in real time. The design choice that makes it fair: the server, not the browser, owns the timer.",
        "content": (
            "A quiz played together has one hard requirement: everyone sees the same question and the same time remaining. If each browser runs its own countdown, players drift apart within a few questions, and a leaderboard fetched by polling is always a step behind.\n\n"
            "LiveQuiz is built on Django Channels. Each quiz room is a WebSocket group, served by the Daphne ASGI server with Redis as the channel layer. When a host opens a room, the server draws the questions at random for the chosen education level, field of study, subject and topic, and holds the room's state: its questions, the scores so far and who has answered.\n\n"
            "The countdown runs on the server. Each tick, each new question, each score update and the final leaderboard are sent to the whole group at once with a group broadcast. Browsers display what they are told; none of them decides when time is up.\n\n"
            "The same state drives the rest of the room's behaviour. The number of questions and the time allowed come from the host's plan. Rooms lock after a short delay so players cannot join mid-quiz. Rooms can be grouped into a battle for team play.\n\n"
            "Work that does not belong in a request runs in the background: APScheduler sends subscription expiry reminders and clears out old guest submissions, so guests can play without accumulating data forever.\n\n"
            "The general lesson holds beyond quizzes: when several people must agree on what is happening right now, give one place the authority to say so, and push that to everyone."
        ),
    },
]

TEAM_FOUNDER = {
    "role": "Founder & Lead Software Engineer",
    "short_bio": "Python and Django engineer; builds and runs Techmiary's platforms end to end.",
    "bio": LONG_BIO,
    "email": PERSONAL_EMAIL,
    "github_url": GITHUB,
}

# The profile README lists these roles but gives no dates or employers for
# most of them. They are created hidden until the owner supplies dates.
EXPERIENCE_PENDING = [
    ("Techmiary Coding Academy", "Founder & Lead Software Engineer", True,
     ["Founded the academy and leads its software engineering work.",
      "Builds and maintains the platforms the academy runs on."]),
    ("Techmiary Technology Concepts", "Python/Django Web Application Developer", True,
     ["Developed and maintained around 10 client platforms and around 15 websites and web applications.",
      "School management systems, examination portals, registration systems and reporting dashboards.",
      "Supported more than 20 university students with final-year software projects."]),
    ("To be confirmed", "ICT Instructor & Computer Lab Administrator", False,
     ["Taught ICT and administered the computer laboratory."]),
    ("To be confirmed", "Computer Science & ICT Instructor", False,
     ["Taught computer science and ICT."]),
]

TEST_USERS = ("testadmin", "amina", "visitor-nostaff")


class Command(BaseCommand):
    help = "Replace sample content with real content sourced from the owner's projects."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true",
                            help="Report what would change, then roll back.")

    def handle(self, *args, **options):
        self.report = []
        with transaction.atomic():
            self.site_settings()
            self.social_links()
            self.projects()
            self.services()
            self.skills()
            self.solutions()
            self.industries()
            self.team()
            self.experience()
            self.remove_fabrications()
            self.blog()
            if options["dry_run"]:
                transaction.set_rollback(True)

        for line in self.report:
            self.stdout.write(line)
        verb = "Would apply" if options["dry_run"] else "Applied"
        self.stdout.write(self.style.SUCCESS(f"\n{verb} real content."))

    # -- helpers -----------------------------------------------------------
    def note(self, text):
        self.report.append(text)

    @staticmethod
    def fields_of(model):
        return {f.name for f in model._meta.get_fields() if hasattr(f, "attname")}

    def only(self, model, data):
        allowed = self.fields_of(model)
        return {k: v for k, v in data.items() if k in allowed}

    @staticmethod
    def delete_file(filefield):
        if filefield:
            try:
                filefield.delete(save=False)
            except Exception:
                pass

    # -- site settings ------------------------------------------------------
    def site_settings(self):
        from core.models import SiteSettings

        site = SiteSettings.load()
        if site is None:
            self.note("! no SiteSettings row — run seed_portfolio first")
            return

        cleared = []
        for field, placeholders in MY_PLACEHOLDERS.items():
            if getattr(site, field, None) in placeholders:
                setattr(site, field, None if field == "founded_year" else "")
                cleared.append(field)

        site.company_name = "Techmiary Technology Concepts"
        site.legal_name = "Techmiary Technology Concepts"
        site.short_bio = SHORT_BIO
        site.long_bio = LONG_BIO
        site.company_overview = COMPANY_OVERVIEW
        site.hero_subheadline = HERO_SUBHEADLINE
        site.website_url = "https://techmiary.tech"
        site.github_url = GITHUB
        site.whatsapp_url = WHATSAPP
        if not site.phone or site.phone.startswith("+234 800") or site.phone == "+234 802 111 2222":
            site.phone = PHONE
        if not site.email:
            site.email = BUSINESS_EMAIL
        if not site.sales_email:
            site.sales_email = BUSINESS_EMAIL
        if not site.support_email:
            site.support_email = BUSINESS_EMAIL
        site.save()
        self.note(f"site settings: identity and bios set; placeholders cleared: {', '.join(cleared) or 'none'}")

    def social_links(self):
        from core.models import SocialLink

        real = {"GitHub": (GITHUB, "github"), "WhatsApp": (WHATSAPP, "whatsapp"),
                "Company site": ("https://techmiary.tech", "link")}
        for link in SocialLink.objects.all():
            if link.name in real:
                link.url, link.icon = real[link.name]
                link.is_active = True
            elif "example" in link.url:
                link.is_active = False   # no real profile known
            link.save()
        for name, (url, icon) in real.items():
            SocialLink.objects.get_or_create(name=name, defaults={"url": url, "icon": icon})
        off = SocialLink.objects.filter(is_active=False).values_list("name", flat=True)
        self.note(f"social links: GitHub, WhatsApp, website live; hidden until a real URL is given: {', '.join(off) or 'none'}")

    # -- projects -----------------------------------------------------------
    def projects(self):
        from projects.models import (Project, ProjectCategory, ProjectChallenge,
                                     ProjectFeature, ProjectImage, Technology)

        order = 1
        for spec in PROJECTS:
            category, _ = ProjectCategory.objects.get_or_create(
                name=spec["category"], defaults={"display_order": 10 + order})
            project = Project.objects.filter(slug=spec["slug"]).first()
            created = project is None
            if created:
                project = Project(slug=spec["slug"], status=Project.STATUS_DEVELOPMENT,
                                  is_published=True)
            for field in ("title", "short_description", "description", "problem", "solution",
                          "result", "architecture_description", "website_url", "github_url", "year"):
                setattr(project, field, spec[field])
            project.category = category
            project.client = ""               # no consent recorded for any client
            project.display_order = order
            project.featured = order <= 5
            project.meta_title = ""
            project.meta_description = ""
            project.cover_image_alt = f"{spec['title']} interface"
            if spec["slug"] in LIVE_PER_PROFILE | LIVE_PER_OWNER:
                project.status = Project.STATUS_LIVE
            # Generated placeholder images are not screenshots of the product.
            for field in ("cover_image", "architecture_diagram"):
                f = getattr(project, field)
                if f and (spec["slug"] in f.name or "cover" in f.name or "arch" in f.name):
                    self.delete_file(f)
                    setattr(project, field, None)
            project.save()

            project.technologies.set([Technology.objects.get_or_create(name=t)[0]
                                      for t in spec["technologies"]])
            ProjectFeature.objects.filter(project=project).delete()
            ProjectFeature.objects.bulk_create([
                ProjectFeature(project=project, title=t, description=d, display_order=i)
                for i, (t, d) in enumerate(spec["features"], start=1)])
            ProjectChallenge.objects.filter(project=project).delete()
            ProjectChallenge.objects.bulk_create([
                ProjectChallenge(project=project, title=t, description=d, display_order=i)
                for i, (t, d) in enumerate(spec["challenges"], start=1)])
            for img in ProjectImage.objects.filter(project=project):
                self.delete_file(img.image)
                img.delete()
            self.note(f"project {'+' if created else '~'} {spec['title']}: "
                      f"{len(spec['features'])} features, status={project.get_status_display()}")
            order += 1

        stray = Project.objects.exclude(slug__in=[p["slug"] for p in PROJECTS])
        for p in stray:
            self.note(f"project ? left untouched (not in sources): {p.title}")

    # -- services -----------------------------------------------------------
    def services(self):
        from services.models import Service

        order = 1
        keep = []
        for old_title, title, icon, summary, deliverables in SERVICES:
            service = None
            if old_title:
                service = Service.objects.filter(title=old_title).first()
            if service is None:
                service = Service.objects.filter(title=title).first()
            if service is None:
                service = Service(title=title)
            service.title = title
            service.slug = slugify(title)
            service.icon = icon
            service.summary = summary
            service.description = ""
            service.deliverables = "\n".join(deliverables)
            service.display_order = order
            service.is_active = True
            service.is_featured = order <= 6
            service.save()
            keep.append(service.pk)
            order += 1
        self.note(f"services: {len(keep)} written from the profile's 'What I Build' list")

    # -- skills -------------------------------------------------------------
    def skills(self):
        from core.models import Skill, SkillCategory

        total = 0
        for i, (cat_name, items) in enumerate(SKILLS.items(), start=1):
            display = SKILL_CATEGORY_RENAME.get(cat_name, cat_name)
            category = (SkillCategory.objects.filter(name=cat_name).first()
                        or SkillCategory.objects.filter(name=display).first()
                        or SkillCategory(name=display))
            category.name = display
            category.slug = slugify(display)
            category.display_order = i
            category.description = SKILL_CATEGORY_DESCRIPTIONS.get(display, category.description)
            category.save()
            names = [n for n, _ in items]
            Skill.objects.filter(category=category).exclude(name__in=names).delete()
            for j, (name, note) in enumerate(items, start=1):
                Skill.objects.update_or_create(
                    category=category, name=name,
                    defaults={"description": note, "proficiency": "",
                              "display_order": j, "is_active": True})
                total += 1
        self.note(f"skills: {total} across {len(SKILLS)} categories, each tied to where it is used; proficiency levels cleared")

    # -- company ------------------------------------------------------------
    def solutions(self):
        from company.models import Solution, SolutionCapability
        from projects.models import Project

        for slug, spec in SOLUTIONS.items():
            sol = Solution.objects.filter(slug=slug).first()
            if sol is None:
                if "icon" not in spec:
                    self.note(f"! solution {slug} not found — skipped")
                    continue
                sol = Solution(slug=slug, is_active=True, is_featured=True,
                               display_order=Solution.objects.count() + 1)
            if "icon" in spec:
                sol.icon = spec["icon"]
            for field in ("name", "tagline", "summary", "overview", "who_its_for", "outcome"):
                if field in self.fields_of(Solution):
                    setattr(sol, field, spec[field])
            sol.related_project = Project.objects.filter(slug=spec["related"]).first()
            sol.meta_title = ""
            sol.meta_description = ""
            if sol.hero_image and "solution-" in sol.hero_image.name:
                self.delete_file(sol.hero_image)
                sol.hero_image = None
            sol.save()
            if spec.get("industries"):
                from company.models import Industry
                sol.industries.set(Industry.objects.filter(slug__in=spec["industries"]))
            SolutionCapability.objects.filter(solution=sol).delete()
            cap_fields = self.fields_of(SolutionCapability)
            for i, (title, desc) in enumerate(spec["capabilities"], start=1):
                SolutionCapability.objects.create(**self.only(SolutionCapability, {
                    "solution": sol, "title": title, "description": desc, "display_order": i}))
        self.note(f"solutions: {len(SOLUTIONS)} rewritten and linked to their projects")

    def industries(self):
        from company.models import Industry

        for slug, spec in INDUSTRIES.items():
            ind = Industry.objects.filter(slug=slug).first()
            if ind is None:
                continue
            for field, value in spec.items():
                setattr(ind, field, value)
            if ind.image and "industry-" in ind.image.name:
                self.delete_file(ind.image)
                ind.image = None
            ind.save()
        self.note(f"industries: {len(INDUSTRIES)} rewritten")

    def team(self):
        from company.models import TeamMember

        founder = TeamMember.objects.filter(is_founder=True).first()
        removed = 0
        for member in TeamMember.objects.exclude(pk=getattr(founder, "pk", None)):
            self.delete_file(member.photo)
            member.delete()
            removed += 1
        if founder:
            for field, value in TEAM_FOUNDER.items():
                setattr(founder, field, value)
            founder.linkedin_url = ""
            founder.twitter_url = ""
            if founder.photo and "team-" in founder.photo.name:
                self.delete_file(founder.photo)
                founder.photo = None
            founder.save()
        self.note(f"team: {removed} invented staff removed; founder profile written")

    def experience(self):
        from experience.models import Experience, Responsibility

        Experience.objects.filter(
            Q(organization__contains=MARKER) | Q(description__contains=MARKER)).delete()
        Experience.objects.filter(organization="Techmiary Technology Concepts",
                                  position="Founder & Software Engineer").delete()
        for i, (org, position, current, bullets) in enumerate(EXPERIENCE_PENDING, start=1):
            exp, _ = Experience.objects.update_or_create(
                organization=org, position=position,
                defaults={"start_date": date(2000, 1, 1), "end_date": None,
                          "is_current": current, "description": "",
                          "display_order": i,
                          # Hidden: the start date above is a stand-in, not a fact.
                          "is_active": False})
            Responsibility.objects.filter(experience=exp).delete()
            Responsibility.objects.bulk_create([
                Responsibility(experience=exp, text=t, display_order=j)
                for j, t in enumerate(bullets, start=1)])
        self.note(f"experience: {len(EXPERIENCE_PENDING)} roles from the profile, HIDDEN until dates are confirmed")

    # -- removals -----------------------------------------------------------
    def remove_fabrications(self):
        from blog.models import BlogPost
        from careers.models import JobApplication, JobOpening
        from company.models import Client, Milestone, Resource, Testimonial
        from contact.models import ContactMessage, NewsletterSubscriber, QuoteRequest
        from core.models import Partner
        from proposals.models import Proposal

        def purge(model, qs=None, files=()):
            qs = qs if qs is not None else model.objects.all()
            n = 0
            for obj in qs:
                for f in files:
                    self.delete_file(getattr(obj, f, None))
                obj.delete()
                n += 1
            return n

        tagged = lambda model, *fields: model.objects.filter(
            _any([Q(**{f"{f}__contains": MARKER}) for f in fields]))

        self.note(
            "removed (invented, or no consent on record): "
            f"{purge(Client, files=('logo',))} clients, "
            f"{purge(Testimonial, files=('author_photo',))} testimonials, "
            f"{purge(Partner, files=('logo',))} partners, "
            f"{purge(Milestone)} milestones, "
            f"{purge(Resource, files=('file', 'cover_image'))} resources, "
            f"{purge(JobApplication, files=('cv',))} job applications, "
            f"{purge(JobOpening)} job openings, "
            f"{purge(BlogPost, BlogPost.objects.filter(content__contains=MARKER), files=('featured_image',))} blog posts"
        )
        n_leads = (
            purge(ContactMessage, ContactMessage.objects.filter(
                Q(message__contains=MARKER) | Q(email__endswith="@example.com") | Q(email__endswith="@example.net")))
            + purge(QuoteRequest, QuoteRequest.objects.filter(
                Q(email__endswith="@example.com") | Q(organisation__icontains="sample")
                | Q(internal_notes__contains=MARKER)))
            + purge(NewsletterSubscriber, NewsletterSubscriber.objects.filter(
                Q(email__endswith="@example.com") | Q(email__startswith="conc-")))
        )
        n_props = purge(Proposal, Proposal.objects.filter(client_organisation__in=(
            "Bright Future Academy", "Al-Noor International School")))
        n_users = get_user_model().objects.filter(username__in=TEST_USERS).delete()[0]
        self.note(f"removed test data: {n_leads} sample enquiries/quotes/subscribers, "
                  f"{n_props} test proposals, test accounts ({n_users} rows incl. relations)")

    def blog(self):
        from blog.models import BlogCategory, BlogPost

        author = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
        now = timezone.now()
        for i, post in enumerate(BLOG):
            cat, _ = BlogCategory.objects.get_or_create(name=post["category"])
            BlogPost.objects.update_or_create(
                slug=slugify(post["title"])[:220],
                defaults={
                    "title": post["title"], "excerpt": post["excerpt"],
                    "content": post["content"], "category": cat, "author": author,
                    "published": True, "is_featured": i == 0,
                    "published_at": now - timedelta(days=7 * (i + 1)),
                    "meta_title": "", "meta_description": "",
                })
        self.note(f"blog: {len(BLOG)} articles about the real systems, each claim checked against the code")


def _any(qs):
    out = Q()
    for q in qs:
        out |= q
    return out
