terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
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
  force_destroy               = true # lets "terraform destroy" delete a non-empty bucket

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