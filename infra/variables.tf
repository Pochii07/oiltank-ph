variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "Primary region for all regional resources"
  type        = string
  default     = "asia-southeast1"
}

variable "environment" {
  description = "Environment label (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "db_tier" {
  description = "Cloud SQL machine tier"
  type        = string
  default     = "db-f1-micro"
}

variable "db_password" {
  description = "Initial app DB user password (stored in Secret Manager)"
  type        = string
  sensitive   = true
}

variable "aisstream_api_key" {
  description = "AISStream.io API key (stored in Secret Manager)"
  type        = string
  sensitive   = true
}

variable "frontend_origin" {
  description = "Allowed CORS origin for the React frontend (e.g. https://user.github.io)"
  type        = string
}

variable "ingest_schedule_cron" {
  description = "Cron expression for the daily ingestion job"
  type        = string
  default     = "0 2 * * *" # 02:00 UTC daily (10:00 PHT)
}

variable "ingest_capture_minutes" {
  description = "How long the ingestor listens to AISStream per run"
  type        = number
  default     = 45
}
