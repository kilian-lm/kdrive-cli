"""Azure Key Vault token provider."""

from .base import TokenProvider


class AzureKeyVaultProvider(TokenProvider):
    """Fetch token from Azure Key Vault.

    Requires azure-identity and azure-keyvault-secrets packages,
    plus valid Azure credentials.
    """

    def __init__(self, vault_url: str, secret_name: str = "infomaniak-api-token"):
        self.vault_url = vault_url
        self.secret_name = secret_name

    def get_token(self) -> str | None:
        try:
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.secrets import SecretClient
            credential = DefaultAzureCredential()
            client = SecretClient(vault_url=self.vault_url, credential=credential)
            secret = client.get_secret(self.secret_name)
            return secret.value.strip() if secret.value else None
        except Exception:
            return None
