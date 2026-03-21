"""Infomaniak kDrive API client."""

import sys

import requests

API_BASE = "https://api.infomaniak.com"


class KDriveClient:
    """Low-level HTTP client for the Infomaniak kDrive API."""

    def __init__(self, token: str):
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        })
        self._account_id: int | None = None

    def request(self, method: str, path: str, params=None, json_body=None,
                data=None, headers=None, stream=False):
        url = f"{API_BASE}{path}"
        resp = self.session.request(
            method, url, params=params, json=json_body,
            data=data, headers=headers, stream=stream,
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
            desc = err.get("description", resp.text[:200])
            raise RuntimeError(f"API Error ({code}): {desc}")
        return body

    @property
    def account_id(self) -> int:
        if self._account_id is None:
            body = self.request("GET", "/1/accounts")
            accounts = body.get("data", [])
            if not accounts:
                print("Error: No Infomaniak accounts found.", file=sys.stderr)
                sys.exit(1)
            self._account_id = accounts[0]["id"]
        return self._account_id

    def list_drives(self) -> list[dict]:
        body = self.request("GET", "/2/drive", params={"account_id": self.account_id})
        return body.get("data", [])

    def get_drive(self, drive_id: int) -> dict:
        body = self.request("GET", f"/2/drive/{drive_id}")
        return body.get("data", {})

    def list_files(self, drive_id: int, directory_id: int = 1,
                   order_by: str = "name", order_dir: str = "asc") -> list[dict]:
        all_files = []
        cursor = None
        while True:
            params = {"order_by": order_by, "order_direction": order_dir}
            if cursor:
                params["cursor"] = cursor
            body = self.request(
                "GET", f"/3/drive/{drive_id}/files/{directory_id}/files",
                params=params,
            )
            all_files.extend(body.get("data", []))
            if not body.get("has_more", False):
                break
            cursor = body.get("cursor")
            if not cursor:
                break
        return all_files

    def get_file(self, drive_id: int, file_id: int, with_extra: str | None = None) -> dict:
        params = {}
        if with_extra:
            params["with"] = with_extra
        body = self.request("GET", f"/3/drive/{drive_id}/files/{file_id}", params=params)
        return body.get("data", {})

    def create_directory(self, drive_id: int, parent_id: int, name: str) -> dict:
        body = self.request(
            "POST", f"/3/drive/{drive_id}/files/{parent_id}/directory",
            json_body={"name": name},
        )
        return body.get("data", {})

    def upload_file(self, drive_id: int, directory_id: int, file_name: str,
                    file_data: bytes, conflict: str = "rename") -> dict:
        body = self.request(
            "POST", f"/3/drive/{drive_id}/upload",
            params={
                "directory_id": directory_id,
                "file_name": file_name,
                "total_size": len(file_data),
                "conflict": conflict,
            },
            data=file_data,
            headers={"Content-Type": "application/octet-stream"},
        )
        return body.get("data", {})

    def download_file(self, drive_id: int, file_id: int):
        return self.request("GET", f"/2/drive/{drive_id}/files/{file_id}/download", stream=True)

    def search(self, drive_id: int, query: str) -> list[dict]:
        body = self.request(
            "GET", f"/3/drive/{drive_id}/files/search",
            params={"query": query},
        )
        return body.get("data", [])

    def trash_file(self, drive_id: int, file_id: int) -> dict:
        body = self.request("DELETE", f"/2/drive/{drive_id}/files/{file_id}")
        return body.get("data", {})

    def resolve_path(self, drive_id: int, path: str) -> int:
        """Walk a path like 'Documents/Photos' and return the final file_id."""
        parts = [p for p in path.strip("/").split("/") if p]
        current_id = 1
        for part in parts:
            files = self.list_files(drive_id, current_id)
            match = next((f for f in files if f.get("name") == part), None)
            if not match:
                print(f"Error: '{part}' not found in directory {current_id}", file=sys.stderr)
                sys.exit(1)
            current_id = match["id"]
        return current_id
