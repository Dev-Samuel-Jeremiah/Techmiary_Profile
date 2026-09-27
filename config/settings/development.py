"""Local development settings."""
from .base import *  # noqa: F401,F403
from .base import BASE_DIR, config

DEBUG = config("DEBUG", default=True, cast=bool)
ALLOWED_HOSTS = ["*"]

# The database comes from base.py, which defaults to SQLite with the
# production pragmas applied. Defining it again here would mean development
# and production ran on different settings — the kind of difference that only
# shows up under load.

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Serve static files straight from disk while developing.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# ---------------------------------------------------------------------------
# Static file caching in development
# ---------------------------------------------------------------------------
# runserver's own static handler sends only Last-Modified — no Cache-Control
# and no ETag. Browsers then apply *heuristic* caching: they invent a freshness
# window and reuse the file without revalidating, so an edited stylesheet keeps
# serving the old version on ordinary navigation until a hard reload. In
# production the hashed filenames from CompressedManifestStaticFilesStorage
# make this impossible, so it only ever bites while developing.
#
# whitenoise.runserver_nostatic disables that handler and lets WhiteNoise serve
# instead, with an explicit max-age of 0 so every request is revalidated.
INSTALLED_APPS = ["whitenoise.runserver_nostatic"] + INSTALLED_APPS  # noqa: F405

WHITENOISE_USE_FINDERS = True   # serve from STATICFILES_DIRS, no collectstatic
WHITENOISE_AUTOREFRESH = True   # pick up edits without restarting the server
WHITENOISE_MAX_AGE = 0          # always revalidate; no stale CSS after an edit
