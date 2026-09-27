#!/usr/bin/env bash
#
# Back up the SQLite database — safely, while the site is running.
#
# Copying db.sqlite3 with cp is not a backup. In WAL mode the live file is only
# half the story: recent transactions sit in db.sqlite3-wal, and a copy taken
# mid-checkpoint can be torn. SQLite's own backup API walks the database under
# a read lock and produces a consistent file, which is what this does.
#
#   ./backup.sh                 # write a dated, gzipped backup, prune old ones
#   KEEP=30 ./backup.sh         # keep 30 instead of the default 14
#
set -euo pipefail

APP_DIR="${APP_DIR:-/srv/portfolio}"
DATA_DIR="${DATA_DIR:-$APP_DIR/data}"
DB="${SQLITE_PATH:-$DATA_DIR/db.sqlite3}"
BACKUP_DIR="${BACKUP_DIR:-$DATA_DIR/backups}"
KEEP="${KEEP:-14}"
PYTHON="${PYTHON:-$APP_DIR/venv/bin/python}"

[ -x "$PYTHON" ] || PYTHON="$(command -v python3)"

if [ ! -f "$DB" ]; then
    echo "No database at $DB" >&2
    exit 1
fi

mkdir -p "$BACKUP_DIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TARGET="$BACKUP_DIR/db-$STAMP.sqlite3"

echo "==> Backing up $DB"
"$PYTHON" - "$DB" "$TARGET" <<'PY'
import sqlite3
import sys

source_path, target_path = sys.argv[1], sys.argv[2]

# Read-only URI: the backup must never be the thing that writes to the live
# database, even by accident.
source = sqlite3.connect(f"file:{source_path}?mode=ro", uri=True, timeout=30)
target = sqlite3.connect(target_path)
try:
    with target:
        source.backup(target)
    # A backup nobody verified is a backup nobody has.
    result = target.execute("PRAGMA integrity_check").fetchone()[0]
    if result != "ok":
        raise SystemExit(f"integrity_check on the backup returned: {result}")
finally:
    source.close()
    target.close()
print("   consistent copy written")
PY

gzip -9 "$TARGET"
chmod 600 "$TARGET.gz"
echo "==> Wrote $TARGET.gz ($(du -h "$TARGET.gz" | cut -f1))"

# Uploaded media is user data too, and it is not in the database. Roll it into
# the same dated set so a restore has both halves.
if [ -d "$DATA_DIR/media" ]; then
    MEDIA_ARCHIVE="$BACKUP_DIR/media-$STAMP.tar.gz"
    tar -czf "$MEDIA_ARCHIVE" -C "$DATA_DIR" media
    chmod 600 "$MEDIA_ARCHIVE"
    echo "==> Wrote $MEDIA_ARCHIVE ($(du -h "$MEDIA_ARCHIVE" | cut -f1))"
fi

echo "==> Pruning to the newest $KEEP of each kind"
for prefix in db media; do
    # shellcheck disable=SC2012  # filenames here are generated, never arbitrary
    ls -1t "$BACKUP_DIR/$prefix-"*.gz 2>/dev/null | tail -n "+$((KEEP + 1))" | while read -r old; do
        echo "    removing $(basename "$old")"
        rm -f "$old"
    done
done

echo "==> Done"
echo "    Copy these off the machine. A backup on the same disk is not a backup."
