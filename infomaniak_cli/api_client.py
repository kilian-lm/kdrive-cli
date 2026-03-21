"""Shared Infomaniak API client used by all CLI command groups."""

import json
import sys

import requests

API_BASE = "https://api.infomaniak.com"
KCHAT_API_BASE = "https://{team_slug}.kchat.infomaniak.com/api/v4"


class InfomaniakClient:
    """Low-level HTTP client for the Infomaniak REST API."""

    def __init__(self, token: str):
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        })
        self._account_id: int | None = None
        self._profile: dict | None = None

    def request(self, method: str, path: str, *, base_url: str = API_BASE,
                params=None, json_body=None, data=None, headers=None,
                stream=False) -> dict | requests.Response:
        url = f"{base_url}{path}" if not path.startswith("http") else path
        resp = self.session.request(
            method, url, params=params, json=json_body,
            data=data, headers=headers, stream=stream,
            timeout=60,
        )
        if stream and resp.status_code == 200:
            return resp
        try:
            body = resp.json()
        except ValueError:
            body = {"raw": resp.text}
        if resp.status_code >= 400:
            err = body.get("error", {})
            code = err.get("code", resp.status_code)
            desc = err.get("description", err.get("message", resp.text[:300]))
            raise APIError(code, desc, resp.status_code)
        return body

    def get(self, path: str, **kwargs):
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs):
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs):
        return self.request("PUT", path, **kwargs)

    def patch(self, path: str, **kwargs):
        return self.request("PATCH", path, **kwargs)

    def delete(self, path: str, **kwargs):
        return self.request("DELETE", path, **kwargs)

    # ── Convenience ──

    @property
    def account_id(self) -> int:
        if self._account_id is None:
            body = self.get("/1/accounts")
            accounts = body.get("data", [])
            if not accounts:
                print("Error: No Infomaniak accounts found.", file=sys.stderr)
                sys.exit(1)
            self._account_id = accounts[0]["id"]
        return self._account_id

    @property
    def profile(self) -> dict:
        if self._profile is None:
            self._profile = self.get("/2/profile").get("data", {})
        return self._profile


class APIError(RuntimeError):
    def __init__(self, code, description, http_status=None):
        self.code = code
        self.description = description
        self.http_status = http_status
        super().__init__(f"API Error ({code}): {description}")
