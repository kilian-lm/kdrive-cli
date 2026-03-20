"""Entry point for `python -m kdrive_cli`."""

import argparse
import sys

from . import __version__
from .commands import (
    cmd_configure,
    cmd_download,
    cmd_drives,
    cmd_info,
    cmd_ls,
    cmd_mkdir,
    cmd_rm,
    cmd_search,
    cmd_upload,
)

DESCRIPTION = """\
kdrive-cli — Infomaniak kDrive from the command line.

Manage files, folders, and drives on Infomaniak kDrive via the REST API.
Token is resolved in order: --token flag > INFOMANIAK_TOKEN env > configured provider.
Run `kdrive configure` to set up authentication."""

EXAMPLES = """\
examples:
  kdrive configure                    # interactive setup
  kdrive drives                       # list drives
  kdrive ls                           # list root
  kdrive ls Documents/Photos          # list by path
  kdrive mkdir Projects/new-folder    # create nested dir
  kdrive upload report.pdf 7          # upload to dir id 7
  kdrive download 42 ./local.pdf      # download file id 42
  kdrive search "invoice"             # search by name
  kdrive rm Private/test-cli          # trash a file/folder
"""


def main():
    parser = argparse.ArgumentParser(
        prog="kdrive",
        description=DESCRIPTION,
        epilog=EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-v", "--version", action="version", version=f"kdrive-cli {__version__}")
    parser.add_argument("--token", help="API token (overrides all other sources)")
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    sub.add_parser("configure", help="interactive setup")
    sub.add_parser("drives", help="list accessible drives")

    p = sub.add_parser("ls", help="list directory contents")
    p.add_argument("--drive", help="drive ID")
    p.add_argument("path", nargs="?", help="directory ID or path (default: root)")

    p = sub.add_parser("mkdir", help="create directory")
    p.add_argument("--drive", help="drive ID")
    p.add_argument("path", help="path to create (e.g. Documents/new-folder)")

    p = sub.add_parser("upload", help="upload a file")
    p.add_argument("--drive", help="drive ID")
    p.add_argument("local_file", help="local file path")
    p.add_argument("remote_dir_id", nargs="?", help="target directory ID (default: root)")

    p = sub.add_parser("download", help="download a file")
    p.add_argument("--drive", help="drive ID")
    p.add_argument("file_id", help="file ID")
    p.add_argument("local_path", nargs="?", help="local save path")

    p = sub.add_parser("info", help="file/folder details (JSON)")
    p.add_argument("--drive", help="drive ID")
    p.add_argument("file_id", help="file or folder ID")

    p = sub.add_parser("search", help="search files by name")
    p.add_argument("--drive", help="drive ID")
    p.add_argument("query", help="search query")

    p = sub.add_parser("rm", help="move file/folder to trash")
    p.add_argument("--drive", help="drive ID")
    p.add_argument("target", help="file ID or path")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    dispatch = {
        "configure": cmd_configure,
        "drives": cmd_drives,
        "ls": cmd_ls,
        "mkdir": cmd_mkdir,
        "upload": cmd_upload,
        "download": cmd_download,
        "info": cmd_info,
        "search": cmd_search,
        "rm": cmd_rm,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
