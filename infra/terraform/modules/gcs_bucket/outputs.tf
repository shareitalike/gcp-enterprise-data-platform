output "bucket_name" {
  description = "The name of the created GCS bucket."
  value       = google_storage_bucket.this.name
}

output "bucket_url" {
  description = "The gs:// URL of the created bucket."
  value       = "gs://${google_storage_bucket.this.name}"
}

output "bucket_self_link" {
  description = "Self-link URI of the bucket."
  value       = google_storage_bucket.this.self_link
}
