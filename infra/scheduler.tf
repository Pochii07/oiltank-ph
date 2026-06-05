resource "google_cloud_scheduler_job" "daily_ingest" {
  name        = "${local.name_prefix}-daily-ingest"
  description = "Triggers the daily AIS ingestion job"
  schedule    = var.ingest_schedule_cron
  time_zone   = "Etc/UTC"
  region      = var.region

  retry_config {
    retry_count = 1
  }

  http_target {
    http_method = "POST"
    uri         = "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_id}/jobs/${google_cloud_run_v2_job.ingestor.name}:run"

    oauth_token {
      service_account_email = google_service_account.scheduler.email
    }
  }

  depends_on = [
    google_project_service.enabled,
    google_cloud_run_v2_job_iam_member.ingestor_invoker,
  ]
}
