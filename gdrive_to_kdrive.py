#!/usr/bin/env python3
"""
Copy files from a Google Drive folder to Infomaniak kDrive.

Uses:
  - Google service account with domain-wide delegation (Drive scope)
  - Infomaniak kDrive API token (via kdrive-cli's pluggable auth)

Prerequisites:
  - A Google service account with domain-wide delegation for drive scope
  - The SA credentials stored in a secret manager (GCP, AWS, Azure) or env var
  - An Infomaniak API token configured via `kdrive configure`

Usage:
    python gdrive_to_kdrive.py \\
        --gdrive-folder FOLDER_ID \\
        --user user@yourdomain.com \\
        --sa-secret MY_SA_SECRET \\
        --gcp-project my-project

Environment variables:
    GOOGLE_SA_JSON    - inline JSON of the service account key (alternative to secret manager)
    GOOGLE_SA_FILE    - path to a local service account JSON file (alternative to secret manager)
"""

import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import time

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from kdrive_cli.auth import resolve_token
from kdrive_cli.client import KDriveClient
from kdrive_cli.config import load_config

# Google Workspace export MIME mappings for native docs
EXPORT_MIMES = {
    "application/vnd.google-apps.document": ("application/pdf", ".pdf"),
    "application/vnd.google-apps.spreadsheet": (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".xlsx"),
    "application/vnd.google-apps.presentation": (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation", ".pptx"),
    "application/vnd.google-apps.drawing": ("application/pdf", ".pdf"),
    "application/vnd.google-apps.jam": ("application/pdf", ".pdf"),
}

# Google types that cannot be downloaded
SKIP_MIMES = {
    "application/vnd.google-apps.form",
    "application/vnd.google-apps.map",
    "application/vnd.google-apps.site",
    "application/vnd.google-apps.script",
    "application/vnd.google-apps.shortcut",
}

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]


def _load_sa_from_secret_manager(secret_name: str, project: str, account: str | None = None) -> dict:
    """Load a service account JSON from GCP Secret Manager."""
    if shutil.which("gcloud"):
        cmd = [
            "gcloud", "secrets", "versions", "access", "latest",
            "--secret", secret_name, "--project", project,
        ]
        if account:
            cmd += ["--account", account]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
    # Fallback: client library (GCE/Cloud Run)
    try:
        from google.cloud import secretmanager
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project}/secrets/{secret_name}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return json.loads(response.payload.data.decode("UTF-8"))
    except Exception as e:
        raise RuntimeError(f"Could not load secret '{secret_name}' from project '{project}': {e}")


def _load_sa_credentials() -> dict:
    """Load service account credentials from env or file."""
    sa_json = os.environ.get("GOOGLE_SA_JSON")
    if sa_json:
        return json.loads(sa_json)
    sa_file = os.environ.get("GOOGLE_SA_FILE")
    if sa_file and os.path.exists(sa_file):
        with open(sa_file) as f:
            return json.load(f)
    return {}


def get_drive_service(user: str, sa_secret: str | None = None,
                      gcp_project: str | None = None, gcp_account: str | None = None):
    """Build Google Drive service with domain-wide delegation.

    Credential sources (tried in order):
      1. GOOGLE_SA_JSON env var (inline JSON)
      2. GOOGLE_SA_FILE env var (file path)
      3. GCP Secret Manager (--sa-secret / --gcp-project)
    """
    sa_info = _load_sa_credentials()
    if not sa_info and sa_secret and gcp_project:
        sa_info = _load_sa_from_secret_manager(sa_secret, gcp_project, gcp_account)
    if not sa_info:
        print("Error: No Google service account credentials found.", file=sys.stderr)
        print("Provide via: GOOGLE_SA_JSON env, GOOGLE_SA_FILE env, or --sa-secret + --gcp-project", file=sys.stderr)
        sys.exit(1)

    creds = service_account.Credentials.from_service_account_info(sa_info, scopes=DRIVE_SCOPES)
    creds = creds.with_subject(user)
    return build("drive", "v3", credentials=creds)


def list_folder(drive_svc, folder_id: str) -> list[dict]:
    """List all files in a Google Drive folder (handles pagination)."""
    all_files = []
    page_token = None
    while True:
        resp = drive_svc.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            fields="nextPageToken, files(id, name, mimeType, size, modifiedTime)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            pageSize=1000,
            pageToken=page_token,
        ).execute()
        all_files.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return all_files


def download_file(drive_svc, file_info: dict) -> tuple[bytes, str]:
    """Download a file from Google Drive. Returns (data, filename)."""
    file_id = file_info["id"]
    name = file_info["name"]
    mime = file_info["mimeType"]

    if mime in EXPORT_MIMES:
        export_mime, ext = EXPORT_MIMES[mime]
        if not name.endswith(ext):
            name += ext
        request = drive_svc.files().export_media(fileId=file_id, mimeType=export_mime)
    else:
        request = drive_svc.files().get_media(fileId=file_id, supportsAllDrives=True)

    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buf.getvalue(), name


def copy_folder_recursive(drive_svc, kdrive: KDriveClient, kdrive_id: int,
                          gdrive_folder_id: str, kdrive_parent_id: int,
                          path: str = "", stats: dict | None = None):
    """Recursively copy a Google Drive folder to kDrive."""
    if stats is None:
        stats = {"files": 0, "dirs": 0, "skipped": 0, "errors": 0, "bytes": 0}

    items = list_folder(drive_svc, gdrive_folder_id)
    folders = [f for f in items if f["mimeType"] == "application/vnd.google-apps.folder"]
    files = [f for f in items if f["mimeType"] != "application/vnd.google-apps.folder"]

    for f in files:
        display = f"{path}/{f['name']}" if path else f["name"]

        if f["mimeType"] in SKIP_MIMES:
            print(f"  SKIP  {display}  ({f['mimeType']})")
            stats["skipped"] += 1
            continue

        try:
            data, filename = download_file(drive_svc, f)
            size_kb = len(data) / 1024

            if len(data) > 1_000_000_000:
                print(f"  SKIP  {display}  (> 1GB, chunked upload not yet supported)")
                stats["skipped"] += 1
                continue

            kdrive.upload_file(kdrive_id, kdrive_parent_id, filename, data, conflict="rename")
            stats["files"] += 1
            stats["bytes"] += len(data)
            print(f"  OK    {display}  ({size_kb:.0f} KB)")

        except Exception as e:
            print(f"  ERR   {display}  ({e})")
            stats["errors"] += 1

        time.sleep(0.3)

    for folder in folders:
        folder_name = folder["name"]
        display = f"{path}/{folder_name}" if path else folder_name
        print(f"  DIR   {display}/")

        try:
            new_dir = kdrive.create_directory(kdrive_id, kdrive_parent_id, folder_name)
            new_dir_id = new_dir["id"]
            stats["dirs"] += 1
        except Exception as e:
            print(f"  ERR   Could not create {display}: {e}")
            stats["errors"] += 1
            continue

        copy_folder_recursive(
            drive_svc, kdrive, kdrive_id,
            folder["id"], new_dir_id,
            path=display, stats=stats,
        )

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Copy a Google Drive folder to Infomaniak kDrive",
        epilog="Credentials: Google SA via GOOGLE_SA_JSON/GOOGLE_SA_FILE env or "
               "--sa-secret + --gcp-project. kDrive token via kdrive-cli config.",
    )
    parser.add_argument("--gdrive-folder", required=True, help="Google Drive folder ID")
    parser.add_argument("--user", required=True, help="Google Workspace user to impersonate")
    parser.add_argument("--sa-secret", help="GCP Secret Manager secret name for the Google SA key")
    parser.add_argument("--gcp-project", help="GCP project ID for Secret Manager")
    parser.add_argument("--gcp-account", help="gcloud account for Secret Manager access (local dev)")
    parser.add_argument("--kdrive-dir", help="kDrive destination directory ID")
    parser.add_argument("--kdrive-folder-name", help="Create a new folder with this name on kDrive")
    parser.add_argument("--token", help="Infomaniak API token (overrides kdrive-cli config)")
    args = parser.parse_args()

    # Google Drive
    print(f"Connecting to Google Drive as {args.user}...")
    drive_svc = get_drive_service(args.user, args.sa_secret, args.gcp_project, args.gcp_account)

    try:
        folder_info = drive_svc.files().get(
            fileId=args.gdrive_folder, fields="id,name,mimeType", supportsAllDrives=True,
        ).execute()
        print(f"Source: {folder_info.get('name', args.gdrive_folder)}")
    except Exception as e:
        print(f"Error accessing Google Drive folder: {e}", file=sys.stderr)
        sys.exit(1)

    # kDrive
    token = resolve_token(args.token)
    kdrive = KDriveClient(token)
    config = load_config()
    kdrive_id = config.get("default_drive_id") or kdrive.list_drives()[0]["id"]

    if args.kdrive_folder_name:
        parent_id = int(args.kdrive_dir) if args.kdrive_dir else 1
        dest = kdrive.create_directory(kdrive_id, parent_id, args.kdrive_folder_name)
        dest_id = dest["id"]
        print(f"Destination: kDrive /{args.kdrive_folder_name}/ (id: {dest_id})")
    elif args.kdrive_dir:
        dest_id = int(args.kdrive_dir)
        print(f"Destination: kDrive dir {dest_id}")
    else:
        source_name = folder_info.get("name", "Google Drive Import")
        # Try Private space (id=5) first, fall back to root
        try:
            dest = kdrive.create_directory(kdrive_id, 5, source_name)
        except SystemExit:
            dest = kdrive.create_directory(kdrive_id, 1, source_name)
        dest_id = dest["id"]
        print(f"Destination: kDrive /{source_name}/ (id: {dest_id})")

    print("\nStarting copy...\n")
    stats = copy_folder_recursive(drive_svc, kdrive, kdrive_id, args.gdrive_folder, dest_id)

    print(f"\nDone!")
    print(f"  Files:   {stats['files']} ({stats['bytes'] / (1024 * 1024):.1f} MB)")
    print(f"  Folders: {stats['dirs']}")
    print(f"  Skipped: {stats['skipped']}")
    print(f"  Errors:  {stats['errors']}")


if __name__ == "__main__":
    main()
