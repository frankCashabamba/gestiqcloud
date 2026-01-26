"""
Secrets Management Service
Handles retrieval of sensitive credentials from secure sources
"""

import json
import logging
import os

logger = logging.getLogger(__name__)


class SecretsManager:
    """
    Centralized secrets management.
    Supports multiple backends: env vars, AWS Secrets Manager, Vault, etc.
    """

    @staticmethod
    def get_certificate_password(tenant_id: str, country: str = "ECU") -> str:
        """
        Get certificate password for a specific tenant and country.

        Priority:
        1. AWS Secrets Manager (production)
        2. Environment variable (development)
        3. Raise error

        Args:
            tenant_id: Tenant identifier
            country: Country code (ECU, ESP, etc)

        Returns:
            Certificate password

        Raises:
            ValueError: If password cannot be retrieved
        """
        # Try environment variable first (development, local testing)
        env_key = f"CERT_PASSWORD_{tenant_id}_{country}".upper()
        env_password = os.getenv(env_key)
        if env_password:
            logger.info(f"Using certificate password from env var {env_key}")
            return env_password

        # Try AWS Secrets Manager (production)
        try:
            return SecretsManager._get_from_aws_secrets(tenant_id, country)
        except Exception as e:
            logger.warning(f"AWS Secrets Manager failed: {e}")

        # No password found
        raise ValueError(
            f"Certificate password not found for tenant {tenant_id} ({country}). "
            f"Configure {env_key} or use AWS Secrets Manager."
        )

    @staticmethod
    def _get_from_aws_secrets(tenant_id: str, country: str) -> str:
        """
        Retrieve certificate password from AWS Secrets Manager.

        Assumes secret is stored as JSON:
        {
            "certificate_password": "actual_password"
        }
        """
        try:
            import boto3
        except ImportError:
            raise ValueError("boto3 not installed. Install with: pip install boto3")

        secret_name = f"gestiqcloud/{tenant_id}/certificates/{country}"
        region = os.getenv("AWS_REGION", "us-east-1")

        client = boto3.client("secretsmanager", region_name=region)
        try:
            response = client.get_secret_value(SecretId=secret_name)
        except client.exceptions.ResourceNotFoundException:
            raise ValueError(f"Secret {secret_name} not found in AWS Secrets Manager")
        except Exception as e:
            raise ValueError(f"Failed to retrieve secret {secret_name}: {e}")

        if "SecretString" in response:
            secret = json.loads(response["SecretString"])
            password = secret.get("certificate_password")
            if not password:
                raise ValueError(f"Secret {secret_name} missing 'certificate_password' key")
            return password

        raise ValueError(f"Secret {secret_name} does not contain SecretString")

    @staticmethod
    def get_smtp_password() -> str | None:
        """Get SMTP password from secure source"""
        return os.getenv("SMTP_PASSWORD")

    @staticmethod
    def get_api_key(service: str) -> str | None:
        """Get API key for external service"""
        return os.getenv(f"{service.upper()}_API_KEY")


# Singleton instance
_secrets = SecretsManager()


def get_certificate_password(tenant_id: str, country: str = "ECU") -> str:
    """Convenience function to get certificate password"""
    return _secrets.get_certificate_password(tenant_id, country)


def get_smtp_password() -> str | None:
    """Convenience function to get SMTP password"""
    return _secrets.get_smtp_password()


def get_api_key(service: str) -> str | None:
    """Convenience function to get API key"""
    return _secrets.get_api_key(service)
