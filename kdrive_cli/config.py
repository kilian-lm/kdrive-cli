"""Configuration management for kDrive CLI."""

import json
import os
from pathlib import Path
from typing import Any

DEFAULT_CONFIG_DIR = Path(os.environ.get("KDRIVE_CONFIG_DIR", Path.home() / ".config" / "kdrive-cli"))
CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.json"


def load_config() -> dict[str, Any]:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}


def save_config(config: dict[str, Any]) -> None:
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2) + "\n")


def get_config_value(key: str, default: Any = None) -> Any:
    return load_config().get(key, default)


def set_config_value(key: str, value: Any) -> None:
    config = load_config()
    config[key] = value
    save_config(config)
