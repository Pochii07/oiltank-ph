output "api_url" {
  description = "Public URL of the API Cloud Run service"
  value       = google_cloud_run_v2_service.api.uri
}

output "ingestor_job_name" {
  description = "Cloud Run Job name (used by `gcloud run jobs execute`)"
  value       = google_cloud_run_v2_job.ingestor.name
}

output "db_connection_name" {
  description = "Cloud SQL instance connection name (PROJECT:REGION:INSTANCE)"
  value       = google_sql_database_instance.main.connection_name
}

output "artifact_repo_url" {
  description = "Artifact Registry Docker repository URL"
  value       = local.artifact_repo_url
}

output "service_accounts" {
  description = "Service account emails"
  value = {
    api       = google_service_account.api.email
    ingestor  = google_service_account.ingestor.email
    scheduler = google_service_account.scheduler.email
  }
}
