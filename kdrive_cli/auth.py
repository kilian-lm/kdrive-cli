"""Token resolution — tries providers in priority order."""

import sys

from .config import load_config
from .providers.base import TokenProvider
from .providers.env import EnvTokenProvider


def build_providers_from_config() -> list[TokenProvider]:
    """Build token provider chain from config file settings."""
    providers: list[TokenProvider] = [EnvTokenProvider()]

    config = load_config()
    provider_config = config.get("token_provider", {})
    provider_type = provider_config.get("type")

    if provider_type == "gcp":
        from .providers.gcp_secret_manager import GCPSecretManagerProvider
        providers.append(GCPSecretManagerProvider(
            project=provider_config["project"],
            secret_name=provider_config.get("secret_name", "INFOMANIAK_API_TOKEN"),
            account=provider_config.get("account"),
        ))
    elif provider_type == "aws":
        from .providers.aws_secrets_manager import AWSSecretsManagerProvider
        providers.append(AWSSecretsManagerProvider(
            secret_name=provider_config.get("secret_name", "infomaniak-api-token"),
            region=provider_config.get("region", "eu-central-1"),
        ))
    elif provider_type == "azure":
        from .providers.azure_keyvault import AzureKeyVaultProvider
        providers.append(AzureKeyVaultProvider(
            vault_url=provider_config["vault_url"],
            secret_name=provider_config.get("secret_name", "infomaniak-api-token"),
        ))
    elif provider_type == "keyring":
        from .providers.keyring_provider import KeyringTokenProvider
        providers.append(KeyringTokenProvider())

    return providers


def resolve_token(explicit_token: str | None = None) -> str:
    """Resolve API token. Priority: explicit > env > configured provider."""
    if explicit_token:
        return explicit_token

    for provider in build_providers_from_config():
        token = provider.get_token()
        if token:
            return token

    print("Error: No API token found.", file=sys.stderr)
    print("Options:", file=sys.stderr)
    print("  1. Set INFOMANIAK_TOKEN environment variable", file=sys.stderr)
    print("  2. Pass --token on the command line", file=sys.stderr)
    print("  3. Run 'kdrive configure' to set up a token provider", file=sys.stderr)
    sys.exit(1)
