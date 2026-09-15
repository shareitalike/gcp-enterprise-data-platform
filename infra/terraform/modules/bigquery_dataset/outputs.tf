output "dataset_id" {
  description = "BigQuery dataset ID."
  value       = google_bigquery_dataset.this.dataset_id
}

output "dataset_self_link" {
  description = "Self-link URI of the dataset."
  value       = google_bigquery_dataset.this.self_link
}

output "dataset_project" {
  description = "Project ID that owns the dataset."
  value       = google_bigquery_dataset.this.project
}
