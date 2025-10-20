"""
Certificate Manager - Gestión de certificados digitales para e-factura

Maneja el almacenamiento seguro y recuperación de certificados PKCS#12
para firmas digitales en SRI (Ecuador) y SII (España).
"""

import os
import base64
from typing import Optional, Dict, Any
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.backends import default_backend

from app.config.database import get_db_session
from app.models.core.einvoicing import EinvoicingCredentials


class CertificateManager:
    """
    Gestiona certificados digitales para e-factura.

    Soporta:
    - Almacenamiento en base de datos (BLOB)
    - Almacenamiento en S3 (recomendado para prod)
    - Validación de certificados
    - Extracción de información del certificado
    """

    def __init__(self):
        # En desarrollo, usar filesystem
        # En producción, usar S3
        self.storage_type = os.getenv("CERT_STORAGE_TYPE", "filesystem")
        self.cert_dir = Path("uploads/certs") if self.storage_type == "filesystem" else None

        if self.cert_dir:
            self.cert_dir.mkdir(parents=True, exist_ok=True)

    async def store_certificate(
        self,
        tenant_id: str,
        country: str,
        cert_data: bytes,
        password: str,
        cert_type: str = "p12"
    ) -> str:
        """
        Almacena un certificado para un tenant/país.

        Args:
            tenant_id: UUID del tenant
            country: 'EC' o 'ES'
            cert_data: Bytes del archivo P12/PFX
            password: Contraseña del certificado
            cert_type: Tipo de certificado ('p12', 'pfx')

        Returns:
            cert_ref: Referencia para recuperar el certificado
        """
        # Validar certificado
        cert_info = self._validate_certificate(cert_data, password)
        if not cert_info:
            raise ValueError("Certificado inválido o contraseña incorrecta")

        # Generar referencia única
        cert_ref = f"{tenant_id}_{country}_{cert_type}_{cert_info['serial']}"

        # Almacenar según tipo de storage
        if self.storage_type == "filesystem":
            cert_path = self.cert_dir / f"{cert_ref}.p12"
            with open(cert_path, "wb") as f:
                f.write(cert_data)
        elif self.storage_type == "database":
            # Almacenar en DB como BLOB
            await self._store_in_database(tenant_id, country, cert_data, cert_ref)
        elif self.storage_type == "s3":
            # TODO: Implementar S3 storage
            raise NotImplementedError("S3 storage not implemented yet")

        # Actualizar/insertar credenciales en DB
        await self._update_credentials(
            tenant_id, country, cert_ref, password, cert_info
        )

        return cert_ref

    async def get_certificate(
        self,
        tenant_id: str,
        country: str
    ) -> Optional[Dict[str, Any]]:
        """
        Recupera certificado y datos para un tenant/país.
        """
        async with get_db_session() as db:
            result = await db.execute("""
                SELECT sri_cert_ref, sri_key_ref, sri_env,
                       sii_cert_ref, sii_key_ref
                FROM einvoicing_credentials
                WHERE tenant_id = :tenant_id AND country = :country
            """, {"tenant_id": tenant_id, "country": country})

            creds = result.first()
            if not creds:
                return None

            cert_ref = creds.sri_cert_ref if country == "EC" else creds.sii_cert_ref
            if not cert_ref:
                return None

            # Recuperar archivo según storage type
            cert_data = await self._retrieve_certificate_data(cert_ref)

            return {
                "cert_data": cert_data,
                "cert_ref": cert_ref,
                "country": country,
                "env": creds.sri_env if country == "EC" else "production"
            }

    def _validate_certificate(self, cert_data: bytes, password: str) -> Optional[Dict[str, Any]]:
        """
        Valida un certificado PKCS#12 y extrae información.
        """
        try:
            private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(
                cert_data, password.encode(), default_backend()
            )

            if not certificate:
                return None

            # Extraer información básica
            subject = certificate.subject
            issuer = certificate.issuer
            serial = certificate.serial_number
            not_before = certificate.not_valid_before
            not_after = certificate.not_valid_after

            return {
                "subject": str(subject),
                "issuer": str(issuer),
                "serial": str(serial),
                "not_before": not_before,
                "not_after": not_after,
                "is_valid": True
            }

        except Exception as e:
            print(f"Certificate validation failed: {e}")
            return None

    async def _store_in_database(
        self,
        tenant_id: str,
        country: str,
        cert_data: bytes,
        cert_ref: str
    ):
        """Almacena certificado en base de datos como BLOB."""
        async with get_db_session() as db:
            # Aquí iría la lógica para almacenar en una tabla de certificados
            # Por simplicidad, usamos filesystem por ahora
            pass

    async def _retrieve_certificate_data(self, cert_ref: str) -> bytes:
        """Recupera datos del certificado según storage type."""
        if self.storage_type == "filesystem":
            cert_path = self.cert_dir / f"{cert_ref}.p12"
            if cert_path.exists():
                with open(cert_path, "rb") as f:
                    return f.read()
            else:
                raise FileNotFoundError(f"Certificate {cert_ref} not found")

        elif self.storage_type == "database":
            # Recuperar de DB
            async with get_db_session() as db:
                # TODO: Implementar consulta a tabla de certificados
                pass

        elif self.storage_type == "s3":
            # TODO: Implementar S3 retrieval
            pass

        raise ValueError(f"Unsupported storage type: {self.storage_type}")

    async def _update_credentials(
        self,
        tenant_id: str,
        country: str,
        cert_ref: str,
        password: str,
        cert_info: Dict[str, Any]
    ):
        """Actualiza las credenciales de e-factura en la base de datos."""
        async with get_db_session() as db:
            # Insertar o actualizar credenciales
            await db.execute("""
                INSERT INTO einvoicing_credentials (
                    tenant_id, country, sri_cert_ref, sri_env,
                    sii_cert_ref, created_at
                ) VALUES (
                    :tenant_id, :country,
                    CASE WHEN :country = 'EC' THEN :cert_ref ELSE NULL END,
                    CASE WHEN :country = 'EC' THEN 'production' ELSE NULL END,
                    CASE WHEN :country = 'ES' THEN :cert_ref ELSE NULL END,
                    NOW()
                )
                ON CONFLICT (tenant_id, country)
                DO UPDATE SET
                    sri_cert_ref = CASE WHEN :country = 'EC' THEN :cert_ref ELSE einvoicing_credentials.sri_cert_ref END,
                    sri_env = CASE WHEN :country = 'EC' THEN 'production' ELSE einvoicing_credentials.sri_env END,
                    sii_cert_ref = CASE WHEN :country = 'ES' THEN :cert_ref ELSE einvoicing_credentials.sii_cert_ref END
            """, {
                "tenant_id": tenant_id,
                "country": country,
                "cert_ref": cert_ref
            })

            await db.commit()


# Instancia global
certificate_manager = CertificateManager()
