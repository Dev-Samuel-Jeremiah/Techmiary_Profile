# Techmiary Technology Concepts — Company Website

The corporate website for **Techmiary Technology Concepts**, a software engineering and
product company founded by **Samuel Jeremiah**. It presents the company's solutions,
industries, services, case studies, leadership, careers and insights, and captures
enquiries, quote requests, job applications and newsletter signups.

Every piece of content — company profile, solutions, industries, team, clients,
testimonials, resources, FAQs, job openings, services, case studies and SEO metadata —
lives in the database and is edited through the Django admin. No claim about the company
is hard-coded in a template.

---

## Features

**Company**

- Homepage: hero, client wall, solutions, industries, services, delivery process, case
  studies, testimonials, leadership, careers and insights
- About: company overview, mission and vision, values, delivery lifecycle, milestone
  timeline, leadership and clients
- Solutions catalogue with a detail page per solution (overview, who it is for,
  capabilities, outcome, linked case study)
- Industries with sector-specific challenges and the solutions deployed there
- Leadership and team directory with an individual page per person; the founder's page
  also renders their career history
- Clients and testimonials, each with a consent flag recorded in the admin
- Technology page: the stack, a reference architecture and engineering practices
- Case studies (Our Work) with problem, solution, features, challenges, architecture,
  gallery and result

**Commercial**

- Three-step **Request a Quote** form — solution/service, project description, budget
  range, timeline, existing system, contact details — stored and triaged in the admin
- Contact form with validation, honeypot, per-IP rate limiting and optional email alerts
- **Newsletter** signup in the footer, on Insights and on Resources, with CSV export and
  unsubscribe handling in the admin

**Careers**

- Departments, job openings with draft/open/closed states and closing dates
- Application form with CV upload (type and size validated), consent checkbox and honeypot
- Applications tracked in the admin with status actions and a direct CV download link

**Resources & support**

- Downloadable guides and documents by category, with a graceful "available on request"
  state
- Searchable FAQ grouped by category, rendered as native `<details>` accordions
- Insights blog with drafts, scheduled publishing, categories, featured posts, search and
  pagination

**Engineering**

- Split settings (`base` / `development` / `production`) driven by `python-decouple`
- SQLite in WAL mode, `select_related` / `prefetch_related`, database indexes, cached site-wide
  navigation with signal-based invalidation
- WhiteNoise with compressed, hashed static files; lazy-loaded images
- Custom `Content-Security-Policy` and `Permissions-Policy` middleware on top of Django's
  own security settings
- Per-page `<title>`, meta description, canonical URL, Open Graph and X cards, plus
  JSON-LD for `Organization`, `Person`, `Product`, `JobPosting`, `FAQPage`, `BlogPosting`
  and `BreadcrumbList`
- `sitemap.xml` across eight sitemaps, `robots.txt`, and branded 403/404/500 pages
- Accessible markup: semantic landmarks, skip link, visible focus states, labelled
  controls, alt text, keyboard-operable menus and `prefers-reduced-motion` support
- 165 tests covering models, views, forms, uploads, SEO, security headers and the seeder

---

## Design

Light corporate palette: white and soft blue-grey surfaces, deep navy (`#0a2540`) text,
a royal blue primary (`#1b4dff`) and a teal accent (`#00b8a9`). Headings are set in Plus
Jakarta Sans, body copy in Inter, and code in JetBrains Mono.

The custom layer in `static/css/main.css` sits on top of Bootstrap's grid and a handful
of utilities; this is not a Bootstrap theme. `static/js/main.js` is progressive
enhancement only — the mega menu, mobile drawer and scroll reveal all degrade to a fully
usable page with JavaScript disabled.

---

## Stack

| Layer | Technology |
| --- | --- |
| Language | Python 3.11+ |
| Framework | Django 5.2 |
| Database | SQLite (WAL, `IMMEDIATE` transactions) — same engine in development and production |
| Frontend | Django templates, Bootstrap 5 grid, custom CSS layer, vanilla JavaScript |
| Static files | WhiteNoise (compressed manifest storage) |
| App server | Gunicorn |
| Web server | Nginx |
| Config | python-decouple + `.env` |
| Images | Pillow |

---

## Project structure

```
techmiary/
├── manage.py
├── config/
│   ├── settings/{base,development,production}.py
│   ├── sitemaps.py   urls.py   wsgi.py   asgi.py
│
├── core/        # SiteSettings, SocialLink, Partner, Skills, home/about/technology,
│                # SEO helpers, security middleware, seed_portfolio command
├── company/     # Solution, Industry, TeamMember, Client, Testimonial, Resource,
│                # FAQ, CompanyValue, Milestone
├── careers/     # Department, JobOpening, JobApplication
├── projects/    # Case studies: Project, Category, Technology, features, gallery
├── services/    # Service
├── blog/        # BlogCategory, BlogPost
├── contact/     # ContactMessage, QuoteRequest, NewsletterSubscriber
├── experience/  # Career history shown on the founder's team page
│
├── templates/
│   ├── base.html  home.html  about.html  technology.html  privacy.html  terms.html
│   ├── components/   # topbar, navbar, footer, cards, page banner, CTA, empty states
│   ├── company/      # solutions, industries, team, clients, resources, FAQ
│   ├── careers/      # job list and detail with the application form
│   ├── contact/      # contact and quote
│   ├── projects/  blog/  services/  experience/  errors/
│
├── static/{css,js,images}/
├── media/            # uploads (git-ignored)
├── deploy/           # PRODUCTION.md runbook, systemd units, nginx.conf,
│                    # deploy.sh, backup.sh, restore.sh, backup timer
├── requirements.txt   .env.example   .gitignore
```

---

## URL map

| Path | Page |
| --- | --- |
| `/` | Homepage |
| `/about/` | About the company |
| `/solutions/`, `/solutions/<slug>/` | Solutions catalogue and detail |
| `/industries/`, `/industries/<slug>/` | Industries and sector detail |
| `/services/` | Services and engagement models |
| `/projects/`, `/projects/<slug>/` | Case studies |
| `/team/`, `/team/<slug>/` | Leadership, team and profiles |
| `/clients/` | Clients and testimonials |
| `/careers/`, `/careers/<slug>/`, `/careers/<slug>/apply/` | Careers |
| `/technology/` | Technology stack (`/skills/` redirects here) |
| `/blog/`, `/blog/<slug>/` | Insights |
| `/resources/` | Guides and downloads |
| `/faq/` | Frequently asked questions |
| `/contact/` | Contact form |
| `/quote/` | Request a quote |
| `/newsletter/subscribe/` | Newsletter signup (POST) |
| `/privacy/`, `/terms/` | Legal |
| `/sitemap.xml`, `/robots.txt` | SEO |

---

## Local development

```bash
git clone <your-repository-url> techmiary
cd techmiary

python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env              # then edit it
python manage.py migrate
python manage.py seed_portfolio
python manage.py createsuperuser
python manage.py runserver
```

The site is then at <http://127.0.0.1:8000/> and the admin at
<http://127.0.0.1:8000/admin/>.

`manage.py` defaults to `config.settings.development`; `wsgi.py` defaults to
`config.settings.production`.

Generate a secret key with:

```bash
python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
```

---

## Environment variables

`.env.example` is the authoritative list. The important ones:

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY` | Django signing key. Required in production. |
| `DEBUG` | `False` everywhere except your own machine. |
| `ALLOWED_HOSTS` | Comma-separated hostnames. |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated `https://` origins. |
| `SITE_URL` | Canonical origin for canonical links, OG tags and the sitemap. |
| `ADMIN_URL` | Path the admin is mounted at, e.g. `control-panel/`. |
| `DATA_DIR` | Where the database, uploads, cache and backups live. Keep it outside the checkout. |
| `SQLITE_PATH` | Database file. Defaults to `$DATA_DIR/db.sqlite3`. |
| `DATABASE_URL` | Optional `sqlite:////absolute/path.sqlite3`. Anything non-SQLite is rejected at startup. |
| `EMAIL_*`, `DEFAULT_FROM_EMAIL` | SMTP settings for outgoing mail. |
| `CONTACT_NOTIFICATION_EMAIL` | Where contact and quote alerts are sent. |
| `CONTACT_RATE_LIMIT`, `CONTACT_RATE_WINDOW_SECONDS` | Form throttling. |
| `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS` | HTTPS hardening. |

**`.env` is git-ignored and must never be committed**, along with API keys, passwords,
private keys and database credentials.

---

## Database

SQLite, in both development and production — one file, no server to run, and the
same engine in every environment so nothing only breaks under load.

Three settings make it safe behind Gunicorn, applied to every connection in
`config/settings/base.py`:

| Setting | Why |
| --- | --- |
| `journal_mode=WAL` | Readers are not blocked by a writer. Without this, SQLite behind a multi-worker app server is not viable. |
| `transaction_mode=IMMEDIATE` | Django takes the write lock when a write transaction opens instead of upgrading mid-transaction — the usual source of lock errors. |
| `busy_timeout` | A worker waits for a held lock rather than failing immediately. |

Plus `synchronous=NORMAL` (safe in WAL, far faster than FULL) and
`foreign_keys=ON`, which Django assumes and SQLite does not enable by default.

```bash
python manage.py migrate
```

In production, point `DATA_DIR` at a directory outside the code checkout so a
deploy can never take the data with it. The **directory** has to be writable by
the app user, not just the file: SQLite creates `db.sqlite3-wal` and
`db.sqlite3-shm` alongside the database.

**Backups.** `cp` is not a backup — in WAL mode recent transactions live in the
sidecar file and a copy can be torn. `deploy/backup.sh` uses SQLite's own backup
API, verifies the result with `PRAGMA integrity_check`, gzips it, archives the
uploads alongside it and prunes old sets. `deploy/techmiary-backup.timer` runs it
daily. `deploy/restore.sh` puts one back.

**When to outgrow it.** One machine only, and writes serialise. That suits a
content site with a few editors. A busy write workload wants PostgreSQL; the
only code that assumes SQLite is the database block in `base.py`.

## Static files

```bash
python manage.py collectstatic --noinput
```

Assets live in `static/` and are collected into `staticfiles/`, where WhiteNoise serves
them with hashed filenames and long cache headers. Uploads (logos, team photos, solution
images, CVs, resources) go to `media/` and are served by Nginx in production.

---

## Content setup

`python manage.py seed_portfolio` creates the starting content: site profile, four
solutions linked to their case studies, three industries, company values, the founder's
team record, departments, resource categories, FAQs, skills, services and the four
projects. It is idempotent — run it as often as you like.

**It deliberately invents nothing.** No client, testimonial, vacancy, downloadable
resource, milestone, statistic or "live" project status is created. Those are yours to
add once they are real. After seeding, open the admin and:

1. **Site settings** — address, phone, sales and support email, office hours, founding
   year and registration number; upload the logo, favicon and a 1200×630 social image.
2. **Projects** — set each project's real status and write the Problem, Solution and
   Result sections. Add the Borno Agile MIS description once its details are confirmed.
3. **Solutions** — upload a hero image for each and finish the Management Information
   System write-up.
4. **Team** — add photos and the rest of your colleagues.
5. **Clients & testimonials** — add only organisations and quotes you have permission to
   publish. The consent checkbox records that permission.
6. **Careers** — create job openings; none are seeded, so the page shows its empty state
   until you publish one.
7. **Resources** — upload guides against the seeded categories.
8. **Milestones** — add the company's real dates under Company → Milestones.
9. **Social links** — only platforms with a real profile URL.
10. **Skills** — enable the Integrations entries that genuinely apply.

---

## Testing

```bash
python manage.py test
python manage.py test company careers contact     # a subset
python manage.py check
python manage.py check --deploy --settings=config.settings.production
```

The suite covers every public URL, model behaviour and slug generation, published versus
unpublished filtering, quote and application validation, CV upload rules, CSRF, rate
limiting, newsletter re-subscription and open-redirect refusal, SEO metadata and JSON-LD,
security headers, the sitemap, 404 handling, admin registration, template hygiene and the
seeder's idempotency and credibility guarantees.

---

## Production deployment (Ubuntu VPS)

**`deploy/PRODUCTION.md` is the runbook** — full first-install steps, the server
layout, permissions, backups, restores and the operational notes. The short
version:

```bash
# System packages (no PostgreSQL; the PDF renderer needs the pango libraries)
sudo apt update
sudo apt install -y python3-venv python3-dev build-essential \
                    nginx certbot python3-certbot-nginx git curl sqlite3 \
                    libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b \
                    libffi-dev libjpeg-dev libopenjp2-7 fonts-dejavu-core

# Code
sudo mkdir -p /srv/portfolio && sudo chown "$USER":www-data /srv/portfolio
git clone <your-repository-url> /srv/portfolio
cd /srv/portfolio
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt

# Data directory — outside the checkout, owned by the app user
sudo mkdir -p /srv/portfolio/data/{media,cache,backups}
sudo chown -R www-data:www-data /srv/portfolio/data
sudo chmod 750 /srv/portfolio/data

# Secrets
cp .env.example .env && nano .env        # SECRET_KEY, ALLOWED_HOSTS, DATA_DIR
sudo chown root:www-data .env && sudo chmod 640 .env

# Database and static files — as www-data, not root
export DJANGO_SETTINGS_MODULE=config.settings.production
sudo -u www-data ./venv/bin/python manage.py migrate --noinput
sudo -u www-data ./venv/bin/python manage.py collectstatic --noinput
sudo -u www-data ./venv/bin/python manage.py createsuperuser
sudo -u www-data ./venv/bin/python manage.py seed_portfolio
```

Running `migrate` as root leaves the database owned by root, and Gunicorn then
fails with "attempt to write a readonly database". It is the most common
first-deploy mistake with SQLite.

Then the services:

```bash
sudo cp deploy/gunicorn.socket  /etc/systemd/system/techmiary-portfolio.socket
sudo cp deploy/gunicorn.service /etc/systemd/system/techmiary-portfolio.service
sudo cp deploy/techmiary-backup.service /etc/systemd/system/
sudo cp deploy/techmiary-backup.timer   /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now techmiary-portfolio.socket techmiary-portfolio.service
sudo systemctl enable --now techmiary-backup.timer
```

Nginx and TLS. The config is already set for `techmiary.tech` — the apex serves the
site and `www` redirects to it. Point both A records at the server first, or
Certbot cannot verify the domain:

```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/techmiary
sudo ln -s /etc/nginx/sites-available/techmiary /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo certbot --nginx -d techmiary.tech -d www.techmiary.tech
sudo nginx -t && sudo systemctl reload nginx
```

Ongoing deploys:

```bash
cd /srv/portfolio && ./deploy/deploy.sh
```

Backs up, pulls, installs pinned dependencies, migrates, collects static, runs
`check --deploy --fail-level WARNING`, restarts, and waits for the socket to
answer before reporting success.

### Post-deploy checklist

```bash
sudo -u www-data DJANGO_SETTINGS_MODULE=config.settings.production \
    ./venv/bin/python manage.py check --deploy
sqlite3 /srv/portfolio/data/db.sqlite3 "PRAGMA journal_mode;"   # -> wal
sudo systemctl status techmiary-portfolio nginx
```

Then confirm in a browser that every nav item loads, the sitemap and
`robots.txt` respond, the contact form stores a message, the dashboard login
works, a proposal renders as a PDF, the admin is reachable at your `ADMIN_URL`,
and a bad URL shows the branded 404.

---

## Licence

Copyright © Techmiary Technology Concepts. All rights reserved.
