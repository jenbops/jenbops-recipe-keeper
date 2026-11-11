output "ssh_command" {
  value = "gcloud compute ssh ${google_compute_instance.recipes.name} --zone ${var.zone} --tunnel-through-iap --project ${var.project_id}"
}

output "backup_bucket" {
  value = google_storage_bucket.backups.name
}