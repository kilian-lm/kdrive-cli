"""Entry point for `infomaniak` CLI — like gcloud but for Infomaniak."""

import argparse
import sys

from . import __version__
from .api_client import APIError, InfomaniakClient
from .commands import core, drive, chat

DESCRIPTION = """\
infomaniak — Infomaniak Cloud from the command line.

Manage kDrive files, kChat channels, accounts, and more via the REST API.
Token is resolved in order: --token flag > INFOMANIAK_TOKEN env > configured provider.
Run `infomaniak configure` to set up authentication.

Product groups:
  profile     Your Infomaniak profile
  accounts    Account management
  teams       Team management
  drive       kDrive file & folder operations
  chat        kChat messaging, channels & webhooks"""

EXAMPLES = """\
examples:
  infomaniak configure                          # interactive setup
  infomaniak profile show                       # show your profile
  infomaniak accounts list                      # list accounts
  infomaniak accounts products                  # list products
  infomaniak drive list                         # list drives
  infomaniak drive ls                           # list root directory
  infomaniak drive ls Documents/Photos          # list by path
  infomaniak drive upload report.pdf 7          # upload to dir id 7
  infomaniak drive tree --depth 2               # show directory tree
  infomaniak drive search "invoice"             # search files
  infomaniak drive trash list                   # list trashed files
  infomaniak drive share create Documents/spec  # create share link
  infomaniak chat teams                         # list kChat teams
  infomaniak chat channels                      # list channels
  infomaniak chat send "hello" --channel ID     # post a message
  infomaniak chat webhooks                      # list webhooks
  infomaniak chat webhook-send "msg" --url URL  # send via webhook
"""


def main():
    parser = argparse.ArgumentParser(
        prog="infomaniak",
        description=DESCRIPTION,
        epilog=EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-v", "--version", action="version",
                        version=f"infomaniak-tools {__version__}")
    parser.add_argument("--token", help="API token (overrides all other sources)")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="output format (default: text)")

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    # Configure command (standalone)
    sub.add_parser("configure", help="interactive setup (same as kdrive configure)")

    # Register command groups
    core.register(sub)
    drive.register(sub)
    chat.register(sub)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Handle configure separately
    if args.command == "configure":
        from kdrive_cli.commands import cmd_configure
        cmd_configure(args)
        return

    # Build client
    from kdrive_cli.auth import resolve_token
    token = resolve_token(getattr(args, "token", None))
    client = InfomaniakClient(token)

    try:
        # Dispatch to command group
        if args.command in ("profile", "accounts", "teams"):
            core.dispatch(args, client)
        elif args.command == "drive":
            drive.dispatch(args, client)
        elif args.command == "chat":
            chat.dispatch(args, client)
        else:
            print(f"Unknown command: {args.command}", file=sys.stderr)
            parser.print_help()
            sys.exit(1)
    except APIError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nAborted.", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
