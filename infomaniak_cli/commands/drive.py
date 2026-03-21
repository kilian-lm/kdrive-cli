"""kDrive commands — file and folder management."""

import json
import sys
from pathlib import Path

from ..api_client import InfomaniakClient

# Re-use config for default drive ID
from kdrive_cli.config import load_config


def register(sub):
    """Register drive subcommands."""
    drive = sub.add_parser("drive", help="manage kDrive files, folders, and shares")
    ds = drive.add_subparsers(dest="subcommand")

    # ── list / info ──
    ds.add_parser("list", help="list accessible drives")

    p = ds.add_parser("show", help="show drive details")
    p.add_argument("drive_id", nargs="?", help="drive ID (default: configured)")

    p = ds.add_parser("stats", help="show drive statistics")
    p.add_argument("--drive", help="drive ID")

    p = ds.add_parser("settings", help="show drive settings")
    p.add_argument("--drive", help="drive ID")

    p = ds.add_parser("users", help="list drive users")
    p.add_argument("--drive", help="drive ID")

    p = ds.add_parser("activities", help="recent drive activities")
    p.add_argument("--drive", help="drive ID")
    p.add_argument("--limit", type=int, default=20, help="max results")

    # ── files ──
    p = ds.add_parser("ls", help="list directory contents")
    p.add_argument("path", nargs="?", help="directory ID or path (default: root)")
    p.add_argument("--drive", help="drive ID")
    p.add_argument("--json", action="store_true", dest="as_json", help="output as JSON")

    p = ds.add_parser("info", help="file/folder details")
    p.add_argument("target", help="file ID or path")
    p.add_argument("--drive", help="drive ID")

    p = ds.add_parser("tree", help="show directory tree")
    p.add_argument("path", nargs="?", help="directory ID or path (default: root)")
    p.add_argument("--drive", help="drive ID")
    p.add_argument("--depth", type=int, default=3, help="max depth (default: 3)")

    p = ds.add_parser("mkdir", help="create directory")
    p.add_argument("path", help="path to create (e.g. Documents/new-folder)")
    p.add_argument("--drive", help="drive ID")

    p = ds.add_parser("upload", help="upload a file")
    p.add_argument("local_file", help="local file path")
    p.add_argument("remote_dir", nargs="?", help="target directory ID or path")
    p.add_argument("--drive", help="drive ID")
    p.add_argument("--conflict", choices=["rename", "version", "error"], default="rename")

    p = ds.add_parser("download", help="download a file")
    p.add_argument("target", help="file ID or path")
    p.add_argument("local_path", nargs="?", help="local save path")
    p.add_argument("--drive", help="drive ID")

    p = ds.add_parser("search", help="search files by name")
    p.add_argument("query", help="search query")
    p.add_argument("--drive", help="drive ID")
    p.add_argument("--type", choices=["file", "dir"], dest="ftype", help="filter by type")

    p = ds.add_parser("mv", help="move file/folder")
    p.add_argument("source", help="file ID or path")
    p.add_argument("destination", help="destination directory ID or path")
    p.add_argument("--drive", help="drive ID")

    p = ds.add_parser("cp", help="copy file/folder")
    p.add_argument("source", help="file ID or path")
    p.add_argument("destination", help="destination directory ID or path")
    p.add_argument("--drive", help="drive ID")

    p = ds.add_parser("rename", help="rename a file/folder")
    p.add_argument("target", help="file ID or path")
    p.add_argument("new_name", help="new name")
    p.add_argument("--drive", help="drive ID")

    p = ds.add_parser("rm", help="move file/folder to trash")
    p.add_argument("target", help="file ID or path")
    p.add_argument("--drive", help="drive ID")

    p = ds.add_parser("hash", help="get file hash")
    p.add_argument("target", help="file ID or path")
    p.add_argument("--drive", help="drive ID")

    # ── trash ──
    p = ds.add_parser("trash", help="list or manage trash")
    p.add_argument("action", nargs="?", choices=["list", "empty", "restore", "count"],
                   default="list", help="trash action")
    p.add_argument("file_id", nargs="?", help="file ID (for restore)")
    p.add_argument("--drive", help="drive ID")

    # ── sharing ──
    p = ds.add_parser("share", help="manage share links")
    p.add_argument("action", choices=["create", "show", "delete", "list"])
    p.add_argument("target", nargs="?", help="file ID or path")
    p.add_argument("--drive", help="drive ID")

    # ── favorites ──
    p = ds.add_parser("favorites", help="list favorite files")
    p.add_argument("--drive", help="drive ID")

    p = ds.add_parser("fav", help="toggle favorite on a file")
    p.add_argument("target", help="file ID or path")
    p.add_argument("--remove", action="store_true", help="unfavorite")
    p.add_argument("--drive", help="drive ID")

    # ── categories ──
    p = ds.add_parser("categories", help="list or manage categories/tags")
    p.add_argument("action", nargs="?", choices=["list", "create", "delete"], default="list")
    p.add_argument("--name", help="category name (for create)")
    p.add_argument("--color", help="hex color (for create)")
    p.add_argument("--id", dest="cat_id", help="category ID (for delete)")
    p.add_argument("--drive", help="drive ID")

    # ── versions ──
    p = ds.add_parser("versions", help="list file versions")
    p.add_argument("target", help="file ID or path")
    p.add_argument("--drive", help="drive ID")


def dispatch(args, client: InfomaniakClient):
    sub = getattr(args, "subcommand", None)
    if sub is None:
        print("Usage: infomaniak drive <subcommand>")
        print("Run 'infomaniak drive --help' for details.")
        return

    did = _drive_id(args, client)

    handlers = {
        "list": _list_drives, "show": _show_drive, "stats": _stats,
        "settings": _settings, "users": _users, "activities": _activities,
        "ls": _ls, "info": _info, "tree": _tree,
        "mkdir": _mkdir, "upload": _upload, "download": _download,
        "search": _search, "mv": _mv, "cp": _cp, "rename": _rename,
        "rm": _rm, "hash": _hash, "trash": _trash,
        "share": _share, "favorites": _favorites, "fav": _fav,
        "categories": _categories, "versions": _versions,
    }
    fn = handlers.get(sub)
    if fn:
        fn(args, client, did)
    else:
        print(f"Unknown drive subcommand: {sub}")


def _drive_id(args, client: InfomaniakClient) -> int:
    if getattr(args, "drive", None):
        return int(args.drive)
    config = load_config()
    if config.get("default_drive_id"):
        return config["default_drive_id"]
    body = client.get("/2/drive", params={"account_id": client.account_id})
    drives = body.get("data", [])
    if not drives:
        print("No drives found.", file=sys.stderr)
        sys.exit(1)
    return drives[0]["id"]


def _resolve(client: InfomaniakClient, did: int, path_or_id: str | None) -> int:
    if path_or_id is None:
        return 1
    if path_or_id.isdigit():
        return int(path_or_id)
    parts = [p for p in path_or_id.strip("/").split("/") if p]
    current_id = 1
    for part in parts:
        body = client.get(f"/3/drive/{did}/files/{current_id}/files")
        files = body.get("data", [])
        match = next((f for f in files if f.get("name") == part), None)
        if not match:
            print(f"Error: '{part}' not found in directory {current_id}", file=sys.stderr)
            sys.exit(1)
        current_id = match["id"]
    return current_id


def _fmt_size(size: int, is_dir: bool) -> str:
    if is_dir:
        return "     DIR"
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):7.1f}M"
    if size >= 1024:
        return f"{size / 1024:7.1f}K"
    return f"{size:7d}B"


def _paginate_files(client, did, dir_id, params=None):
    all_files = []
    cursor = None
    while True:
        p = dict(params or {})
        if cursor:
            p["cursor"] = cursor
        body = client.get(f"/3/drive/{did}/files/{dir_id}/files", params=p)
        all_files.extend(body.get("data", []))
        if not body.get("has_more", False):
            break
        cursor = body.get("cursor")
        if not cursor:
            break
    return all_files


# ── Handlers ──

def _list_drives(args, client, did):
    body = client.get("/2/drive", params={"account_id": client.account_id})
    for d in body.get("data", []):
        used = d.get("used_size", 0)
        total = d.get("size", 0)
        name = d.get("name", "unnamed")
        print(f"  {d['id']:>10}  {name:30s}  {used / (1024**3):.1f} / {total / (1024**3):.1f} GB")


def _show_drive(args, client, did):
    d_id = int(args.drive_id) if getattr(args, "drive_id", None) else did
    data = client.get(f"/2/drive/{d_id}").get("data", {})
    print(json.dumps(data, indent=2))


def _stats(args, client, did):
    data = client.get(f"/2/drive/{did}/statistics/sizes").get("data", {})
    print(json.dumps(data, indent=2))


def _settings(args, client, did):
    data = client.get(f"/2/drive/{did}/settings").get("data", {})
    print(json.dumps(data, indent=2))


def _users(args, client, did):
    data = client.get(f"/3/drive/{did}/users").get("data", [])
    for u in data:
        role = u.get("right", u.get("role", "?"))
        print(f"  {u.get('id'):>10}  {u.get('display_name', '?'):30s}  [{role}]")


def _activities(args, client, did):
    body = client.get(f"/3/drive/{did}/activities")
    for a in body.get("data", [])[:args.limit]:
        action = a.get("action", "?")
        path = a.get("file", {}).get("name", "?")
        user = a.get("user", {}).get("display_name", "?")
        ts = a.get("created_at", "?")
        print(f"  {ts}  {user:20s}  {action:15s}  {path}")


def _ls(args, client, did):
    fid = _resolve(client, did, getattr(args, "path", None))
    files = _paginate_files(client, did, fid)
    if not files:
        print("(empty)")
        return
    if getattr(args, "as_json", False):
        print(json.dumps(files, indent=2))
        return
    for f in files:
        is_dir = f.get("type") == "dir"
        ftype = "d" if is_dir else "-"
        size_str = _fmt_size(f.get("size", 0), is_dir)
        print(f"  {ftype} {f['id']:>10}  {size_str}  {f.get('name', '?')}")


def _info(args, client, did):
    fid = _resolve(client, did, args.target)
    data = client.get(f"/3/drive/{did}/files/{fid}", params={"with": "path,capabilities"}).get("data", {})
    print(json.dumps(data, indent=2))


def _tree(args, client, did):
    fid = _resolve(client, did, getattr(args, "path", None))
    max_depth = args.depth

    def walk(parent_id, prefix, depth):
        if depth > max_depth:
            return
        files = _paginate_files(client, did, parent_id)
        dirs = [f for f in files if f.get("type") == "dir"]
        non_dirs = [f for f in files if f.get("type") != "dir"]
        entries = dirs + non_dirs
        for i, f in enumerate(entries):
            is_last = (i == len(entries) - 1)
            connector = "└── " if is_last else "├── "
            name = f.get("name", "?")
            if f.get("type") == "dir":
                name += "/"
            print(f"{prefix}{connector}{name}")
            if f.get("type") == "dir":
                ext = "    " if is_last else "│   "
                walk(f["id"], prefix + ext, depth + 1)

    root_info = client.get(f"/3/drive/{did}/files/{fid}").get("data", {})
    print(f"{root_info.get('name', '/')}/" )
    walk(fid, "", 1)


def _mkdir(args, client, did):
    path = args.path.rstrip("/")
    if "/" in path:
        parent_path, dir_name = path.rsplit("/", 1)
        parent_id = _resolve(client, did, parent_path)
    else:
        parent_id = 1
        dir_name = path
    result = client.post(f"/3/drive/{did}/files/{parent_id}/directory",
                         json_body={"name": dir_name}).get("data", {})
    print(f"Created: {result.get('name', dir_name)} (id: {result.get('id', '?')})")


def _upload(args, client, did):
    local = Path(args.local_file)
    if not local.exists():
        print(f"Error: {local} not found", file=sys.stderr)
        sys.exit(1)
    dir_id = _resolve(client, did, getattr(args, "remote_dir", None))
    data = local.read_bytes()
    conflict = getattr(args, "conflict", "rename")
    print(f"Uploading {local.name} ({len(data) / 1024:.1f} KB)...")
    result = client.post(
        f"/3/drive/{did}/upload",
        params={"directory_id": dir_id, "file_name": local.name,
                "total_size": len(data), "conflict": conflict},
        data=data, headers={"Content-Type": "application/octet-stream"},
    ).get("data", {})
    print(f"Uploaded: {result.get('name', local.name)} (id: {result.get('id', '?')})")


def _download(args, client, did):
    fid = _resolve(client, did, args.target)
    info = client.get(f"/3/drive/{did}/files/{fid}").get("data", {})
    name = info.get("name", f"file_{fid}")
    local = Path(args.local_path) if getattr(args, "local_path", None) else Path(name)
    if local.is_dir():
        local = local / name
    print(f"Downloading {name}...")
    resp = client.get(f"/2/drive/{did}/files/{fid}/download", stream=True)
    with open(local, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"Saved: {local} ({local.stat().st_size / 1024:.1f} KB)")


def _search(args, client, did):
    params = {"query": args.query}
    if getattr(args, "ftype", None):
        params["type"] = args.ftype
    data = client.get(f"/3/drive/{did}/files/search", params=params).get("data", [])
    if not data:
        print("No results.")
        return
    for f in data:
        ftype = "d" if f.get("type") == "dir" else "-"
        print(f"  {ftype} {f['id']:>10}  {f.get('name', '?')}")


def _mv(args, client, did):
    src = _resolve(client, did, args.source)
    dst = _resolve(client, did, args.destination)
    client.post(f"/3/drive/{did}/files/{src}/move/{dst}")
    print(f"Moved {args.source} -> {args.destination}")


def _cp(args, client, did):
    src = _resolve(client, did, args.source)
    dst = _resolve(client, did, args.destination)
    client.post(f"/3/drive/{did}/files/{src}/copy/{dst}")
    print(f"Copied {args.source} -> {args.destination}")


def _rename(args, client, did):
    fid = _resolve(client, did, args.target)
    client.post(f"/2/drive/{did}/files/{fid}/rename", json_body={"name": args.new_name})
    print(f"Renamed to: {args.new_name}")


def _rm(args, client, did):
    fid = _resolve(client, did, args.target)
    client.delete(f"/2/drive/{did}/files/{fid}")
    print(f"Trashed: {args.target}")


def _hash(args, client, did):
    fid = _resolve(client, did, args.target)
    data = client.get(f"/2/drive/{did}/files/{fid}/hash").get("data", {})
    print(json.dumps(data, indent=2))


def _trash(args, client, did):
    action = args.action
    if action == "list":
        data = client.get(f"/3/drive/{did}/trash").get("data", [])
        for f in data:
            print(f"  {f['id']:>10}  {f.get('name', '?')}")
    elif action == "count":
        data = client.get(f"/2/drive/{did}/trash/count").get("data", {})
        print(f"Trash: {data.get('count', '?')} items")
    elif action == "empty":
        client.delete(f"/2/drive/{did}/trash")
        print("Trash emptied.")
    elif action == "restore":
        if not args.file_id:
            print("Error: specify file_id to restore", file=sys.stderr)
            sys.exit(1)
        client.post(f"/2/drive/{did}/trash/{args.file_id}/restore")
        print(f"Restored: {args.file_id}")


def _share(args, client, did):
    action = args.action
    if action == "list":
        data = client.get(f"/3/drive/{did}/files/links").get("data", [])
        for f in data:
            print(f"  {f.get('id'):>10}  {f.get('name', '?')}  url={f.get('link', {}).get('url', '?')}")
    elif action == "show":
        fid = _resolve(client, did, args.target)
        data = client.get(f"/2/drive/{did}/files/{fid}/link").get("data", {})
        print(json.dumps(data, indent=2))
    elif action == "create":
        fid = _resolve(client, did, args.target)
        data = client.post(f"/2/drive/{did}/files/{fid}/link").get("data", {})
        print(f"Share link: {data.get('url', '?')}")
    elif action == "delete":
        fid = _resolve(client, did, args.target)
        client.delete(f"/2/drive/{did}/files/{fid}/link")
        print("Share link removed.")


def _favorites(args, client, did):
    data = client.get(f"/3/drive/{did}/files/favorites").get("data", [])
    if not data:
        print("No favorites.")
        return
    for f in data:
        ftype = "d" if f.get("type") == "dir" else "-"
        print(f"  {ftype} {f['id']:>10}  {f.get('name', '?')}")


def _fav(args, client, did):
    fid = _resolve(client, did, args.target)
    if getattr(args, "remove", False):
        client.delete(f"/2/drive/{did}/files/{fid}/favorite")
        print(f"Unfavorited: {args.target}")
    else:
        client.post(f"/2/drive/{did}/files/{fid}/favorite")
        print(f"Favorited: {args.target}")


def _categories(args, client, did):
    action = args.action
    if action == "list":
        data = client.get(f"/2/drive/{did}/categories").get("data", [])
        for c in data:
            print(f"  {c.get('id'):>6}  {c.get('name', '?'):20s}  color={c.get('color', '?')}")
    elif action == "create":
        body = {}
        if args.name:
            body["name"] = args.name
        if args.color:
            body["color"] = args.color
        data = client.post(f"/2/drive/{did}/categories", json_body=body).get("data", {})
        print(f"Created category: {data.get('name', '?')} (id: {data.get('id', '?')})")
    elif action == "delete":
        if not args.cat_id:
            print("Error: specify --id for category to delete", file=sys.stderr)
            sys.exit(1)
        client.delete(f"/2/drive/{did}/categories/{args.cat_id}")
        print(f"Deleted category {args.cat_id}")


def _versions(args, client, did):
    fid = _resolve(client, did, args.target)
    data = client.get(f"/3/drive/{did}/files/{fid}/versions").get("data", [])
    if not data:
        print("No versions.")
        return
    for v in data:
        print(f"  v{v.get('id'):>6}  {v.get('created_at', '?')}  {_fmt_size(v.get('size', 0), False)}")
