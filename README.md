# Recipe Keeper

A private, mobile-friendly web app for saving recipes, tagging them, and finding any of them fast. Built as a hands-on training project: design it like a product manager (requirements first), build it, containerize it, deploy it with Infrastructure as Code (IaC), and protect it.

- **Live:** `recipes.jenb-ops.dev` (private, behind a login)
- **Requirements:** see the Product Requirements Document (PRD) in the project docs

## Features

- Add, edit, and delete recipes (title, ingredients, steps, notes, source link)
- Multiple tags per recipe, with tag-filter chips (a recipe must match all selected tags)
- Keyword search across title, ingredients, and steps (PostgreSQL full-text search)
- Search updates as you type, without a full page reload
- Mobile-first layout with large tap targets
- A JavaScript Object Notation (JSON) interface with interactive docs at `/docs`

## Architecture

```
Phone / laptop
      |
      v
Cloudflare  (Domain Name System (DNS), HTTPS, Access login wall)
      |
      |  Cloudflare Tunnel: the VM connects OUT to Cloudflare, so no inbound ports are open
      v
Google Cloud e2-micro Virtual Machine (VM), Debian 12
 +- Docker Compose
     +- cloudflared  (tunnel connector)
     +- web          (FastAPI app)
     +- db           (PostgreSQL 17)
      |
      +--> nightly pg_dump --> private Cloud Storage bucket (30-day auto-delete)
```

## Tech stack

| Layer | Choice |
|---|---|
| App | Python 3.13, FastAPI, Jinja2 templates, htmx |
| Database | PostgreSQL 17 (full-text search, many-to-many tags) |
| Containers | Docker, Docker Compose (OrbStack locally) |
| Hosting | Google Cloud Platform (GCP) e2-micro VM, Always Free eligible |
| Infrastructure as Code | Terraform (network, firewall, VM, service account, backup bucket) |
| Access and ingress | Cloudflare Tunnel and Cloudflare Access (one-time email code) |
| Admin access | Secure Shell (SSH) through Identity-Aware Proxy (IAP), no public SSH |

## Project structure

```
.
├── compose.yaml            # db, web, and cloudflared (prod profile) services
├── Dockerfile              # app image, runs as a non-root user
├── cloudbuild.yaml         # Cloud Build pipeline: build, smoke test, publish image
├── requirements.txt        # pinned dependency versions
├── .env.example            # template for the local, git-ignored .env
├── app/
│   ├── main.py             # JSON endpoints, security middleware
│   ├── ui.py               # HTML pages (list, view, add, edit, delete)
│   ├── repo.py             # all database queries
│   ├── db.py               # database connection
│   └── templates/          # Jinja2 page templates
├── db/schema.sql           # tables, join table, full-text search index
├── scripts/
│   ├── backup.sh               # cloud VM: nightly backup to Cloud Storage
│   ├── backup-local.sh         # Mac: nightly backup to ~/Backups/recipe-keeper
│   ├── restore-local.sh        # Mac: safe restore test, or live restore
│   └── push-local-to-cloud.sh  # Mac: replace the cloud database with the local one
└── infra/                  # Terraform
    ├── main.tf  variables.tf  outputs.tf
    └── startup.sh          # creates a 2 GB swap file on first boot
```

## Run locally

Prerequisites: Docker (or OrbStack) running.

```bash
cp .env.example .env            # then edit the password
docker compose up -d --build    # build and start db + web
docker compose exec -T db psql -U recipes -d recipes < db/schema.sql
open http://localhost:8000      # the app
open http://localhost:8000/docs # interactive JSON docs
```

Stop with `docker compose down` (keeps data) or `docker compose down -v` (also deletes the database volume).

The `db` and `web` services use `restart: unless-stopped`, so after a reboot the Docker engine (OrbStack, which starts at login) brings them back automatically. Containers you stopped yourself with `down` or `stop` stay stopped. The `cloudflared` service belongs to the `prod` profile and never starts locally.

## Releases

Known-good versions are marked with Git tags (for example `v1.0`). To return to one: `git checkout v1.0`. Push a new tag with `git tag -a v1.1 -m "message" && git push origin v1.1`.

## Continuous integration (Cloud Build)

`cloudbuild.yaml` builds the image, runs a smoke test (the app code imports cleanly), and publishes the image to Artifact Registry. A trigger on a lab branch starts it on every push. The trigger and the registry are created on demand for experiments and deleted afterward to avoid storage charges. Setup needs: the Cloud Build and Artifact Registry services enabled, an Artifact Registry repository, a build service account with logging, registry-write, and storage-read roles, and the Cloud Build GitHub app granted access to this repository.

## Data model

```
recipes ──< recipe_tags >── tags
```

- `recipes`: title, ingredients, steps, source_url, notes, timestamps, and a generated `search_vector` column indexed with a Generalized Inverted Index (GIN)
- `tags`: unique, lowercased names
- `recipe_tags`: join table; deleting a recipe removes its links

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Web app: list, search, tag filter |
| GET/POST | `/r/new` | Add a recipe |
| GET | `/r/{id}` | View a recipe |
| GET/POST | `/r/{id}/edit` | Edit a recipe |
| POST | `/r/{id}/delete` | Delete a recipe |
| GET/POST | `/recipes` | JSON list (`?q=` and repeated `?tag=`) / create |
| GET/PUT/DELETE | `/recipes/{id}` | JSON read / update / delete |
| GET | `/tags` | Tags with recipe counts |
| GET | `/health`, `/health/db` | Liveness checks |

## Deploy

Prerequisites: a GCP project with billing enabled and a budget alert, `gcloud` signed in, Terraform, and a domain on Cloudflare.

1. **Provision:** `cd infra && terraform init && terraform plan && terraform apply`
2. **Connect:** `gcloud compute ssh recipe-keeper --zone us-central1-a --tunnel-through-iap`
3. **On the VM:** install Docker, add a read-only GitHub deploy key, clone the repo, create `.env` (strong random database password, `TUNNEL_TOKEN`, `COMPOSE_PROFILES=prod`).
4. **Start:** `docker compose up -d --build`, then apply `db/schema.sql`.
5. **Cloudflare:** create an Access application with an Allow policy for your email, create a tunnel, and add a published route to `http://web:8000`.

## Backups and restore

Recipes live in two places (the local Mac stack and the cloud VM), so each has its own backup. A backup you have never restored is not proven: run the restore test after any change to the backup scripts.

### Cloud (VM)

`scripts/backup.sh` dumps the database, compresses it, and uploads it to a private bucket. A cron entry runs it nightly (03:15 Coordinated Universal Time (UTC)). Old backups are deleted by a 30-day bucket rule.

Restore test (use a throwaway database, never the live one):

```bash
gcloud storage cp gs://<bucket>/db/<backup>.sql.gz /tmp/restore.sql.gz
docker compose exec -T db psql -U recipes -d postgres -c "CREATE DATABASE restore_test;"
gunzip -c /tmp/restore.sql.gz | docker compose exec -T db psql -U recipes -d restore_test
docker compose exec -T db psql -U recipes -d restore_test -c "SELECT title FROM recipes;"
docker compose exec -T db psql -U recipes -d postgres -c "DROP DATABASE restore_test;"
```

### Local (Mac)

`scripts/backup-local.sh` dumps the local Docker database to `~/Backups/recipe-keeper/`, writes to a temporary file first, rejects suspiciously small dumps, and keeps the newest 14 backups. Docker (OrbStack) must be running.

It is scheduled with launchd, the macOS scheduler, through `~/Library/LaunchAgents/dev.jenbops.recipe-backup.plist` (kept outside the repo). The job runs daily at 21:00 local time, runs once after wake if the Mac was asleep, and writes its output to `~/Backups/recipe-keeper/backup.log`.

| Command | Purpose |
|---|---|
| `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/dev.jenbops.recipe-backup.plist` | load the job (once; it also loads at login) |
| `launchctl kickstart -k gui/$(id -u)/dev.jenbops.recipe-backup` | run it now |
| `launchctl print gui/$(id -u)/dev.jenbops.recipe-backup` | show state and last exit code (0 means success) |
| `launchctl bootout gui/$(id -u)/dev.jenbops.recipe-backup` | unload it (also do this before editing the plist, then bootstrap again) |

### Restoring locally

```bash
./scripts/restore-local.sh                  # SAFE TEST: newest backup into a throwaway database, prints counts and titles, then deletes it
./scripts/restore-local.sh FILE.sql.gz      # same, for a specific backup
./scripts/restore-local.sh [FILE] --live    # REPLACES the real local database
```

`--live` asks you to type `RESTORE`, takes a safety backup of the current data first, stops the web container, drops and recreates the database, loads the backup as one all-or-nothing transaction, and restarts the web container. Because the safety backup becomes the newest file, name the file you want explicitly after a live restore.

### Pushing local data to the cloud

```bash
./scripts/push-local-to-cloud.sh
```

Takes a fresh local dump, shows recipe and tag counts for local and cloud, asks you to type `PUSH`, uploads the dump over the Identity-Aware Proxy tunnel, takes a safety backup of the cloud database to the bucket, then replaces the cloud database and restarts the cloud web container. Settings can be overridden with `PROJECT_ID`, `ZONE`, and `VM`.

Before using it:

- Recipes that exist only in the cloud are replaced (they remain in the safety backup for 30 days).
- The cloud site is briefly unavailable while the web container is stopped.
- The cloud code version must match the local database structure; deploy the matching code first after any schema change.
- To see the counts without changing anything, run it and type anything other than `PUSH`.

## Security

- No inbound ports: visitors reach the app only through the Cloudflare Tunnel; SSH is allowed only from Google's IAP range
- Cloudflare Access login in front of the whole site
- Cross-site request forgery (CSRF) defense: state-changing requests with a foreign `Origin` header are rejected
- Security headers (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`)
- All database access uses parameterized queries (no string-built Structured Query Language (SQL))
- App container runs as a non-root user; dependency versions are pinned
- Secrets live only in the git-ignored `.env` on each machine; the GitHub deploy key is read-only
- Automatic Debian security updates on the VM

## Measured footprint

On the 1 GB VM with a 2 GB swap file: the web container uses about 52 MiB and PostgreSQL about 40 MiB at idle.

## Cost notes

Designed to stay within GCP Always Free limits: one e2-micro VM in `us-west1`, `us-central1`, or `us-east1`, a 30 GB standard disk, and under 1 GB of outbound traffic. The VM's temporary external IP address could in theory be billed (about $3.65 per month in the worst case); no external IP charge has appeared in the billing reports so far, but billing data lags, so keep re-checking. Keep a budget alert set, and remember that leftover resources from other projects (such as a Cloud DNS zone) can bill the same account.

## Tear down

```bash
cd infra && terraform destroy
```

The backup bucket has `force_destroy = false`, so Terraform refuses to delete it while it holds backups. Set it to `true` first if you really want everything gone. Also delete the Cloudflare tunnel and Access application.

## Roadmap

- Self-host the htmx script and add a strict Content Security Policy
- Photos, import from URL, structured ingredients, and meal planning
- Automated tests and a GitHub Actions pipeline
- Remote Terraform state
