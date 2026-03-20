"""CLI command implementations."""

import json
import sys
from pathlib import Path

from .auth import resolve_token
from .client import KDriveClient
from .config import load_config, save_config, set_config_value


def _get_client(args) -> KDriveClient:
    token = resolve_token(getattr(args, "token", None))
    return KDriveClient(token)


def _resolve_drive_id(args, client: KDriveClient) -> int:
    if getattr(args, "drive", None):
        return int(args.drive)
    config = load_config()
    if config.get("default_drive_id"):
        return config["default_drive_id"]
    drives = client.list_drives()
    if not drives:
        print("No drives found. Check your account.", file=sys.stderr)
        sys.exit(1)
    return drives[0]["id"]


def _resolve_file_id(client: KDriveClient, drive_id: int, path_or_id: str | None) -> int:
    if path_or_id is None:
        return 1  # root
    if path_or_id.isdigit():
        return int(path_or_id)
    return client.resolve_path(drive_id, path_or_id)


def _format_size(size: int, is_dir: bool) -> str:
    if is_dir:
        return "     DIR"
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):7.1f}M"
    if size >= 1024:
        return f"{size / 1024:7.1f}K"
    return f"{size:7d}B"


# ── Commands ──────────────────────────────────────────────────────────

def cmd_configure(args):
    """Interactive setup: token provider and default drive."""
    print("kdrive-cli configuration\n")

    # Choose token provider
    print("Token provider options:")
    print("  [1] Environment variable (INFOMANIAK_TOKEN)")
    print("  [2] GCP Secret Manager")
    print("  [3] AWS Secrets Manager")
    print("  [4] Azure Key Vault")
    print("  [5] System keyring (macOS Keychain / Windows Credential Manager)")
    print("  [6] Enter token directly (stored in config file)")

    choice = input("\nSelect provider [1-6]: ").strip()

    config = load_config()

    if choice == "1":
        config["token_provider"] = {"type": "env"}
        print("Set INFOMANIAK_TOKEN in your shell profile.")

    elif choice == "2":
        project = input("GCP project ID: ").strip()
        secret = input("Secret name [INFOMANIAK_API_TOKEN]: ").strip() or "INFOMANIAK_API_TOKEN"
        account = input("gcloud account (optional, for local dev): ").strip() or None
        config["token_provider"] = {
            "type": "gcp", "project": project,
            "secret_name": secret, **({"account": account} if account else {}),
        }

    elif choice == "3":
        secret = input("Secret name [infomaniak-api-token]: ").strip() or "infomaniak-api-token"
        region = input("AWS region [eu-central-1]: ").strip() or "eu-central-1"
        config["token_provider"] = {"type": "aws", "secret_name": secret, "region": region}

    elif choice == "4":
        vault = input("Azure Key Vault URL: ").strip()
        secret = input("Secret name [infomaniak-api-token]: ").strip() or "infomaniak-api-token"
        config["token_provider"] = {"type": "azure", "vault_url": vault, "secret_name": secret}

    elif choice == "5":
        token_val = input("API token: ").strip()
        from .providers.keyring_provider import KeyringTokenProvider
        KeyringTokenProvider.store_token(token_val)
        config["token_provider"] = {"type": "keyring"}
        print("Token stored in system keyring.")

    elif choice == "6":
        config["token_provider"] = {"type": "env"}
        config["token"] = input("API token: ").strip()

    else:
        print("Invalid choice.", file=sys.stderr)
        sys.exit(1)

    # Verify token works
    token = resolve_token(None)
    client = KDriveClient(token)
    drives = client.list_drives()

    if drives:
        print(f"\nAuthenticated. Found {len(drives)} drive(s):")
        for i, d in enumerate(drives):
            print(f"  [{i}] {d['id']} - {d.get('name', 'unnamed')}")
        if len(drives) == 1:
            config["default_drive_id"] = drives[0]["id"]
            print(f"\nDefault drive: {drives[0]['id']}")
        else:
            idx = input("\nSelect default drive (number): ").strip()
            config["default_drive_id"] = drives[int(idx)]["id"]

    save_config(config)
    from .config import CONFIG_FILE
    print(f"\nConfig saved to {CONFIG_FILE}")


def cmd_drives(args):
    """List accessible drives."""
    client = _get_client(args)
    drives = client.list_drives()
    if not drives:
        print("No drives found.")
        return
    for d in drives:
        used = d.get("used_size", 0)
        total = d.get("size", 0)
        name = d.get("name", "unnamed")
        print(f"  {d['id']}  {name}  ({used / (1024**3):.1f} / {total / (1024**3):.1f} GB)")


def cmd_ls(args):
    """List files in a directory."""
    client = _get_client(args)
    drive_id = _resolve_drive_id(args, client)
    file_id = _resolve_file_id(client, drive_id, args.path)

    files = client.list_files(drive_id, file_id)
    if not files:
        print("(empty)")
        return
    for f in files:
        is_dir = f.get("type") == "dir"
        ftype = "d" if is_dir else "-"
        size_str = _format_size(f.get("size", 0), is_dir)
        print(f"  {ftype} {f['id']:>10}  {size_str}  {f.get('name', '?')}")


def cmd_mkdir(args):
    """Create a directory."""
    client = _get_client(args)
    drive_id = _resolve_drive_id(args, client)

    path = args.path.rstrip("/")
    if "/" in path:
        parent_path, dir_name = path.rsplit("/", 1)
        parent_id = client.resolve_path(drive_id, parent_path)
    else:
        parent_id = 1
        dir_name = path

    result = client.create_directory(drive_id, parent_id, dir_name)
    print(f"Created: {result.get('name', dir_name)} (id: {result.get('id', '?')})")


def cmd_upload(args):
    """Upload a file."""
    client = _get_client(args)
    drive_id = _resolve_drive_id(args, client)
    local_path = Path(args.local_file)

    if not local_path.exists():
        print(f"Error: {local_path} not found", file=sys.stderr)
        sys.exit(1)

    dir_id = int(args.remote_dir_id) if args.remote_dir_id else 1
    file_data = local_path.read_bytes()

    print(f"Uploading {local_path.name} ({len(file_data) / 1024:.1f} KB)...")
    result = client.upload_file(drive_id, dir_id, local_path.name, file_data)
    print(f"Uploaded: {result.get('name', local_path.name)} (id: {result.get('id', '?')})")


def cmd_download(args):
    """Download a file."""
    client = _get_client(args)
    drive_id = _resolve_drive_id(args, client)

    info = client.get_file(drive_id, int(args.file_id))
    file_name = info.get("name", f"file_{args.file_id}")

    local_path = Path(args.local_path) if args.local_path else Path(file_name)
    if local_path.is_dir():
        local_path = local_path / file_name

    print(f"Downloading {file_name}...")
    resp = client.download_file(drive_id, int(args.file_id))
    with open(local_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"Saved: {local_path} ({local_path.stat().st_size / 1024:.1f} KB)")


def cmd_info(args):
    """Get file/folder details as JSON."""
    client = _get_client(args)
    drive_id = _resolve_drive_id(args, client)
    data = client.get_file(drive_id, int(args.file_id), with_extra="path,capabilities")
    print(json.dumps(data, indent=2))


def cmd_search(args):
    """Search files by name."""
    client = _get_client(args)
    drive_id = _resolve_drive_id(args, client)
    files = client.search(drive_id, args.query)
    if not files:
        print("No results.")
        return
    for f in files:
        ftype = "d" if f.get("type") == "dir" else "-"
        print(f"  {ftype} {f['id']:>10}  {f.get('name', '?')}")


def cmd_rm(args):
    """Move a file/folder to trash."""
    client = _get_client(args)
    drive_id = _resolve_drive_id(args, client)
    file_id = _resolve_file_id(client, drive_id, args.target)
    client.trash_file(drive_id, file_id)
    print(f"Trashed: {args.target}")
