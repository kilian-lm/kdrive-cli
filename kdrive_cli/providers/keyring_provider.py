"""System keyring token provider (macOS Keychain, Windows Credential Manager, etc.)."""

from .base import TokenProvider

SERVICE_NAME = "kdrive-cli"
ACCOUNT_NAME = "api-token"


class KeyringTokenProvider(TokenProvider):
    """Read/write token using the OS keyring."""

    def get_token(self) -> str | None:
        try:
            import keyring
            return keyring.get_password(SERVICE_NAME, ACCOUNT_NAME)
        except ImportError:
            return None

    @staticmethod
    def store_token(token: str) -> None:
        import keyring
        keyring.set_password(SERVICE_NAME, ACCOUNT_NAME, token)

    @staticmethod
    def delete_token() -> None:
        import keyring
        keyring.delete_password(SERVICE_NAME, ACCOUNT_NAME)
