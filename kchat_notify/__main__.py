"""CLI entry point for kchat-notify."""

import argparse
import sys

from .client import KChatNotifier


def main():
    parser = argparse.ArgumentParser(description="Send a message to kChat via webhook")
    parser.add_argument("message", nargs="?", help="Message text (or read from stdin)")
    parser.add_argument("--webhook-url", help="Webhook URL (or set KCHAT_WEBHOOK_URL)")
    parser.add_argument("--title", help="Rich message title (enables attachment format)")
    parser.add_argument("--color", default="#0076D1", help="Attachment color (hex)")
    parser.add_argument("--username", help="Override display username")
    parser.add_argument("--field", action="append", nargs=2, metavar=("KEY", "VALUE"),
                        help="Add a field to rich message (repeatable)")
    args = parser.parse_args()

    text = args.message
    if text is None:
        if not sys.stdin.isatty():
            text = sys.stdin.read().strip()
        else:
            parser.error("Provide a message as argument or pipe via stdin")

    try:
        notifier = KChatNotifier.from_config(webhook_url=args.webhook_url)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    if args.title:
        fields = dict(args.field) if args.field else None
        ok = notifier.send_rich(args.title, text=text, fields=fields,
                                color=args.color, username=args.username)
    else:
        ok = notifier.send(text, username=args.username)

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
