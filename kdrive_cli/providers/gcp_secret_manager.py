"""GCP Secret Manager token provider."""

import shutil
import subprocess

from .base import TokenProvider


class GCPSecretManagerProvider(TokenProvider):
    """Fetch token from Google Cloud Secret Manager.

    Tries the gcloud CLI first (works with any authenticated account),
    then falls back to the Python client library (works on GCE/Cloud Run).
    """

    def __init__(self, project: str, secret_name: str = "INFOMANIAK_API_TOKEN", account: str | None = None):
        self.project = project
        self.secret_name = secret_name
        self.account = account

    def get_token(self) -> str | None:
        return self._try_gcloud_cli() or self._try_client_library()

    def _try_gcloud_cli(self) -> str | None:
        if not shutil.which("gcloud"):
            return None
        try:
            cmd = [
                "gcloud", "secrets", "versions", "access", "latest",
                "--secret", self.secret_name,
                "--project", self.project,
            ]
            if self.account:
                cmd += ["--account", self.account]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            pass
        return None

    def _try_client_library(self) -> str | None:
        try:
            from google.cloud import secretmanager
            client = secretmanager.SecretManagerServiceClient()
            name = f"projects/{self.project}/secrets/{self.secret_name}/versions/latest"
            response = client.access_secret_version(request={"name": name})
            return response.payload.data.decode("UTF-8").strip()
        except Exception:
            return None
