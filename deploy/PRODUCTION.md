# Production runbook — Techmiary website

Ubuntu VPS, Nginx → Gunicorn → Django → SQLite. One machine, one database file,
no database server to run.

---

## Why SQLite is fine here, and where it stops being fine

This is a content site: a handful of editors, a few form submissions a day, and
everything else is reads. SQLite handles that comfortably and removes an entire
service from the stack.

Know the limits before you grow into them:

- **One machine.** SQLite has no network protocol, so a second app server cannot
  share the database. Scaling means a bigger box, not more of them.
- **Writes serialise.** WAL lets readers carry on during a write, but only one
  write happens at a time. Fine at this volume; wrong for a busy forum.
- **Backups are a file, not a dump.** Use `deploy/backup.sh`. Copying
  `db.sqlite3` with `cp` while the site runs can capture a torn state.

The settings that make this safe under Gunicorn — WAL, `busy_timeout`,
`synchronous=NORMAL`, `foreign_keys=ON`, `transaction_mode=IMMEDIATE` — live in
`config/settings/base.py`.

---

## Layout on the server

```
/srv/portfolio/              code checkout (git)
├── venv/                    virtualenv
├── .env                     secrets, 0640 root:www-data
├── staticfiles/             collectstatic output, served by Nginx
└── data/                    NOTHING here is in git
    ├── db.sqlite3           the database (+ -wal, -shm)
    ├── media/               uploads: logos, photos, CVs, resources
    ├── cache/               shared filesystem cache
    └── backups/             dated backups from backup.sh
```

Keeping `data/` outside the checkout is the point: a `git pull`, a re-clone, or
a botched deploy cannot take the database or the uploads with it.

---

## First install

### 1. System packages

```bash
sudo apt update
sudo apt install -y python3-venv python3-dev build-essential \
                    nginx certbot python3-certbot-nginx git curl sqlite3

# WeasyPrint renders the proposal PDFs. Without these it imports but cannot
# draw, and /admin/proposals/<id>/pdf/ returns 503 with a clear message.
sudo apt install -y libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b \
                    libffi-dev libjpeg-dev libopenjp2-7 fonts-dejavu-core
```

No PostgreSQL, and no `libpq-dev`. The `sqlite3` CLI is optional — the backup
script uses Python's own `sqlite3` module — but it is useful for poking around.

### 2. Application

```bash
sudo mkdir -p /srv/portfolio && sudo chown "$USER":www-data /srv/portfolio
git clone <your-repository-url> /srv/portfolio
cd /srv/portfolio

python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt
```

### 3. Data directory and permissions

```bash
sudo mkdir -p /srv/portfolio/data/{media,cache,backups}
sudo chown -R www-data:www-data /srv/portfolio/data
sudo chmod 750 /srv/portfolio/data
```

The **directory** must be writable by `www-data`, not just the database file.
SQLite creates `db.sqlite3-wal` and `db.sqlite3-shm` beside the database and
cannot open it read-write without being able to.

### 4. Environment

```bash
cp .env.example .env
nano .env                      # SECRET_KEY, ALLOWED_HOSTS, DATA_DIR, SMTP
sudo chown root:www-data .env
sudo chmod 640 .env
```

Set at minimum: `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS`,
`CSRF_TRUSTED_ORIGINS`, `SITE_URL`, `DATA_DIR=/srv/portfolio/data`,
`TRUSTED_PROXY_COUNT=1`.

Production **refuses to start** if `SECRET_KEY` is missing or still the
development placeholder, or if `ALLOWED_HOSTS` was never set. That is deliberate
— a site running on a default key is worse than a site that will not boot.

### 5. Database and static files

```bash
export DJANGO_SETTINGS_MODULE=config.settings.production
sudo -u www-data ./venv/bin/python manage.py migrate --noinput
sudo -u www-data ./venv/bin/python manage.py collectstatic --noinput
sudo -u www-data ./venv/bin/python manage.py createsuperuser
sudo -u www-data ./venv/bin/python manage.py seed_portfolio
```

Run these as `www-data`. If you run them as root, the database file ends up
owned by root and Gunicorn cannot write to it — the single most common cause of
"attempt to write a readonly database" on a first deploy.

Confirm WAL took effect:

```bash
sqlite3 /srv/portfolio/data/db.sqlite3 "PRAGMA journal_mode;"   # -> wal
```

### 6. Gunicorn

```bash
sudo cp deploy/gunicorn.socket  /etc/systemd/system/techmiary-portfolio.socket
sudo cp deploy/gunicorn.service /etc/systemd/system/techmiary-portfolio.service
sudo systemctl daemon-reload
sudo systemctl enable --now techmiary-portfolio.socket techmiary-portfolio.service
sudo systemctl status techmiary-portfolio
```

The unit runs under `ProtectSystem=strict`, so the filesystem is read-only
except the paths in `ReadWritePaths`. If you move `data/` or `staticfiles/`,
update that line or the service will fail to write.

### 7. DNS

Point the domain at the server **before** running Certbot — it proves control of
the name over HTTP, so the records have to resolve first.

At your registrar, for `techmiary.tech`:

| Type | Name | Value |
| --- | --- | --- |
| A | `@` | your server's IPv4 address |
| A | `www` | your server's IPv4 address |
| AAAA | `@` | your server's IPv6 address, if it has one |
| AAAA | `www` | same |

A `CNAME` on `www` pointing at the apex works too, but plain A records keep it
simple and avoid the flattening some registrars need for the apex.

Check they have propagated before continuing:

```bash
dig +short techmiary.tech
dig +short www.techmiary.tech
```

Both must return your server's address. Propagation is usually minutes, but the
TTL on any previous record can stretch it.

### 8. Nginx and TLS

The shipped config is already set for `techmiary.tech`: the apex serves the site and
`www` 301s to it, so every page has one canonical address.

```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/techmiary
sudo ln -s /etc/nginx/sites-available/techmiary /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

`nginx -t` will fail at this point because the certificate does not exist yet.
That is expected — Certbot writes it and reloads:

```bash
sudo certbot --nginx -d techmiary.tech -d www.techmiary.tech
sudo nginx -t && sudo systemctl reload nginx
sudo systemctl list-timers | grep certbot     # renewal is automatic
```

One certificate covers both names, which is why the www redirect block can use
the same `live/techmiary.tech/` paths.

### 9. Backups

```bash
sudo cp deploy/techmiary-backup.service /etc/systemd/system/
sudo cp deploy/techmiary-backup.timer   /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now techmiary-backup.timer
sudo systemctl start techmiary-backup.service     # prove it works now
ls -la /srv/portfolio/data/backups/
```

Daily at 02:30, keeping the newest 14 of each kind. **Copy them off the machine**
— a backup on the same disk is not a backup. `rclone`, `scp` from elsewhere, or
your provider's snapshots all work.

---

## Routine deploys

```bash
cd /srv/portfolio && ./deploy/deploy.sh
```

Backs up first, then pulls, installs pinned dependencies, migrates, collects
static, runs `check --deploy --fail-level WARNING`, restarts and waits for the
socket to answer. It exits non-zero and prints the last 40 journal lines if the
service does not come back.

---

## Restoring

```bash
ls -1t /srv/portfolio/data/backups/db-*.gz | head
sudo ./deploy/restore.sh /srv/portfolio/data/backups/db-20260927T023000Z.sqlite3.gz
```

It verifies the archive with `PRAGMA integrity_check` before touching anything,
stops the service, moves the current database aside rather than deleting it, and
re-runs migrations in case the backup predates them. Media restores separately:

```bash
tar -xzf /srv/portfolio/data/backups/media-20260927T023000Z.tar.gz -C /srv/portfolio/data
```

---

## Post-deploy checks

```bash
sudo -u www-data DJANGO_SETTINGS_MODULE=config.settings.production \
    ./venv/bin/python manage.py check --deploy
sudo systemctl status techmiary-portfolio nginx
sudo journalctl -u techmiary-portfolio -n 50 --no-pager
```

Then in a browser at `https://techmiary.tech`: every nav item loads, `/sitemap.xml`
and `/robots.txt` respond, the contact form stores a message, the dashboard
login works, a proposal renders as a PDF, the admin is reachable at your
`ADMIN_URL`, and a deliberately bad URL shows the branded 404.

Check the redirects resolve the way they should:

```bash
curl -sI http://techmiary.tech        | head -2   # 301 -> https://techmiary.tech
curl -sI https://www.techmiary.tech   | head -2   # 301 -> https://techmiary.tech
curl -sI https://techmiary.tech       | head -2   # 200
```

And confirm the canonical tag agrees with `SITE_URL`:

```bash
curl -s https://techmiary.tech/about/ | grep canonical
```

---

## Operational notes

**Uploaded CVs are public files.** Careers applications land in
`data/media/careers/applications/` and are served by Nginx at a guessable URL.
That is personal data on an unauthenticated path. `deploy/nginx.conf` has a
commented `location /media/careers/ { deny all; }` that closes it — note the
admin's download link goes through the same path, so staff would then read them
off the server instead. Closing it properly means serving those files through a
permission-checked view, which is an application change, not a config one.

**Sessions are signed cookies.** Ordinary requests stay read-only, which is what
SQLite is good at. The trade-off: a session cannot be revoked server-side.
Changing a user's password still invalidates their session. Set
`SESSION_ENGINE=django.contrib.sessions.backends.db` if you need revocation.

**The cache holds the rate-limit counters.** It defaults to a filesystem cache
under `DATA_DIR` so all workers share it. Do not switch it to `LocMemCache` in
production or the real limit becomes `CONTACT_RATE_LIMIT × workers`.

**"database is locked".** Means a write waited longer than
`SQLITE_BUSY_TIMEOUT_MS`. Raise it, or lower `--workers` in the service file.
Piling on workers makes this worse, not better.

**Don't run `seed_testdata` here.** It writes fabricated clients, testimonials,
vacancies and applications tagged `[sample]`. It is for local work only.

**Log rotation.** Gunicorn logs to stdout, which systemd rotates as part of the
journal. Nginx logs rotate through the packaged logrotate config. Nothing extra
to configure unless you set `LOG_FILE`.

---

## The domain in the site's own content

Two things carry the domain and are **not** configuration:

- `SITE_URL` in `.env` drives canonical links, Open Graph tags and the sitemap.
  It is set to `https://techmiary.tech`.
- **Site Settings → Website URL** in the Django admin is content. The seeded
  value is `https://techmiary.cloud`, which is what the footer and the
  Organization schema show. Change it there if `techmiary.tech` is now the company's
  address.
