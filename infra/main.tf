terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 8.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# --- Network: a private network with one subnet ---
resource "google_compute_network" "main" {
  name                    = "recipe-net"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "main" {
  name          = "recipe-subnet"
  ip_cidr_range = "10.10.0.0/24"
  region        = var.region
  network       = google_compute_network.main.id
}

# --- Firewall: SSH allowed only from Google's IAP range (35.235.240.0/20) ---
resource "google_compute_firewall" "ssh_iap" {
  name      = "allow-ssh-from-iap"
  network   = google_compute_network.main.name
  direction = "INGRESS"

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["35.235.240.0/20"]
  target_tags   = ["recipe-keeper"]
}

# --- Identity for the VM (used later to write backups) ---
resource "google_service_account" "vm" {
  account_id   = "recipe-vm"
  display_name = "Recipe Keeper VM"
}

# --- Backup bucket: private, regional, old backups auto-deleted ---
resource "google_storage_bucket" "backups" {
  name                        = "${var.project_id}-backups"
  location                    = upper(var.region)
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false # lets "terraform destroy" delete a non-empty bucket

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }
}

resource "google_storage_bucket_iam_member" "vm_backups" {
  bucket = google_storage_bucket.backups.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.vm.email}"
}

# --- The VM: e2-micro, standard disk, free-tier region ---
resource "google_compute_instance" "recipes" {
  name                      = "recipe-keeper"
  machine_type              = "e2-micro"
  zone                      = var.zone
  tags                      = ["recipe-keeper"]
  allow_stopping_for_update = true

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-12"
      size  = 30
      type  = "pd-standard"
    }
  }

  network_interface {
    subnetwork = google_compute_subnetwork.main.id
    access_config {} # gives the VM a temporary external IP (for outbound internet)
  }

  service_account {
    email  = google_service_account.vm.email
    scopes = ["cloud-platform"]
  }

  metadata_startup_script = file("${path.module}/startup.sh")
}
# --- Releases bucket: holds one tiny file, "approved-release", written by CI after tests pass ---
resource "google_storage_bucket" "releases" {
  name                        = "${var.project_id}-releases"
  location                    = upper(var.region)
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = true # nothing precious lives here, so "terraform destroy" may empty it

  versioning {
    enabled = true # every overwrite keeps the old version: a free history of approved releases
  }
}

# --- The identity CI uses to publish the approved release ---
resource "google_service_account" "deploy" {
  account_id   = "recipe-deploy"
  display_name = "Recipe Keeper deploy"
}

# CI may write the approved-release file, in THIS bucket only
resource "google_storage_bucket_iam_member" "deploy_writes_releases" {
  bucket = google_storage_bucket.releases.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.deploy.email}"
}

# The VM may only read it
resource "google_storage_bucket_iam_member" "vm_reads_releases" {
  bucket = google_storage_bucket.releases.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.vm.email}"
}

# Builds that run as the deploy robot need permission to write their own logs
resource "google_project_iam_member" "deploy_logs" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.deploy.email}"
}