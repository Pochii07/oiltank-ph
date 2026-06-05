resource "google_secret_manager_secret" "db_password" {
  secret_id = "${local.name_prefix}-db-password"

  replication {
    auto {}
  }

  labels = local.labels

  depends_on = [google_project_service.enabled]
}

resource "google_secret_manager_secret_version" "db_password" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = var.db_password
}

resource "google_secret_manager_secret" "aisstream_key" {
  secret_id = "${local.name_prefix}-aisstream-key"

  replication {
    auto {}
  }

  labels = local.labels

  depends_on = [google_project_service.enabled]
}

resource "google_secret_manager_secret_version" "aisstream_key" {
  secret      = google_secret_manager_secret.aisstream_key.id
  secret_data = var.aisstream_api_key
}
