terraform {
  required_version = ">= 1.6"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  name_prefix = "oiltank-ph"

  labels = {
    project     = "oil-tanker-ph"
    environment = var.environment
    managed_by  = "terraform"
  }
}
