resource "google_artifact_registry_repository" "containers" {
  location      = var.region
  repository_id = local.name_prefix
  format        = "DOCKER"
  description   = "Container images for the Philippine oil tanker tracker"

  labels = local.labels

  depends_on = [google_project_service.enabled]
}

locals {
  artifact_repo_url = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.containers.repository_id}"
  api_image         = "${local.artifact_repo_url}/api:latest"
  ingestor_image    = "${local.artifact_repo_url}/ingestor:latest"
}
