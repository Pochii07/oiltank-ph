resource "google_service_account" "api" {
  account_id   = "${local.name_prefix}-api"
  display_name = "API service (Cloud Run)"
}

resource "google_service_account" "ingestor" {
  account_id   = "${local.name_prefix}-ingest"
  display_name = "Ingestor job (Cloud Run Job)"
}

resource "google_service_account" "scheduler" {
  account_id   = "${local.name_prefix}-sched"
  display_name = "Scheduler invoker"
}

locals {
  api_roles = [
    "roles/cloudsql.client",
    "roles/secretmanager.secretAccessor",
    "roles/logging.logWriter",
  ]

  ingestor_roles = [
    "roles/cloudsql.client",
    "roles/secretmanager.secretAccessor",
    "roles/logging.logWriter",
  ]
}

resource "google_project_iam_member" "api" {
  for_each = toset(local.api_roles)
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.api.email}"
}

resource "google_project_iam_member" "ingestor" {
  for_each = toset(local.ingestor_roles)
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.ingestor.email}"
}
