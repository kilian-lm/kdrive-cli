"""Core resource commands: profile, accounts, teams, products."""

import json

from ..api_client import InfomaniakClient


def register(sub):
    """Register core subcommands under the 'core' group."""

    # ── profile ──
    profile = sub.add_parser("profile", help="manage your Infomaniak profile")
    profile_sub = profile.add_subparsers(dest="subcommand")

    profile_sub.add_parser("show", help="show profile information")
    profile_sub.add_parser("emails", help="list email addresses")
    profile_sub.add_parser("phones", help="list phone numbers")
    profile_sub.add_parser("app-passwords", help="list application passwords")

    p = profile_sub.add_parser("update", help="update profile fields")
    p.add_argument("--first-name", help="first name")
    p.add_argument("--last-name", help="last name")
    p.add_argument("--language", help="language code (e.g. en, fr, de)")

    # ── accounts ──
    accounts = sub.add_parser("accounts", help="manage Infomaniak accounts")
    acc_sub = accounts.add_subparsers(dest="subcommand")

    acc_sub.add_parser("list", help="list all accounts")

    p = acc_sub.add_parser("show", help="show account details")
    p.add_argument("account_id", nargs="?", help="account ID (default: primary)")

    p = acc_sub.add_parser("products", help="list products for an account")
    p.add_argument("account_id", nargs="?", help="account ID (default: primary)")

    p = acc_sub.add_parser("users", help="list users in an account")
    p.add_argument("account_id", nargs="?", help="account ID (default: primary)")

    # ── teams ──
    teams = sub.add_parser("teams", help="manage teams in an account")
    teams_sub = teams.add_subparsers(dest="subcommand")

    p = teams_sub.add_parser("list", help="list teams")
    p.add_argument("--account", help="account ID")

    p = teams_sub.add_parser("show", help="show team details")
    p.add_argument("team_id", help="team ID")
    p.add_argument("--account", help="account ID")

    p = teams_sub.add_parser("create", help="create a new team")
    p.add_argument("name", help="team name")
    p.add_argument("--account", help="account ID")

    p = teams_sub.add_parser("delete", help="delete a team")
    p.add_argument("team_id", help="team ID")
    p.add_argument("--account", help="account ID")

    p = teams_sub.add_parser("members", help="list team members")
    p.add_argument("team_id", help="team ID")
    p.add_argument("--account", help="account ID")


def dispatch(args, client: InfomaniakClient):
    """Route to the correct handler."""
    group = args.command
    sub = getattr(args, "subcommand", None)

    if group == "profile":
        return _profile(args, client, sub)
    elif group == "accounts":
        return _accounts(args, client, sub)
    elif group == "teams":
        return _teams(args, client, sub)


# ── Profile ──

def _profile(args, client: InfomaniakClient, sub: str):
    if sub == "show" or sub is None:
        data = client.get("/2/profile").get("data", {})
        _print_kv({
            "ID": data.get("id"),
            "Name": f"{data.get('firstname', '')} {data.get('lastname', '')}".strip(),
            "Email": data.get("email"),
            "Login": data.get("login"),
            "Language": data.get("language"),
            "Created": data.get("created_at"),
        })
    elif sub == "emails":
        data = client.get("/2/profile/emails").get("data", [])
        for e in data:
            primary = " (primary)" if e.get("is_primary") else ""
            print(f"  {e.get('email', '?')}{primary}  [{e.get('type', '?')}]")
    elif sub == "phones":
        data = client.get("/2/profile/phones").get("data", [])
        for p in data:
            print(f"  {p.get('number', '?')}  [{p.get('type', '?')}]")
    elif sub == "app-passwords":
        data = client.get("/2/profile/applications/passwords").get("data", [])
        if not data:
            print("No application passwords.")
            return
        for p in data:
            print(f"  {p.get('id'):>6}  {p.get('name', '?')}  (created: {p.get('created_at', '?')})")
    elif sub == "update":
        body = {}
        if args.first_name:
            body["firstname"] = args.first_name
        if args.last_name:
            body["lastname"] = args.last_name
        if args.language:
            body["language"] = args.language
        if not body:
            print("Nothing to update. Use --first-name, --last-name, or --language.")
            return
        client.patch("/2/profile", json_body=body)
        print("Profile updated.")
    else:
        print(f"Unknown subcommand: profile {sub}")


# ── Accounts ──

def _accounts(args, client: InfomaniakClient, sub: str):
    if sub == "list" or sub is None:
        data = client.get("/1/accounts").get("data", [])
        for a in data:
            print(f"  {a['id']:>10}  {a.get('name', '?')}")
    elif sub == "show":
        aid = args.account_id or client.account_id
        data = client.get(f"/1/accounts/{aid}").get("data", {})
        print(json.dumps(data, indent=2))
    elif sub == "products":
        aid = args.account_id or client.account_id
        data = client.get(f"/1/accounts/{aid}/products").get("data", [])
        for p in data:
            print(f"  {p.get('id'):>10}  {p.get('product_name', '?'):20s}  {p.get('customer_name', '')}")
    elif sub == "users":
        aid = args.account_id or client.account_id
        data = client.get(f"/2/accounts/{aid}/users").get("data", [])
        for u in data:
            role = u.get("role", "?")
            uid = u.get("id", "?")
            name = u.get("display_name", "?") or "?"
            email = u.get("email", "") or ""
            print(f"  {str(uid):>10}  {name:30s}  {email:30s}  [{role}]")
    else:
        print(f"Unknown subcommand: accounts {sub}")


# ── Teams ──

def _teams(args, client: InfomaniakClient, sub: str):
    aid = getattr(args, "account", None) or client.account_id

    if sub == "list" or sub is None:
        data = client.get(f"/1/accounts/{aid}/teams").get("data", [])
        if not data:
            print("No teams.")
            return
        for t in data:
            print(f"  {t.get('id'):>10}  {t.get('name', '?')}")
    elif sub == "show":
        data = client.get(f"/1/accounts/{aid}/teams/{args.team_id}").get("data", {})
        print(json.dumps(data, indent=2))
    elif sub == "create":
        data = client.post(f"/1/accounts/{aid}/teams", json_body={"name": args.name}).get("data", {})
        print(f"Created team: {data.get('name', args.name)} (id: {data.get('id', '?')})")
    elif sub == "delete":
        client.delete(f"/1/accounts/{aid}/teams/{args.team_id}")
        print(f"Deleted team {args.team_id}")
    elif sub == "members":
        data = client.get(f"/1/accounts/{aid}/teams/{args.team_id}/users").get("data", [])
        for u in data:
            print(f"  {u.get('id'):>10}  {u.get('display_name', '?')}")
    else:
        print(f"Unknown subcommand: teams {sub}")


def _print_kv(items: dict):
    width = max(len(k) for k in items) + 2
    for k, v in items.items():
        if v is not None:
            print(f"  {k + ':':{width}s} {v}")
