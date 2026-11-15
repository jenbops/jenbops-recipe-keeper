#!/bin/bash
# Copy the LOCAL recipes database to the CLOUD VM, REPLACING the cloud database.
# Overrides: PROJECT_ID=... ZONE=... VM=... ./scripts/push-local-to-cloud.sh
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

PROJECT_ID="${PROJECT_ID:-jenbops-recipe-keeper}"
ZONE="${ZONE:-us-central1-a}"
VM="${VM:-recipe-keeper}"
LOCAL_REPO="$HOME/repos/jenbops-recipe-keeper"
DUMP="/tmp/recipes-push-$(date +%Y%m%dT%H%M%S).sql.gz"

# always delete the temporary local dump when the script ends
trap 'rm -f "$DUMP"' EXIT
# if anything fails midway, say what to check
trap 'echo "PUSH FAILED. The cloud app may be stopped: ssh in, run docker compose start web, and restore from the safety backup in the bucket." >&2' ERR

# helper: run a command on the VM through the secure IAP tunnel (no terminal needed)
remote() {
  gcloud compute ssh "$VM" --zone "$ZONE" --project "$PROJECT_ID" \
    --tunnel-through-iap --ssh-flag=-T --command="$1"
}

COUNTS='SELECT (SELECT count(*) FROM recipes) AS recipes, (SELECT count(*) FROM tags) AS tags;'

# 1. dump the local database
cd "$LOCAL_REPO"
docker compose exec -T db pg_dump -U recipes -d recipes | gzip > "$DUMP"
if [ "$(stat -f%z "$DUMP")" -lt 200 ]; then
  echo "Local dump is suspiciously small; stopping." >&2
  exit 1
fi

# 2. compare local and cloud before doing anything
echo "=== LOCAL ==="
docker compose exec -T db psql -U recipes -d recipes -c "$COUNTS"
echo "=== CLOUD (will be replaced) ==="
remote "cd ~/jenbops-recipe-keeper && docker compose exec -T db psql -U recipes -d recipes -c \"$COUNTS\" < /dev/null"

# 3. explicit confirmation
echo
echo "WARNING: the CLOUD database will be REPLACED by the LOCAL one."
echo "Recipes that exist only in the cloud will be lost (a safety backup is taken first)."
read -r -p "Type PUSH to continue: " ANSWER
[ "$ANSWER" = "PUSH" ] || { echo "Cancelled."; trap - ERR; exit 1; }

# 4. upload the dump to the VM
gcloud compute scp "$DUMP" "$VM:~/recipes-push.sql.gz" \
  --zone "$ZONE" --project "$PROJECT_ID" --tunnel-through-iap

# 5. restore on the VM. NOTE: every docker command that doesn't need input has
# "< /dev/null" so it can't swallow the rest of this script, which arrives on stdin.
remote 'bash -s' <<'REMOTE'
set -euo pipefail
cd ~/jenbops-recipe-keeper
test -f ~/recipes-push.sql.gz

echo "Safety backup of the cloud database to the bucket..."
./scripts/backup.sh < /dev/null

docker compose stop web < /dev/null
docker compose exec -T db psql -U recipes -v ON_ERROR_STOP=1 -d postgres -c "DROP DATABASE recipes WITH (FORCE);" < /dev/null
docker compose exec -T db psql -U recipes -v ON_ERROR_STOP=1 -d postgres -c "CREATE DATABASE recipes;" < /dev/null
gunzip -c ~/recipes-push.sql.gz | docker compose exec -T db psql -U recipes -v ON_ERROR_STOP=1 -d recipes -1 -q -f -
docker compose start web < /dev/null
rm -f ~/recipes-push.sql.gz

echo "=== CLOUD after push ==="
docker compose exec -T db psql -U recipes -d recipes -c "SELECT (SELECT count(*) FROM recipes) AS recipes, (SELECT count(*) FROM tags) AS tags;" < /dev/null
REMOTE

echo "Done. Open https://recipes.jenb-ops.dev and check your recipes."