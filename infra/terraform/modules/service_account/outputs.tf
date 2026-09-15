output "email" {
  description = "Full service account email address."
  value       = google_service_account.this.email
}

output "unique_id" {
  description = "Unique ID of the service account."
  value       = google_service_account.this.unique_id
}

output "member" {
  description = "IAM member string: serviceAccount:<email>"
  value       = "serviceAccount:${google_service_account.this.email}"
}
