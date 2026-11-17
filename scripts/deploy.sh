#!/usr/bin/env bash
# Deploys one release tag on the VM: backup -> checkout -> migrate -> rebuild -> health check.
# Usage: scripts/deploy.sh v1.2
set -euo pipefail
cd "$(dirname "$0")/.."

TAG="${1:?usage: scripts/deploy.sh vX.Y}"
# the tag name ends up in git commands, so accept only a plain version number
[[ "$TAG" =~ ^v[0-9]+(\.[0-9]+)*$ ]] || { echo "Refusing odd tag name: $TAG"; exit 1; }

if [ -n "$(git status --porcelain)" ]; then
  echo "The VM's working copy has local changes; refusing to deploy over them."
  exit 1
fi

PREVIOUS=$(git rev-parse HEAD)   # where to go back to if something fails

echo "== Backup =="
./scripts/backup.sh

echo "== Fetch $TAG =="
git fetch --tags --force origin
git checkout --quiet "$TAG"

health() {   # wait up to ~60 seconds for the app to answer
  for i in $(seq 1 30); do
    curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1 && return 0
    sleep 2
  done
  return 1
}

rollback() {
  echo "!! Deploy of $TAG failed; going back to $PREVIOUS"
  git checkout --quiet "$PREVIOUS"
  docker compose up -d --build web
  exit 1
}

echo "== Migrate database =="
./scripts/migrate.sh || rollback

echo "== Rebuild app =="
docker compose up -d --build web || rollback
health || rollback

echo "== Fill ingredient rows for any recipe that lacks them =="
docker compose exec -T web python -m app.backfill || echo "(backfill skipped)"

echo "Deployed $TAG"