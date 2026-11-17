#!/usr/bin/env bash
# Applies any db/migrations/*.sql files that have not run yet, in filename order.
set -euo pipefail
cd "$(dirname "$0")/.."

# read just the two settings we need from .env (we don't "source" the whole file,
# because a password with special characters could confuse the shell)
POSTGRES_USER=$(grep '^POSTGRES_USER=' .env | cut -d= -f2-)
POSTGRES_DB=$(grep '^POSTGRES_DB=' .env | cut -d= -f2-)

# run psql inside the database container; stop at the first SQL error
psql_run() {
  docker compose exec -T db psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" "$@"
}

# the table that remembers which files have run
psql_run -q -c "CREATE TABLE IF NOT EXISTS schema_migrations (
  filename   TEXT PRIMARY KEY,
  applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);"

applied=0
for file in db/migrations/*.sql; do
  name=$(basename "$file")
  already=$(psql_run -tA -c "SELECT 1 FROM schema_migrations WHERE filename = '$name'")
  if [ "$already" = "1" ]; then
    echo "skip   $name"
    continue
  fi
  echo "apply  $name"
  psql_run -q --single-transaction < "$file"
  psql_run -q -c "INSERT INTO schema_migrations (filename) VALUES ('$name')"
  applied=$((applied + 1))
done
echo "Done. $applied new migration(s) applied."