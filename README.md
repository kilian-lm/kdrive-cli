# infomaniak-tools

Unofficial CLI for [Infomaniak Cloud](https://www.infomaniak.com) — manage kDrive, kChat, accounts, and more from the terminal. Like `gcloud` for GCP, but for Infomaniak.

## Install

```bash
# pip
pip install infomaniak-tools

# with cloud token providers
pip install infomaniak-tools[gcp]    # GCP Secret Manager
pip install infomaniak-tools[aws]    # AWS Secrets Manager
pip install infomaniak-tools[azure]  # Azure Key Vault
pip install infomaniak-tools[all]    # all providers

# from source
git clone https://github.com/kilian-lm/infomaniak-tools.git
cd infomaniak-tools && pip install .
```

## Quick start

```bash
# configure (interactive — picks your token provider + default drive)
infomaniak configure

# profile & account
infomaniak profile show
infomaniak accounts list
infomaniak accounts products

# kDrive — files & folders
infomaniak drive list
infomaniak drive ls
infomaniak drive ls Documents/Photos
infomaniak drive tree --depth 2
infomaniak drive mkdir Projects/new-project
infomaniak drive upload report.pdf 42
infomaniak drive download 99 ./local-copy.pdf
infomaniak drive search "invoice 2026"
infomaniak drive mv old-folder new-folder
infomaniak drive share create Documents/spec
infomaniak drive trash list
infomaniak drive categories list
infomaniak drive versions my-file.pdf

# kChat — messaging & webhooks
infomaniak chat me
infomaniak chat teams
infomaniak chat channels
infomaniak chat send "deploy complete" --channel CHANNEL_ID
infomaniak chat posts CHANNEL_ID
infomaniak chat webhooks
infomaniak chat webhook-create --channel CHANNEL_ID
infomaniak chat webhook-send "alert!" --url WEBHOOK_URL
infomaniak chat bots

# teams
infomaniak teams list
infomaniak teams create "engineering"
```

## CLI entry points

The package provides three CLI commands:

| Command | Description |
|---------|-------------|
| `infomaniak` | Full CLI — all products (profile, drive, chat, teams) |
| `kdrive` | Legacy kDrive-only CLI (backward compatible) |
| `kchat-notify` | Send kChat webhook notifications from scripts |

## Authentication

Token is resolved in this order:

1. `--token` flag
2. `INFOMANIAK_TOKEN` environment variable
3. Configured provider (set via `infomaniak configure`)

### Supported token providers

| Provider | Install | Config key |
|----------|---------|------------|
| Environment variable | (built-in) | `env` |
| GCP Secret Manager | `pip install infomaniak-tools[gcp]` | `gcp` |
| AWS Secrets Manager | `pip install infomaniak-tools[aws]` | `aws` |
| Azure Key Vault | `pip install infomaniak-tools[azure]` | `azure` |
| System keyring | `pip install infomaniak-tools[keyring]` | `keyring` |

Config is stored at `~/.config/kdrive-cli/config.json`.

### Create an API token

1. Go to https://manager.infomaniak.com
2. Profile (top-right) → Developer → API tokens
3. Create a token with kDrive + kChat scope

## Command reference

### Core

| Command | Description |
|---------|-------------|
| `configure` | Interactive setup |
| `profile show` | Your profile info |
| `profile emails` | List email addresses |
| `profile update --language de` | Update profile fields |
| `accounts list` | List accounts |
| `accounts products` | List products (kDrive, kChat, etc.) |
| `accounts users` | List account users |
| `teams list` | List teams |
| `teams create NAME` | Create a team |
| `teams members TEAM_ID` | List team members |

### kDrive

| Command | Description |
|---------|-------------|
| `drive list` | List accessible drives |
| `drive ls [PATH]` | List directory contents |
| `drive tree [PATH]` | Directory tree view |
| `drive info TARGET` | File metadata (JSON) |
| `drive mkdir PATH` | Create directory (nested) |
| `drive upload FILE [DIR]` | Upload file |
| `drive download TARGET [PATH]` | Download file |
| `drive search QUERY` | Search by name |
| `drive mv SRC DST` | Move file/folder |
| `drive cp SRC DST` | Copy file/folder |
| `drive rename TARGET NAME` | Rename |
| `drive rm TARGET` | Trash file/folder |
| `drive hash TARGET` | Get file hash |
| `drive trash list\|empty\|restore\|count` | Manage trash |
| `drive share create\|show\|delete\|list` | Share links |
| `drive favorites` | List favorites |
| `drive fav TARGET` | Toggle favorite |
| `drive categories list\|create\|delete` | Manage categories |
| `drive versions TARGET` | List file versions |
| `drive stats` | Drive statistics |
| `drive users` | Drive users |
| `drive activities` | Recent activities |

### kChat

| Command | Description |
|---------|-------------|
| `chat me` | Current user info |
| `chat teams` | List teams |
| `chat channels` | List channels |
| `chat channel CHANNEL_ID` | Channel details |
| `chat channel-create NAME` | Create channel |
| `chat channel-search QUERY` | Search channels |
| `chat channel-members CHANNEL_ID` | List members |
| `chat posts CHANNEL_ID` | Recent messages |
| `chat send MESSAGE --channel ID` | Post message |
| `chat thread POST_ID` | Get thread |
| `chat search-posts QUERY` | Search messages |
| `chat pin\|unpin POST_ID` | Pin/unpin post |
| `chat react POST_ID EMOJI` | Add reaction |
| `chat users` | List users |
| `chat status [USER_ID]` | Get/set status |
| `chat webhooks` | List webhooks |
| `chat webhook-create --channel ID` | Create webhook |
| `chat webhook-send MSG --url URL` | Send via webhook |
| `chat bots` | List bots |
| `chat bot-create USERNAME` | Create bot |
| `chat emoji` | List custom emoji |

## License

MIT
