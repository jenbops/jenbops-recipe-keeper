variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "region" {
  type    = string
  default = "us-central1" # must be us-west1, us-central1, or us-east1 for the free VM
}

variable "zone" {
  type    = string
  default = "us-central1-a"
}