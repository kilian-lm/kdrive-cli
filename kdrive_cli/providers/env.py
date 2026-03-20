"""Environment variable token provider."""

import os

from .base import TokenProvider


class EnvTokenProvider(TokenProvider):
    """Read token from an environment variable."""

    def __init__(self, var_name: str = "INFOMANIAK_TOKEN"):
        self.var_name = var_name

    def get_token(self) -> str | None:
        return os.environ.get(self.var_name)
