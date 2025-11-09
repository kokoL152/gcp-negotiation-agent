# Terraform for Cloud Run version

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
  credentials = "C:\\Users\\ladyc\\AppData\\Local\\Packages\\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\\LocalCache\\Roaming\\gcloud\\application_default_credentials.json"
}

variable "gcp_project_id" { type = string }
variable "gcp_region" { type = string }

# Create service account
resource "google_service_account" "cloud_run_sa" {
  account_id   = "cloud-run-sa"
  display_name = "Cloud Run service account for agent services"
}

# Grant Firestore readonly and logging writer
resource "google_project_iam_member" "sa_datastore_viewer" {
  project = var.gcp_project_id
  role    = "roles/datastore.viewer"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

resource "google_project_iam_member" "sa_logging_writer" {
  project = var.gcp_project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# Cloud Run service
resource "google_cloud_run_v2_service" "get_customer_data_func" {
  name     = "get-customer-data-func"
  location = var.gcp_region
  project  = var.gcp_project_id

  template {
    service_account = google_service_account.cloud_run_sa.email

    containers {
      image = "gcr.io/${var.gcp_project_id}/get-customer-data-func:final-fix"
      ports {
        container_port = 8080
      }
    }
  }

  ingress = "INGRESS_TRAFFIC_ALL"

  annotations = {
    "client/app-version-trigger" = data.local_file.app_py_hash.content_md5 # ⬅️ 新增
  }
}

# Make public
resource "google_cloud_run_v2_service_iam_member" "public_access_v2" {
  name  = google_cloud_run_v2_service.get_customer_data_func.name
  location = google_cloud_run_v2_service.get_customer_data_func.location
  project  = google_cloud_run_v2_service.get_customer_data_func.project
  role     = "roles/run.invoker"
  member   = "allUsers"
  depends_on = [google_cloud_run_v2_service.get_customer_data_func]
}

output "cloud_run_service_name" {
  value = google_cloud_run_v2_service.get_customer_data_func.name
}

output "cloud_run_service_location" {
  value = google_cloud_run_v2_service.get_customer_data_func.location
}
output "cloud_run_service_url" {
  description = "The publicly accessible URL of the deployed Cloud Run service."
  # Cloud Run v2 URL
  value = google_cloud_run_v2_service.get_customer_data_func.uri
}

data "local_file" "app_py_hash" {
  filename = "app.py" # 确保 app.py 在 Terraform 运行的目录下
}