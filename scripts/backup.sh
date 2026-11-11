#!/bin/bash
# Nightly database backup: dump -> compress -> upload to the private bucket
set -euo pipefail   # stop on any error, undefined variable, or failed step in a pipe

cd "$(dirname "$0")/.."   # run from the repo folder, wherever the script is called from
BUCKET="gs://jenbops-recipe-keeper-backups"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
FILE="/tmp/recipes-$STAMP.sql.gz"

# pg_dump runs inside the db container; -T is needed because cron has no terminal
docker compose exec -T db pg_dump -U recipes -d recipes | gzip > "$FILE"

gcloud storage cp "$FILE" "$BUCKET/db/recipes-$STAMP.sql.gz"
rm -f "$FILE"
echo "backup ok: recipes-$STAMP.sql.gz"