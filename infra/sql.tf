resource "google_sql_database_instance" "main" {
  name             = "${local.name_prefix}-pg"
  database_version = "POSTGRES_15"
  region           = var.region

  deletion_protection = false

  settings {
    tier              = var.db_tier
    availability_type = "ZONAL"
    disk_size         = 10
    disk_type         = "PD_SSD"

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = false
      start_time                     = "03:00"
    }

    ip_configuration {
      ipv4_enabled = true
      ssl_mode     = "ENCRYPTED_ONLY"
    }

    user_labels = local.labels
  }

  depends_on = [google_project_service.enabled]
}

resource "google_sql_database" "app" {
  name     = "tankers"
  instance = google_sql_database_instance.main.name
}

resource "google_sql_user" "app" {
  name     = "tankers_app"
  instance = google_sql_database_instance.main.name
  password = var.db_password
}
