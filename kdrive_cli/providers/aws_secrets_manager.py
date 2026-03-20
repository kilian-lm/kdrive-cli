"""AWS Secrets Manager token provider."""

from .base import TokenProvider


class AWSSecretsManagerProvider(TokenProvider):
    """Fetch token from AWS Secrets Manager.

    Requires boto3 and valid AWS credentials (env vars, ~/.aws/credentials, or IAM role).
    """

    def __init__(self, secret_name: str = "infomaniak-api-token", region: str = "eu-central-1"):
        self.secret_name = secret_name
        self.region = region

    def get_token(self) -> str | None:
        try:
            import boto3
            client = boto3.client("secretsmanager", region_name=self.region)
            response = client.get_secret_value(SecretId=self.secret_name)
            return response["SecretString"].strip()
        except Exception:
            return None
