# kdrive-cli

Unofficial CLI for [Infomaniak kDrive](https://www.infomaniak.com/en/ksuite/kdrive) — manage files, folders, and drives from the terminal.

## Install

```bash
# pip
pip install kdrive-cli

# brew (macOS/Linux)
brew install kilian-lm/tap/kdrive-cli

# from source
git clone https://github.com/kilian-lm/kdrive-cli.git
cd kdrive-cli && pip install .
```

## Quick start

```bash
# configure (interactive — picks your token provider)
kdrive configure

# list drives
kdrive drives

# list files
kdrive ls
kdrive ls Documents/Photos

# create directory
kdrive mkdir Projects/new-project

# upload / download
kdrive upload report.pdf 42
kdrive download 99 ./local-copy.pdf

# search
kdrive search "invoice 2026"

# file info (JSON)
kdrive info 42

# trash
kdrive rm old-file.txt
```

## Authentication

Token is resolved in this order:

1. `--token` flag
2. `INFOMANIAK_TOKEN` environment variable
3. Configured provider (set via `kdrive configure`)

### Supported token providers

| Provider | Install | Config key |
|----------|---------|------------|
| Environment variable | (built-in) | `env` |
| GCP Secret Manager | `pip install kdrive-cli[gcp]` | `gcp` |
| AWS Secrets Manager | `pip install kdrive-cli[aws]` | `aws` |
| Azure Key Vault | `pip install kdrive-cli[azure]` | `azure` |
| System keyring | `pip install kdrive-cli[keyring]` | `keyring` |

Config is stored at `~/.config/kdrive-cli/config.json`.

### Create an API token

1. Go to https://manager.infomaniak.com
2. Profile (top-right) > Developer > API tokens
3. Create a token with kDrive scope

## Commands

| Command | Description |
|---------|-------------|
| `configure` | Interactive setup (token provider + default drive) |
| `drives` | List accessible kDrives |
| `ls [PATH]` | List directory contents (by path or ID) |
| `mkdir PATH` | Create directory (supports nested paths) |
| `upload FILE [DIR_ID]` | Upload file (< 1 GB) |
| `download FILE_ID [PATH]` | Download file |
| `info FILE_ID` | File/folder metadata as JSON |
| `search QUERY` | Search by file name |
| `rm TARGET` | Move file/folder to trash |

## License

MIT
