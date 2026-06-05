resource "google_cloud_run_v2_job" "ingestor" {
  name     = "${local.name_prefix}-ingestor"
  location = var.region

  template {
    template {
      service_account = google_service_account.ingestor.email
      timeout         = "3600s"
      max_retries     = 1

      containers {
        image   = "gcr.io/cloudrun/hello" # placeholder; CI overwrites
        command = ["python"]
        args    = ["-m", "ingestor.main"]

        resources {
          limits = {
            cpu    = "1"
            memory = "512Mi"
          }
        }

        env {
          name  = "DB_INSTANCE_CONNECTION_NAME"
          value = google_sql_database_instance.main.connection_name
        }
        env {
          name  = "DB_USER"
          value = google_sql_user.app.name
        }
        env {
          name  = "DB_NAME"
          value = google_sql_database.app.name
        }
        env {
          name  = "CAPTURE_MINUTES"
          value = tostring(var.ingest_capture_minutes)
        }
        env {
          name  = "PH_BBOX"
          value = "4.5,116.5,21.5,127.0" # min_lat,min_lon,max_lat,max_lon
        }
        env {
          name = "DB_PASSWORD"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.db_password.secret_id
              version = "latest"
            }
          }
        }
        env {
          name = "AISSTREAM_API_KEY"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.aisstream_key.secret_id
              version = "latest"
            }
          }
        }
      }
    }
  }

  lifecycle {
    ignore_changes = [
      template[0].template[0].containers[0].image,
      client,
      client_version,
    ]
  }

  depends_on = [
    google_project_service.enabled,
    google_project_iam_member.ingestor,
  ]
}

resource "google_cloud_run_v2_job_iam_member" "ingestor_invoker" {
  project  = var.project_id
  location = google_cloud_run_v2_job.ingestor.location
  name     = google_cloud_run_v2_job.ingestor.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.scheduler.email}"
}
