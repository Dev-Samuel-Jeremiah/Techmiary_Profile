#!/usr/bin/env bash
#
# Restore the database (and optionally media) from a backup written by
# backup.sh. Stops the site first: restoring under a running app would leave
# workers holding connections to a file that no longer exists.
#
#   sudo ./restore.sh /srv/portfolio/data/backups/db-20260927T023000Z.sqlite3.gz
#
set -euo pipefail

APP_DIR="${APP_DIR:-/srv/portfolio}"
DATA_DIR="${DATA_DIR:-$APP_DIR/data}"
DB="${SQLITE_PATH:-$DATA_DIR/db.sqlite3}"
SERVICE="${SERVICE:-techmiary-portfolio}"

ARCHIVE="${1:-}"
if [ -z "$ARCHIVE" ] || [ ! -f "$ARCHIVE" ]; then
    echo "Usage: $0 /path/to/db-TIMESTAMP.sqlite3.gz" >&2
    echo >&2
    echo "Available:" >&2
    ls -1t "$DATA_DIR/backups/db-"*.gz 2>/dev/null | head -10 >&2 || echo "  (none)" >&2
    exit 1
fi

echo "This will replace $DB with $ARCHIVE."
read -r -p "Type 'restore' to continue: " CONFIRM
[ "$CONFIRM" = "restore" ] || { echo "Aborted."; exit 1; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "==> Decompressing"
gunzip -c "$ARCHIVE" > "$TMP/restored.sqlite3"

echo "==> Checking the archive before trusting it"
python3 - "$TMP/restored.sqlite3" <<'PY'
import sqlite3
import sys

connection = sqlite3.connect(sys.argv[1])
result = connection.execute("PRAGMA integrity_check").fetchone()[0]
connection.close()
if result != "ok":
    raise SystemExit(f"Refusing to restore: integrity_check returned {result}")
print("   archive is intact")
PY

echo "==> Stopping $SERVICE"
sudo systemctl stop "$SERVICE"

if [ -f "$DB" ]; then
    ASIDE="$DB.replaced-$(date -u +%Y%m%dT%H%M%SZ)"
    echo "==> Moving the current database aside: $ASIDE"
    mv "$DB" "$ASIDE"
    # The sidecar files belong to the old database, not the new one.
    rm -f "$DB-wal" "$DB-shm"
fi

echo "==> Installing the restored database"
install -o www-data -g www-data -m 640 "$TMP/restored.sqlite3" "$DB"

echo "==> Applying any migrations the backup predates"
sudo -u www-data env DJANGO_SETTINGS_MODULE=config.settings.production \
    "$APP_DIR/venv/bin/python" "$APP_DIR/manage.py" migrate --noinput

echo "==> Starting $SERVICE"
sudo systemctl start "$SERVICE"
echo "==> Done. Restore media separately if you need it:"
echo "    tar -xzf $DATA_DIR/backups/media-TIMESTAMP.tar.gz -C $DATA_DIR"
