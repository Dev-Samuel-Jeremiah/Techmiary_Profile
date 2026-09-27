"""
Base settings shared by every environment.

Environment-specific modules (development.py / production.py) import from here.
Nothing secret is hard-coded: every sensitive value is read from the
environment via python-decouple.
"""
from pathlib import Path

from decouple import Csv, config
from django.core.exceptions import ImproperlyConfigured

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
# Everything the application writes — database, uploads, cache, backups —
# lives under DATA_DIR. Pointing it outside the checkout means a deploy that
# replaces the code directory can never take the data with it.
DATA_DIR = Path(config("DATA_DIR", default=str(BASE_DIR)))

SECRET_KEY = config("SECRET_KEY", default="django-insecure-change-me-in-your-env-file")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="127.0.0.1,localhost", cast=Csv())
CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", default="", cast=Csv())

# Canonical origin used for absolute URLs (SEO metadata, sitemap, OG tags).
SITE_URL = config("SITE_URL", default="http://127.0.0.1:8000").rstrip("/")
SITE_ID = 1

# The admin lives behind a configurable path so it is not at a guessable default.
ADMIN_URL = config("ADMIN_URL", default="admin/")

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
# Staff sign in at the dashboard, not the Django admin, so an expired session
# returns them to the screen they were already using.
LOGIN_URL = "dashboard:login"
LOGIN_REDIRECT_URL = "dashboard:home"
LOGOUT_REDIRECT_URL = "dashboard:login"

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.humanize",
    "django.contrib.sitemaps",
    "django.contrib.staticfiles",
]

LOCAL_APPS = [
    "core.apps.CoreConfig",
    "company.apps.CompanyConfig",
    "projects.apps.ProjectsConfig",
    "careers.apps.CareersConfig",
    "experience.apps.ExperienceConfig",
    "services.apps.ServicesConfig",
    "blog.apps.BlogConfig",
    "contact.apps.ContactConfig",
    "proposals.apps.ProposalsConfig",
    "dashboard.apps.DashboardConfig",
]

INSTALLED_APPS = DJANGO_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.SecurityHeadersMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                # Makes site settings, navigation and social links available
                # to every template without repeating queries in each view.
                "core.context_processors.site_context",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
# PostgreSQL in every real environment. DATABASE_URL keeps credentials out of
# the codebase, e.g.
#   postgres://portfolio:password@127.0.0.1:5432/portfolio
DATABASE_URL = config("DATABASE_URL", default="")

# SQLite needs deliberate configuration to be safe under a multi-worker app
# server. These are applied to every connection:
#
#   journal_mode=WAL   readers are not blocked by a writer, which is what
#                      makes SQLite viable behind Gunicorn at all
#   busy_timeout       wait for a held write lock instead of raising
#                      "database is locked" immediately
#   synchronous=NORMAL safe in WAL mode and far faster than FULL; a crash can
#                      lose the last transaction, not the database
#   foreign_keys=ON    Django assumes them; SQLite does not enable them itself
#
# transaction_mode="IMMEDIATE" takes the write lock when a write transaction
# opens rather than upgrading mid-transaction, which is the usual source of
# lock errors under concurrency.
SQLITE_PRAGMAS = (
    "PRAGMA journal_mode=WAL;"
    "PRAGMA synchronous=NORMAL;"
    "PRAGMA busy_timeout=%d;"
    "PRAGMA foreign_keys=ON;"
    "PRAGMA temp_store=MEMORY;"
    "PRAGMA cache_size=-64000;"
) % config("SQLITE_BUSY_TIMEOUT_MS", default=10000, cast=int)


def _conn_max_age():
    """CONN_MAX_AGE as Django wants it: an int, or None for a persistent connection."""
    raw = str(config("CONN_MAX_AGE", default="none")).strip().lower()
    if raw in ("", "none", "null", "persistent"):
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _sqlite_config(path):
    return {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(path),
        "OPTIONS": {
            "init_command": SQLITE_PRAGMAS,
            "transaction_mode": "IMMEDIATE",
        },
        # A SQLite connection is a file handle, not a network socket, so it is
        # held for the life of the worker rather than reopened per request.
        # "none" means persistent; decouple casts the default too, so this is
        # read as text and converted here.
        "CONN_MAX_AGE": _conn_max_age(),
    }


def _database_from_url(url):
    """
    Parse a sqlite:// DATABASE_URL.

    ``sqlite:////srv/portfolio/data/db.sqlite3`` (four slashes) is an absolute
    path; ``sqlite:///db.sqlite3`` (three) is relative to DATA_DIR. Anything
    that is not SQLite is rejected loudly rather than silently ignored — this
    project has no other driver installed, so a postgres:// URL would fail much
    later and much less clearly.
    """
    from urllib.parse import urlparse

    parsed = urlparse(url)
    if not parsed.scheme.startswith("sqlite"):
        raise ImproperlyConfigured(
            "This project runs on SQLite. DATABASE_URL must start with "
            f"'sqlite://' — got {parsed.scheme or 'no scheme'!r}. "
            "Use SQLITE_PATH for a plain filesystem path."
        )
    raw = (parsed.path or "").strip()
    if not raw or raw == "/":
        raise ImproperlyConfigured("DATABASE_URL has no database path.")
    if raw.startswith("//"):
        # Four slashes after the scheme: an absolute path. Collapse the run of
        # leading slashes to one, because POSIX gives a leading "//" its own
        # implementation-defined meaning and Path keeps it verbatim.
        path = Path("/" + raw.lstrip("/"))
    else:
        # Three slashes: relative to DATA_DIR.
        path = DATA_DIR / raw.lstrip("/")
    return _sqlite_config(path)


if DATABASE_URL:
    DATABASES = {"default": _database_from_url(DATABASE_URL)}
else:
    # SQLite by default. SQLITE_PATH lets the file live outside the code
    # directory in production, so a deploy that replaces the checkout cannot
    # take the database with it.
    DATABASES = {
        "default": _sqlite_config(
            config("SQLITE_PATH", default=str(DATA_DIR / "db.sqlite3"))
        )
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = config("TIME_ZONE", default="Africa/Lagos")
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static & media
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = Path(config("STATIC_ROOT", default=str(BASE_DIR / "staticfiles")))

MEDIA_URL = "media/"
# Uploads belong with the database, not in the code directory: they are user
# data, they are not in version control, and they have to survive a re-clone.
MEDIA_ROOT = Path(config("MEDIA_ROOT", default=str(DATA_DIR / "media")))

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Uploaded images are capped so a stray upload cannot exhaust the disk.
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

# ---------------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "portfolio-default",
    }
}
# Seconds the cached site-settings/navigation fragments are kept.
SITE_CONTEXT_CACHE_SECONDS = config("SITE_CONTEXT_CACHE_SECONDS", default=300, cast=int)

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
EMAIL_BACKEND = config(
    "EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = config("EMAIL_HOST", default="")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="no-reply@localhost")
CONTACT_NOTIFICATION_EMAIL = config("CONTACT_NOTIFICATION_EMAIL", default="")

# ---------------------------------------------------------------------------
# Application settings
# ---------------------------------------------------------------------------
# How many reverse proxies sit in front of the app. Each one appends to
# X-Forwarded-For, so this is the number of right-hand entries that can be
# trusted; everything further left was supplied by the caller. 0 ignores the
# header and uses REMOTE_ADDR. The shipped nginx config is one hop, so a
# deployment behind it should set TRUSTED_PROXY_COUNT=1 — otherwise every
# visitor shares nginx's own address and therefore one rate-limit bucket.
TRUSTED_PROXY_COUNT = config("TRUSTED_PROXY_COUNT", default=0, cast=int)

# Contact form throttling: max submissions per IP inside the window.
CONTACT_RATE_LIMIT = config("CONTACT_RATE_LIMIT", default=5, cast=int)
CONTACT_RATE_WINDOW_SECONDS = config(
    "CONTACT_RATE_WINDOW_SECONDS", default=3600, cast=int
)

BLOG_PAGE_SIZE = config("BLOG_PAGE_SIZE", default=6, cast=int)
PROJECT_PAGE_SIZE = config("PROJECT_PAGE_SIZE", default=9, cast=int)

# ---------------------------------------------------------------------------
# Security defaults (tightened further in production.py)
# ---------------------------------------------------------------------------
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "[{asctime}] {levelname} {name}: {message}", "style": "{"}
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "root": {"handlers": ["console"], "level": config("LOG_LEVEL", default="INFO")},
}

# Under systemd the console handler already lands in the journal, which is
# rotated for you. Set LOG_FILE only if you want a separate file as well —
# for example to ship it somewhere, or on a host without journald.
LOG_FILE = config("LOG_FILE", default="")
if LOG_FILE:
    LOGGING["handlers"]["file"] = {
        "class": "logging.handlers.RotatingFileHandler",
        "filename": LOG_FILE,
        "maxBytes": config("LOG_MAX_BYTES", default=5 * 1024 * 1024, cast=int),
        "backupCount": config("LOG_BACKUP_COUNT", default=5, cast=int),
        "formatter": "verbose",
    }
    LOGGING["root"]["handlers"].append("file")
