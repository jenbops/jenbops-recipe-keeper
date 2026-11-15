#!/bin/bash
# Local nightly backup: dump the Docker database to ~/Backups, keep the newest 14
set -euo pipefail
# launchd runs with a minimal PATH, so add where Docker's command lives
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

REPO="$HOME/repos/jenbops-recipe-keeper"
DEST="$HOME/Backups/recipe-keeper"
KEEP=14

mkdir -p "$DEST"
cd "$REPO"
STAMP=$(date +%Y%m%dT%H%M%S)
OUT="$DEST/recipes-$STAMP.sql.gz"

# dump -> compress into a temporary file first
docker compose exec -T db pg_dump -U recipes -d recipes | gzip > "$OUT.tmp"

# an empty dump compresses to a tiny file; refuse to keep it
if [ "$(stat -f%z "$OUT.tmp")" -lt 200 ]; then
  rm -f "$OUT.tmp"
  echo "backup too small, discarded" >&2
  exit 1
fi
mv "$OUT.tmp" "$OUT"

# delete everything except the newest $KEEP backups
ls -1t "$DEST"/recipes-*.sql.gz | tail -n +$((KEEP + 1)) | xargs -I{} rm -f {}
echo "backup ok: $OUT"