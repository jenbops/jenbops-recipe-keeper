#!/bin/bash
# Restore a local backup.
#   ./restore-local.sh                    test the newest backup in a throwaway database (safe)
#   ./restore-local.sh FILE.sql.gz        test a specific backup
#   ./restore-local.sh [FILE] --live      REPLACE the real database (asks first)
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

REPO="$HOME/repos/jenbops-recipe-keeper"
DEST="$HOME/Backups/recipe-keeper"
LIVE=0
FILE=""

for arg in "$@"; do
  case "$arg" in
    --live) LIVE=1 ;;
    -h|--help) sed -n '2,5p' "$0"; exit 0 ;;
    *) FILE="$arg" ;;
  esac
done

cd "$REPO"

# if the restore fails partway, make sure the app is running again and say where the safety copy is
trap 'echo "Restore FAILED. Backups are in $DEST" >&2; docker compose start web >/dev/null 2>&1 || true' ERR

# no file given: use the newest backup
if [ -z "$FILE" ]; then
  FILE=$(ls -1t "$DEST"/recipes-*.sql.gz 2>/dev/null | head -1 || true)
fi
[ -n "$FILE" ] && [ -f "$FILE" ] || { echo "No backup file found." >&2; exit 1; }
gunzip -t "$FILE"   # checks the gzip file is intact before using it
echo "Using backup: $FILE"

# helper: run psql inside the db container; stop at the first SQL error
psql_db() { docker compose exec -T db psql -U recipes -v ON_ERROR_STOP=1 "$@"; }

COUNTS="SELECT (SELECT count(*) FROM recipes) AS recipes, (SELECT count(*) FROM tags) AS tags;"

if [ "$LIVE" -eq 0 ]; then
  # SAFE TEST: load into a scratch database, show what's inside, then delete it
  psql_db -d postgres -c "DROP DATABASE IF EXISTS restore_test WITH (FORCE);"
  psql_db -d postgres -c "CREATE DATABASE restore_test;"
  gunzip -c "$FILE" | psql_db -d restore_test -1 -q -f -
  psql_db -d restore_test -c "$COUNTS"
  psql_db -d restore_test -c "SELECT id, title FROM recipes ORDER BY id;"
  psql_db -d postgres -c "DROP DATABASE restore_test;"
  echo "Test restore OK. Your live data was not touched."
  exit 0
fi

# LIVE RESTORE: replaces the real database
echo "WARNING: this REPLACES the real recipes database with the backup above."
read -r -p "Type RESTORE to continue: " ANSWER
[ "$ANSWER" = "RESTORE" ] || { echo "Cancelled."; exit 1; }

echo "Taking a safety backup of the current data first..."
"$REPO/scripts/backup-local.sh"

docker compose stop web
psql_db -d postgres -c "DROP DATABASE recipes WITH (FORCE);"
psql_db -d postgres -c "CREATE DATABASE recipes;"
gunzip -c "$FILE" | psql_db -d recipes -1 -q -f -
docker compose start web
psql_db -d recipes -c "$COUNTS"
echo "Live restore complete."