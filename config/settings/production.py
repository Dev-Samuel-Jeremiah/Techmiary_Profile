"""
Production settings for an Ubuntu VPS behind Nginx, on SQLite.

SQLite is a deliberate choice here: this is a content site with a small
number of editors, so reads dominate and writes are rare. The trade-offs to
know about:

  * One machine only. There is no network protocol, so the database cannot be
    shared with a second app server. Scaling means a bigger box, not more of
    them.
  * Writes serialise. WAL lets readers continue during a write, but only one
    write happens at a time. Fine at this volume; not fine for a busy forum.
  * Backups are a file, not a dump. Use deploy/backup.sh, which uses SQLite's
    own backup API — copying the file while the app is running can capture a
    torn state.

The pragmas that make this safe under Gunicorn live in base.py.
"""
from .base import *  # noqa: F401,F403
from .base import BASE_DIR, DATA_DIR, config

DEBUG = False

# HTTPS / transport security
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=31536000, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Cookies
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # the admin and forms read it from JS-free templates
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# Misc hardening
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

def _parse_admins(raw):
    """"Name|email,Name|email" -> [(name, email), ...]"""
    admins = []
    for pair in raw.split(","):
        pair = pair.strip()
        if "|" in pair:
            name, email = pair.split("|", 1)
            admins.append((name.strip(), email.strip()))
    return admins


ADMINS = _parse_admins(config("DJANGO_ADMINS", default=""))
MANAGERS = ADMINS

# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------
# A local-memory cache is per-process. Behind Gunicorn that means every worker
# keeps its own copy, which quietly breaks two things:
#
#   * the contact and quote rate limits count per worker, so the real ceiling
#     is CONTACT_RATE_LIMIT x number of workers
#   * a navigation change cleared from one worker's cache is still served by
#     the others until their own entries expire
#
# A filesystem cache is shared by every worker on the box and needs nothing
# installed. Point CACHE_BACKEND at Redis instead if you ever add one.
CACHES = {
    "default": {
        "BACKEND": config(
            "CACHE_BACKEND",
            default="django.core.cache.backends.filebased.FileBasedCache",
        ),
        "LOCATION": config("CACHE_LOCATION", default=str(DATA_DIR / "cache")),
        "TIMEOUT": config("CACHE_TIMEOUT", default=300, cast=int),
        "OPTIONS": {"MAX_ENTRIES": config("CACHE_MAX_ENTRIES", default=2000, cast=int)},
    }
}


# ---------------------------------------------------------------------------
# SQLite in production
# ---------------------------------------------------------------------------
# The database file is kept outside the code directory so a deploy that
# replaces the checkout cannot take the data with it, and so Nginx has no path
# that could serve it. The *directory* must be writable by the app user:
# SQLite writes db.sqlite3-wal and db.sqlite3-shm alongside the database, and
# cannot open the database read-write if it cannot create them.
#
# DATA_DIR (see base.py) is the parent for the database, the uploads and the
# cache. In production set DATA_DIR=/srv/portfolio/data in the environment.
SQLITE_PATH = config("SQLITE_PATH", default=str(DATA_DIR / "db.sqlite3"))

# Gunicorn workers each hold their own connection. Threads within a worker
# share it, and SQLite serialises writes anyway, so a small number of workers
# with a few threads each beats many processes competing for the write lock.
# See deploy/gunicorn.service.

# Sessions in the database would make every request a write. Signed cookies
# keep reads read-only, which is what WAL is good at.
SESSION_ENGINE = config(
    "SESSION_ENGINE", default="django.contrib.sessions.backends.signed_cookies"
)


# ---------------------------------------------------------------------------
# Fail fast on a missing secret
# ---------------------------------------------------------------------------
# DEBUG is off here, so a placeholder SECRET_KEY would not be obvious — it
# would just quietly invalidate every signature the first time the process
# restarted with a different default. Refuse to boot instead.
if not SECRET_KEY or SECRET_KEY.startswith("django-insecure"):  # noqa: F405
    raise ImproperlyConfigured(  # noqa: F405
        "SECRET_KEY is unset or still the development placeholder. "
        "Generate one with:\n"
        "  python -c \"from django.core.management.utils import "
        'get_random_secret_key as k; print(k())"'
    )

if not ALLOWED_HOSTS or ALLOWED_HOSTS == ["127.0.0.1", "localhost"]:  # noqa: F405
    raise ImproperlyConfigured(
        "ALLOWED_HOSTS is not configured for production. Set it in .env, "
        "e.g. ALLOWED_HOSTS=example.com,www.example.com"
    )
