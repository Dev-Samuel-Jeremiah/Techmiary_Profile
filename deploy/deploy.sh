#!/usr/bin/env bash
#
# Deploy: back up, pull, install, migrate, collect static, check, restart.
#
# The backup comes first and on purpose. A migration is the one routine
# operation that can destroy data, and on SQLite there is no transaction log to
# roll forward from — the dated file written here is the whole safety net.
#
set -euo pipefail

APP_DIR="${APP_DIR:-/srv/portfolio}"
DATA_DIR="${DATA_DIR:-$APP_DIR/data}"
SERVICE="${SERVICE:-techmiary-portfolio}"
PYTHON="$APP_DIR/venv/bin/python"
PIP="$APP_DIR/venv/bin/pip"

cd "$APP_DIR"
export DJANGO_SETTINGS_MODULE=config.settings.production

echo "==> Backing up before anything else"
DATA_DIR="$DATA_DIR" "$APP_DIR/deploy/backup.sh"

echo "==> Fetching latest code"
git pull --ff-only

echo "==> Installing dependencies"
# No --upgrade: requirements.txt is pinned, and a silent major bump is not
# something a deploy should decide on its own.
"$PIP" install -r requirements.txt

echo "==> Applying migrations"
"$PYTHON" manage.py migrate --noinput

echo "==> Collecting static files"
"$PYTHON" manage.py collectstatic --noinput

echo "==> Deployment checks"
"$PYTHON" manage.py check --deploy --fail-level WARNING

echo "==> Restarting $SERVICE"
sudo systemctl restart "$SERVICE"

echo "==> Waiting for the socket to answer"
for _ in $(seq 1 20); do
    if sudo systemctl is-active --quiet "$SERVICE"; then
        sleep 1
        if curl -fsS --unix-socket /run/gunicorn/techmiary-portfolio.sock \
             -o /dev/null http://localhost/robots.txt 2>/dev/null; then
            echo "==> Up"
            exit 0
        fi
    fi
    sleep 1
done

echo "!! The service did not answer. Recent logs:" >&2
sudo journalctl -u "$SERVICE" -n 40 --no-pager >&2
exit 1
