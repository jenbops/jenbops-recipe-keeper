#!/usr/bin/env bash
# Run by a systemd timer: deploys the release CI has approved, if it is new.
set -euo pipefail
cd "$(dirname "$0")/.."

# only one copy at a time (a deploy can outlast the 5-minute timer)
exec 9>/tmp/recipe-deploy.lock
flock -n 9 || exit 0

# the VM can ask Google which project it lives in; the bucket name is built from that
PROJECT=$(curl -fsS -H "Metadata-Flavor: Google" \
  http://metadata.google.internal/computeMetadata/v1/project/project-id)
BUCKET="gs://${PROJECT}-releases"

APPROVED=$(gcloud storage cat "$BUCKET/approved-release" 2>/dev/null | tr -d '[:space:]') || exit 0
[[ "$APPROVED" =~ ^v[0-9]+(\.[0-9]+)*$ ]] || { echo "Ignoring odd approved-release value"; exit 0; }

DEPLOYED_FILE="$HOME/.recipe-deployed-release"
FAILED_FILE="$HOME/.recipe-failed-release"
DEPLOYED=$(cat "$DEPLOYED_FILE" 2>/dev/null || true)
FAILED=$(cat "$FAILED_FILE" 2>/dev/null || true)

[ "$APPROVED" = "$DEPLOYED" ] && exit 0
# a release that already failed is not retried every 5 minutes; a person looks at it
[ "$APPROVED" = "$FAILED" ] && exit 0

echo "New approved release: $APPROVED (running: ${DEPLOYED:-none})"
if ./scripts/deploy.sh "$APPROVED"; then
  echo "$APPROVED" > "$DEPLOYED_FILE"
  rm -f "$FAILED_FILE"
else
  echo "$APPROVED" > "$FAILED_FILE"
  exit 1
fi