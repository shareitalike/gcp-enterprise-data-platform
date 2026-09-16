"""
secrets.py — Utility for reading secrets from Google Secret Manager at runtime.

Why Secret Manager instead of environment variables or config files?
- Environment variables can be accidentally logged or exposed in stack traces.
- Config files get accidentally committed to Git.
- Secret Manager provides audit logs of every access, version history,
  automatic rotation, and fine-grained IAM controls.

Usage:
    from ingestion.utils.secrets import get_secret

    api_key = get_secret(
        secret_id="my-api-key",
        project_id="commerce360-analytics-dev-alvi"
    )
"""
import logging
from google.cloud import secretmanager

logger = logging.getLogger(__name__)


def get_secret(secret_id: str, project_id: str, version: str = "latest") -> str:
    """Fetches the value of a secret from Google Secret Manager.

    Args:
        secret_id: The ID of the secret (not the full resource name).
                   Example: 'my-database-password'
        project_id: The GCP project that owns the secret.
        version: The version of the secret to fetch. Defaults to 'latest'.
                 In production, pin to a specific version number for reproducibility.

    Returns:
        The decoded string value of the secret.

    Raises:
        google.api_core.exceptions.NotFound: If the secret or version does not exist.
        google.api_core.exceptions.PermissionDenied: If the SA lacks secretmanager.versions.access.

    Example:
        # The calling service account must have roles/secretmanager.secretAccessor
        password = get_secret("bq-api-key", "commerce360-analytics-dev-alvi")
    """
    client = secretmanager.SecretManagerServiceClient()

    # Build the full resource path
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version}"

    logger.info(f"Fetching secret: {secret_id} (version: {version})")

    response = client.access_secret_version(request={"name": name})

    # Decode bytes to string
    payload = response.payload.data.decode("utf-8")

    return payload
