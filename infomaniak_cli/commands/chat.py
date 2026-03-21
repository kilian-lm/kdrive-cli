"""kChat commands — channels, posts, users, teams, webhooks, bots."""

import json
import sys

from ..api_client import InfomaniakClient

# kChat uses the Mattermost-compatible API on a per-team subdomain
# Base: https://{kchat_id}.kchat.infomaniak.com/api/v4
# The kchat_id is discovered from /1/accounts/{account}/products


def register(sub):
    """Register chat subcommands."""
    chat = sub.add_parser("chat", help="manage kChat channels, messages, teams, and webhooks")
    cs = chat.add_subparsers(dest="subcommand")

    # ── teams ──
    cs.add_parser("teams", help="list kChat teams")

    p = cs.add_parser("team", help="show team details")
    p.add_argument("team_id", nargs="?", help="team ID (default: first team)")

    # ── channels ──
    p = cs.add_parser("channels", help="list channels")
    p.add_argument("--team", help="team ID")
    p.add_argument("--type", choices=["public", "private", "all"], default="all")

    p = cs.add_parser("channel", help="show channel details")
    p.add_argument("channel_id", help="channel ID or name")
    p.add_argument("--team", help="team ID")

    p = cs.add_parser("channel-create", help="create a channel")
    p.add_argument("name", help="channel name (lowercase, no spaces)")
    p.add_argument("--display-name", help="display name")
    p.add_argument("--purpose", help="channel purpose")
    p.add_argument("--type", choices=["O", "P"], default="O", help="O=public, P=private")
    p.add_argument("--team", help="team ID")

    p = cs.add_parser("channel-delete", help="archive/delete a channel")
    p.add_argument("channel_id", help="channel ID")

    p = cs.add_parser("channel-members", help="list channel members")
    p.add_argument("channel_id", help="channel ID")

    p = cs.add_parser("channel-join", help="add user to channel")
    p.add_argument("channel_id", help="channel ID")
    p.add_argument("user_id", help="user ID")

    p = cs.add_parser("channel-leave", help="remove user from channel")
    p.add_argument("channel_id", help="channel ID")
    p.add_argument("user_id", help="user ID")

    p = cs.add_parser("channel-search", help="search channels")
    p.add_argument("query", help="search term")
    p.add_argument("--team", help="team ID")

    # ── posts / messages ──
    p = cs.add_parser("posts", help="list recent posts in a channel")
    p.add_argument("channel_id", help="channel ID")
    p.add_argument("--limit", type=int, default=20, help="max posts")

    p = cs.add_parser("send", help="post a message to a channel")
    p.add_argument("message", help="message text")
    p.add_argument("--channel", required=True, help="channel ID")
    p.add_argument("--root", help="reply to post ID (thread)")

    p = cs.add_parser("delete-post", help="delete a post")
    p.add_argument("post_id", help="post ID")

    p = cs.add_parser("pin", help="pin a post")
    p.add_argument("post_id", help="post ID")

    p = cs.add_parser("unpin", help="unpin a post")
    p.add_argument("post_id", help="post ID")

    p = cs.add_parser("search-posts", help="search posts in a team")
    p.add_argument("query", help="search terms")
    p.add_argument("--team", help="team ID")

    p = cs.add_parser("thread", help="get a thread")
    p.add_argument("post_id", help="root post ID")

    # ── users ──
    p = cs.add_parser("users", help="list kChat users")
    p.add_argument("--team", help="team ID")

    p = cs.add_parser("user", help="show user details")
    p.add_argument("user_id", help="user ID")

    p = cs.add_parser("me", help="show current user info")

    p = cs.add_parser("status", help="get/set user status")
    p.add_argument("user_id", nargs="?", help="user ID (default: me)")
    p.add_argument("--set", dest="new_status", choices=["online", "away", "dnd", "offline"],
                   help="set status")

    # ── emoji ──
    p = cs.add_parser("emoji", help="list custom emoji")
    p = cs.add_parser("emoji-search", help="search custom emoji")
    p.add_argument("query", help="search term")

    # ── webhooks ──
    p = cs.add_parser("webhooks", help="list incoming webhooks")
    p.add_argument("--team", help="team ID")

    p = cs.add_parser("webhook-create", help="create incoming webhook")
    p.add_argument("--channel", required=True, help="channel ID")
    p.add_argument("--display-name", default="CLI Webhook", help="display name")
    p.add_argument("--description", default="", help="description")
    p.add_argument("--team", help="team ID")

    p = cs.add_parser("webhook-delete", help="delete a webhook")
    p.add_argument("webhook_id", help="webhook ID")

    p = cs.add_parser("webhook-send", help="send message via webhook URL")
    p.add_argument("message", help="message text")
    p.add_argument("--url", required=True, help="webhook URL")
    p.add_argument("--username", help="override username")

    # ── bots ──
    p = cs.add_parser("bots", help="list bots")

    p = cs.add_parser("bot-create", help="create a bot")
    p.add_argument("username", help="bot username")
    p.add_argument("--display-name", help="display name")
    p.add_argument("--description", default="", help="description")

    # ── reactions ──
    p = cs.add_parser("react", help="add reaction to a post")
    p.add_argument("post_id", help="post ID")
    p.add_argument("emoji", help="emoji name (without colons)")

    p = cs.add_parser("reactions", help="list reactions on a post")
    p.add_argument("post_id", help="post ID")


def dispatch(args, client: InfomaniakClient):
    sub = getattr(args, "subcommand", None)
    if sub is None:
        print("Usage: infomaniak chat <subcommand>")
        print("Run 'infomaniak chat --help' for details.")
        return

    base = _resolve_kchat_base(client)
    team_id = _resolve_team(args, client, base)

    handlers = {
        "teams": _teams, "team": _team,
        "channels": _channels, "channel": _channel,
        "channel-create": _channel_create, "channel-delete": _channel_delete,
        "channel-members": _channel_members,
        "channel-join": _channel_join, "channel-leave": _channel_leave,
        "channel-search": _channel_search,
        "posts": _posts, "send": _send, "delete-post": _delete_post,
        "pin": _pin, "unpin": _unpin, "search-posts": _search_posts, "thread": _thread,
        "users": _users, "user": _user, "me": _me, "status": _status,
        "emoji": _emoji, "emoji-search": _emoji_search,
        "webhooks": _webhooks, "webhook-create": _webhook_create,
        "webhook-delete": _webhook_delete, "webhook-send": _webhook_send,
        "bots": _bots, "bot-create": _bot_create,
        "react": _react, "reactions": _reactions,
    }
    fn = handlers.get(sub)
    if fn:
        fn(args, client, base, team_id)
    else:
        print(f"Unknown chat subcommand: {sub}")


# ── Resolvers ──

_kchat_base_cache = None


def _resolve_kchat_base(client: InfomaniakClient) -> str:
    global _kchat_base_cache
    if _kchat_base_cache:
        return _kchat_base_cache

    from kdrive_cli.config import load_config
    config = load_config()

    # 1. Explicit config
    kchat_slug = config.get("kchat", {}).get("slug")
    if kchat_slug:
        _kchat_base_cache = f"https://{kchat_slug}.kchat.infomaniak.com/api/v4"
        return _kchat_base_cache

    # 2. Derive from webhook URL in config
    webhook_secret = config.get("kchat", {}).get("webhook_secret")
    if webhook_secret:
        # If we have a cached webhook URL, extract slug from it
        try:
            import subprocess
            project = config.get("kchat", {}).get("project", config.get("token_provider", {}).get("project"))
            account = config.get("kchat", {}).get("account", config.get("token_provider", {}).get("account"))
            cmd = ["gcloud", "secrets", "versions", "access", "latest",
                   "--secret", webhook_secret, "--project", project]
            if account:
                cmd += ["--account", account]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                url = result.stdout.strip()
                # Extract slug from https://SLUG.kchat.infomaniak.com/...
                if ".kchat.infomaniak.com" in url:
                    slug = url.split("://")[1].split(".kchat.")[0]
                    _kchat_base_cache = f"https://{slug}.kchat.infomaniak.com/api/v4"
                    return _kchat_base_cache
        except Exception:
            pass

    # 3. Derive from profile: firstname-lastname
    profile = client.profile
    first = (profile.get("firstname") or "").lower().strip()
    last = (profile.get("lastname") or "").lower().strip()
    if first and last:
        slug = f"{first}-{last}"
        _kchat_base_cache = f"https://{slug}.kchat.infomaniak.com/api/v4"
        return _kchat_base_cache

    print("Error: cannot determine kChat URL. Add 'slug' to kchat config:", file=sys.stderr)
    print('  ~/.config/kdrive-cli/config.json -> "kchat": {"slug": "your-slug"}', file=sys.stderr)
    sys.exit(1)


def _resolve_team(args, client, base) -> str | None:
    if getattr(args, "team", None):
        return args.team
    try:
        me = client.get("/users/me", base_url=base).get("id")
        teams = client.get(f"/users/{me}/teams", base_url=base)
        if isinstance(teams, list) and teams:
            return teams[0].get("id")
        elif isinstance(teams, dict) and teams.get("data"):
            return teams["data"][0].get("id")
    except Exception:
        pass
    return None


def _kchat(client, method, path, base, **kwargs):
    """Make a kChat API call."""
    return client.request(method, path, base_url=base, **kwargs)


# ── Teams ──

def _teams(args, client, base, team_id):
    me = _kchat(client, "GET", "/users/me", base)
    user_id = me.get("id")
    data = _kchat(client, "GET", f"/users/{user_id}/teams", base)
    teams = data if isinstance(data, list) else data.get("data", [])
    for t in teams:
        print(f"  {t.get('id', '?')[:12]}  {t.get('display_name', t.get('name', '?'))}")


def _team(args, client, base, team_id):
    tid = getattr(args, "team_id", None) or team_id
    data = _kchat(client, "GET", f"/teams/{tid}", base)
    print(json.dumps(data, indent=2))


# ── Channels ──

def _channels(args, client, base, team_id):
    if not team_id:
        print("Error: no team found. Use --team.", file=sys.stderr)
        return
    ch_type = getattr(args, "type", "all")
    if ch_type == "public":
        data = _kchat(client, "GET", f"/teams/{team_id}/channels", base)
    elif ch_type == "private":
        data = _kchat(client, "GET", f"/teams/{team_id}/channels/private", base)
    else:
        me = _kchat(client, "GET", "/users/me", base)
        data = _kchat(client, "GET", f"/users/{me['id']}/teams/{team_id}/channels", base)

    channels = data if isinstance(data, list) else data.get("data", [])
    for c in channels:
        ch_type_str = {"O": "public", "P": "private", "D": "DM", "G": "group"}.get(c.get("type", "?"), "?")
        name = c.get("display_name") or c.get("name", "?")
        print(f"  {c.get('id', '?')[:12]}  {ch_type_str:8s}  {name}")


def _channel(args, client, base, team_id):
    cid = args.channel_id
    # Try direct ID first, then by name
    try:
        data = _kchat(client, "GET", f"/channels/{cid}", base)
    except Exception:
        if team_id:
            data = _kchat(client, "GET", f"/teams/{team_id}/channels/name/{cid}", base)
        else:
            raise
    print(json.dumps(data, indent=2))


def _channel_create(args, client, base, team_id):
    if not team_id:
        print("Error: no team found. Use --team.", file=sys.stderr)
        return
    body = {
        "team_id": team_id,
        "name": args.name,
        "display_name": getattr(args, "display_name", None) or args.name,
        "type": args.type,
    }
    if getattr(args, "purpose", None):
        body["purpose"] = args.purpose
    data = _kchat(client, "POST", "/channels", base, json_body=body)
    print(f"Created channel: {data.get('display_name', data.get('name', '?'))} (id: {data.get('id', '?')[:12]})")


def _channel_delete(args, client, base, team_id):
    _kchat(client, "DELETE", f"/channels/{args.channel_id}", base)
    print(f"Archived channel: {args.channel_id}")


def _channel_members(args, client, base, team_id):
    data = _kchat(client, "GET", f"/channels/{args.channel_id}/members", base)
    members = data if isinstance(data, list) else data.get("data", [])
    for m in members:
        uid = m.get("user_id", "?")
        roles = m.get("roles", "")
        print(f"  {uid[:12]}  roles={roles}")


def _channel_join(args, client, base, team_id):
    _kchat(client, "POST", f"/channels/{args.channel_id}/members",
           base, json_body={"user_id": args.user_id})
    print(f"Added {args.user_id} to channel {args.channel_id}")


def _channel_leave(args, client, base, team_id):
    _kchat(client, "DELETE", f"/channels/{args.channel_id}/members/{args.user_id}", base)
    print(f"Removed {args.user_id} from channel {args.channel_id}")


def _channel_search(args, client, base, team_id):
    if not team_id:
        print("Error: no team found. Use --team.", file=sys.stderr)
        return
    data = _kchat(client, "POST", f"/teams/{team_id}/channels/search",
                  base, json_body={"term": args.query})
    channels = data if isinstance(data, list) else data.get("data", [])
    for c in channels:
        print(f"  {c.get('id', '?')[:12]}  {c.get('display_name', c.get('name', '?'))}")


# ── Posts ──

def _posts(args, client, base, team_id):
    data = _kchat(client, "GET", f"/channels/{args.channel_id}/posts", base)
    order = data.get("order", [])
    posts = data.get("posts", {})
    for pid in order[:args.limit]:
        p = posts.get(pid, {})
        user = p.get("user_id", "?")[:8]
        msg = p.get("message", "")[:100]
        ts = p.get("create_at", 0)
        print(f"  {pid[:12]}  [{user}]  {msg}")


def _send(args, client, base, team_id):
    body = {"channel_id": args.channel, "message": args.message}
    if getattr(args, "root", None):
        body["root_id"] = args.root
    data = _kchat(client, "POST", "/posts", base, json_body=body)
    print(f"Sent: {data.get('id', '?')[:12]}")


def _delete_post(args, client, base, team_id):
    _kchat(client, "DELETE", f"/posts/{args.post_id}", base)
    print(f"Deleted post: {args.post_id}")


def _pin(args, client, base, team_id):
    _kchat(client, "POST", f"/posts/{args.post_id}/pin", base)
    print(f"Pinned: {args.post_id}")


def _unpin(args, client, base, team_id):
    _kchat(client, "POST", f"/posts/{args.post_id}/unpin", base)
    print(f"Unpinned: {args.post_id}")


def _search_posts(args, client, base, team_id):
    if not team_id:
        print("Error: no team found. Use --team.", file=sys.stderr)
        return
    data = _kchat(client, "POST", f"/teams/{team_id}/posts/search",
                  base, json_body={"terms": args.query})
    order = data.get("order", [])
    posts = data.get("posts", {})
    for pid in order[:20]:
        p = posts.get(pid, {})
        print(f"  {pid[:12]}  {p.get('message', '')[:80]}")


def _thread(args, client, base, team_id):
    data = _kchat(client, "GET", f"/posts/{args.post_id}/thread", base)
    order = data.get("order", [])
    posts = data.get("posts", {})
    for pid in order:
        p = posts.get(pid, {})
        prefix = "  " if pid != args.post_id else "> "
        print(f"{prefix}{pid[:12]}  {p.get('message', '')[:80]}")


# ── Users ──

def _users(args, client, base, team_id):
    if not team_id:
        print("Error: no team found. Use --team.", file=sys.stderr)
        return
    data = _kchat(client, "GET", f"/teams/{team_id}/members", base)
    members = data if isinstance(data, list) else data.get("data", [])
    for m in members:
        uid = m.get("user_id", "?")
        try:
            u = _kchat(client, "GET", f"/users/{uid}", base)
            name = u.get("username", "?")
            email = u.get("email", "")
            print(f"  {uid[:12]}  {name:20s}  {email}")
        except Exception:
            print(f"  {uid[:12]}")


def _user(args, client, base, team_id):
    data = _kchat(client, "GET", f"/users/{args.user_id}", base)
    print(json.dumps(data, indent=2))


def _me(args, client, base, team_id):
    data = _kchat(client, "GET", "/users/me", base)
    print(json.dumps(data, indent=2))


def _status(args, client, base, team_id):
    uid = getattr(args, "user_id", None)
    if not uid:
        me = _kchat(client, "GET", "/users/me", base)
        uid = me["id"]
    if getattr(args, "new_status", None):
        _kchat(client, "PUT", f"/users/{uid}/status", base,
               json_body={"user_id": uid, "status": args.new_status})
        print(f"Status set: {args.new_status}")
    else:
        data = _kchat(client, "GET", f"/users/{uid}/status", base)
        print(f"  Status: {data.get('status', '?')}")
        if data.get("manual"):
            print(f"  Manual: {data.get('manual')}")


# ── Emoji ──

def _emoji(args, client, base, team_id):
    data = _kchat(client, "GET", "/emoji", base)
    emojis = data if isinstance(data, list) else data.get("data", [])
    for e in emojis:
        print(f"  :{e.get('name', '?')}:  (creator: {e.get('creator_id', '?')[:8]})")


def _emoji_search(args, client, base, team_id):
    data = _kchat(client, "POST", "/emoji/search", base, json_body={"term": args.query})
    emojis = data if isinstance(data, list) else data.get("data", [])
    for e in emojis:
        print(f"  :{e.get('name', '?')}:")


# ── Webhooks ──

def _webhooks(args, client, base, team_id):
    if not team_id:
        print("Error: no team found. Use --team.", file=sys.stderr)
        return
    data = _kchat(client, "GET", f"/teams/{team_id}/hooks/incoming", base)
    hooks = data if isinstance(data, list) else []
    if not hooks:
        # Try older endpoint format
        data = _kchat(client, "GET", "/hooks/incoming", base)
        hooks = data if isinstance(data, list) else data.get("data", [])
    for h in hooks:
        print(f"  {h.get('id', '?')[:12]}  {h.get('display_name', '?'):20s}  channel={h.get('channel_id', '?')[:12]}")


def _webhook_create(args, client, base, team_id):
    body = {
        "channel_id": args.channel,
        "display_name": args.display_name,
        "description": args.description,
    }
    data = _kchat(client, "POST", "/hooks/incoming", base, json_body=body)
    hook_id = data.get("id", "?")
    # Construct webhook URL
    base_host = base.replace("/api/v4", "")
    print(f"Webhook created: {hook_id}")
    print(f"URL: {base_host}/hooks/{hook_id}")


def _webhook_delete(args, client, base, team_id):
    _kchat(client, "DELETE", f"/hooks/incoming/{args.webhook_id}", base)
    print(f"Deleted webhook: {args.webhook_id}")


def _webhook_send(args, client, base, team_id):
    import requests
    payload = {"text": args.message}
    if getattr(args, "username", None):
        payload["username"] = args.username
    resp = requests.post(args.url, json=payload, timeout=10)
    if resp.status_code in (200, 201):
        print("Message sent.")
    else:
        print(f"Error ({resp.status_code}): {resp.text[:200]}", file=sys.stderr)


# ── Bots ──

def _bots(args, client, base, team_id):
    data = _kchat(client, "GET", "/bots", base)
    bots = data if isinstance(data, list) else data.get("data", [])
    for b in bots:
        status = "active" if not b.get("delete_at") else "deleted"
        print(f"  {b.get('user_id', '?')[:12]}  {b.get('username', '?'):20s}  [{status}]")


def _bot_create(args, client, base, team_id):
    body = {
        "username": args.username,
        "display_name": getattr(args, "display_name", None) or args.username,
        "description": args.description,
    }
    data = _kchat(client, "POST", "/bots", base, json_body=body)
    print(f"Bot created: {data.get('username', '?')} (id: {data.get('user_id', '?')[:12]})")


# ── Reactions ──

def _react(args, client, base, team_id):
    me = _kchat(client, "GET", "/users/me", base)
    _kchat(client, "POST", "/reactions", base, json_body={
        "user_id": me["id"],
        "post_id": args.post_id,
        "emoji_name": args.emoji,
    })
    print(f"Reacted :{args.emoji}: on {args.post_id[:12]}")


def _reactions(args, client, base, team_id):
    data = _kchat(client, "GET", f"/posts/{args.post_id}/reactions", base)
    reactions = data if isinstance(data, list) else data.get("data", [])
    for r in reactions:
        print(f"  :{r.get('emoji_name', '?')}:  by {r.get('user_id', '?')[:8]}")
