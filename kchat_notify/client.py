"""kChat incoming webhook client.

Sends messages to a kChat channel via an incoming webhook URL.
Incoming webhooks are Mattermost-compatible (Slack-like format).

Setup:
    1. Open kChat in browser → Integrations → Incoming Webhooks
    2. Create a new webhook, pick a channel
    3. Copy the webhook URL (https://kchat.infomaniak.com/hooks/xxx)
    4. Store it in GCP Secret Manager or pass directly

Usage:
    from kchat_notify import KChatNotifier

    notifier = KChatNotifier.from_config()  # loads webhook URL from config/secrets
    notifier.send("Migration started!")
    notifier.send_rich("Migration Complete", fields={"Files": "42", "Errors": "0"})
"""

import json
import os
import sys

import requests


class KChatNotifier:
    """Send messages to kChat via incoming webhook."""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    @classmethod
    def from_config(cls, webhook_url: str | None = None) -> "KChatNotifier":
        """Resolve webhook URL from explicit value, env, or GCP Secret Manager."""
        url = webhook_url or os.environ.get("KCHAT_WEBHOOK_URL")
        if url:
            return cls(url)

        # Try config file
        try:
            from kdrive_cli.config import load_config
            config = load_config()
            kchat_config = config.get("kchat", {})
            url = kchat_config.get("webhook_url")
            if url:
                return cls(url)

            # Try GCP Secret Manager
            if kchat_config.get("webhook_secret"):
                url = _resolve_from_gcp(
                    project=kchat_config.get("project", config.get("token_provider", {}).get("project")),
                    secret_name=kchat_config["webhook_secret"],
                    account=kchat_config.get("account", config.get("token_provider", {}).get("account")),
                )
                if url:
                    return cls(url)
        except ImportError:
            pass

        # Try GCP with default secret name from env
        gcp_project = os.environ.get("GCP_PROJECT")
        if gcp_project:
            try:
                url = _resolve_from_gcp(gcp_project, "KCHAT_WEBHOOK_URL")
                if url:
                    return cls(url)
            except Exception:
                pass

        raise ValueError(
            "No kChat webhook URL found. Set KCHAT_WEBHOOK_URL env var, "
            "pass webhook_url, or configure in kdrive-cli config."
        )

    def send(self, text: str, username: str | None = None, icon_url: str | None = None) -> bool:
        """Send a simple text message."""
        payload = {"text": text}
        if username:
            payload["username"] = username
        if icon_url:
            payload["icon_url"] = icon_url
        return self._post(payload)

    def send_rich(self, title: str, text: str = "", fields: dict[str, str] | None = None,
                  color: str = "#0076D1", username: str | None = None) -> bool:
        """Send a rich message with Mattermost attachment formatting."""
        attachment = {"title": title, "color": color}
        if text:
            attachment["text"] = text
        if fields:
            attachment["fields"] = [
                {"short": True, "title": k, "value": v} for k, v in fields.items()
            ]
        payload = {"attachments": [attachment]}
        if username:
            payload["username"] = username
        return self._post(payload)

    def _post(self, payload: dict) -> bool:
        try:
            resp = self.session.post(self.webhook_url, json=payload, timeout=10)
            if resp.status_code not in (200, 201):
                print(f"kChat webhook error ({resp.status_code}): {resp.text[:200]}", file=sys.stderr)
                return False
            return True
        except Exception as e:
            print(f"kChat webhook failed: {e}", file=sys.stderr)
            return False


def _resolve_from_gcp(project: str, secret_name: str, account: str | None = None) -> str | None:
    """Load a secret value from GCP Secret Manager."""
    import shutil
    import subprocess
    if not shutil.which("gcloud"):
        return None
    cmd = ["gcloud", "secrets", "versions", "access", "latest",
           "--secret", secret_name, "--project", project]
    if account:
        cmd += ["--account", account]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    return None
