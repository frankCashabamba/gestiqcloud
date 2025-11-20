"""
Certificate Manager - Gestión de certificados digitales para e-factura

Gestiona certificados PKCS#12 (.p12/.pfx) para:
- Ecuador: SRI (Servicio de Rentas Internas)
- España: SII/AEAT (Agencia Estatal de Administración Tributaria)

Los certificados se almacenan de forma segura y se utilizan para firmar
documentos electrónicos (XML) antes de enviarlos a las autoridades fiscales.
"""

import hashlib
import os
from pathlib import Path
from typing import Any
from uuid import UUID

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import pkcs12
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.core.einvoicing import EinvoicingCredentials


class CertificateManager:
    """
    Gestiona el almacenamiento y recuperación de certificados digitales.

    Métodos:
        - store_certificate: Almacena un certificado PKCS#12
        - get_certificate: Recupera información del certificado
        - validate_certificate: Valida un certificado PKCS#12
        - delete_certificate: Elimina un certificado
    """

    def __init__(self, storage_path: str | None = None):
        """
        Inicializa el gestor de certificados.

        Args:
            storage_path: Ruta donde almacenar certificados (default: ./uploads/certificates)
        """
        self.storage_path = Path(
            storage_path or os.getenv("CERT_STORAGE_PATH", "./uploads/certificates")
        )
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def _get_cert_filename(self, tenant_id: UUID, country: str) -> str:
        """Genera nombre de archivo único para el certificado"""
        tenant_hash = hashlib.sha256(str(tenant_id).encode()).hexdigest()[:16]
        return f"{country.lower()}_{tenant_hash}.p12"

    def _get_cert_path(self, tenant_id: UUID, country: str) -> Path:
        """Obtiene la ruta completa del archivo de certificado"""
        return self.storage_path / self._get_cert_filename(tenant_id, country)

    async def validate_certificate(
        self,
        cert_data: bytes,
        password: str,
    ) -> dict[str, Any]:
        """
        Valida un certificado PKCS#12.

        Args:
            cert_data: Datos binarios del certificado
            password: Contraseña del certificado

        Returns:
            Dict con información del certificado (subject, issuer, validity)

        Raises:
            ValueError: Si el certificado es inválido
        """
        try:
            # Intentar cargar el certificado
            private_key, certificate, additional_certs = pkcs12.load_key_and_certificates(
                cert_data, password.encode("utf-8"), backend=default_backend()
            )

            if not certificate:
                raise ValueError("No se encontró certificado en el archivo P12")

            if not private_key:
                raise ValueError("No se encontró clave privada en el archivo P12")

            # Extraer información del certificado
            subject = certificate.subject.rfc4514_string()
            issuer = certificate.issuer.rfc4514_string()
            not_before = certificate.not_valid_before
            not_after = certificate.not_valid_after

            return {
                "valid": True,
                "subject": subject,
                "issuer": issuer,
                "not_before": not_before.isoformat(),
                "not_after": not_after.isoformat(),
                "has_private_key": True,
                "additional_certs_count": len(additional_certs) if additional_certs else 0,
            }

        except Exception as e:
            raise ValueError(f"Certificado inválido: {str(e)}")

    async def store_certificate(
        self,
        tenant_id: UUID,
        country: str,
        cert_data: bytes,
        password: str,
        cert_type: str = "p12",
    ) -> str:
        """
        Almacena un certificado digital.

        Args:
            tenant_id: ID del tenant
            country: Código de país ('EC' o 'ES')
            cert_data: Datos binarios del certificado
            password: Contraseña del certificado
            cert_type: Tipo de certificado (default: 'p12')

        Returns:
            Referencia del certificado almacenado

        Raises:
            ValueError: Si el certificado es inválido
            HTTPException: Si hay error al almacenar
        """
        # Validar certificado primero
        await self.validate_certificate(cert_data, password)

        # Guardar archivo físico
        cert_path = self._get_cert_path(tenant_id, country)
        try:
            with open(cert_path, "wb") as f:
                f.write(cert_data)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al guardar certificado: {str(e)}",
            )

        # Guardar referencia en base de datos
        db_gen = get_db()
        db: Session = next(db_gen)
        try:
            # Buscar credencial existente
            stmt = select(EinvoicingCredentials).where(
                EinvoicingCredentials.tenant_id == tenant_id,
                EinvoicingCredentials.country == country,
            )
            result = db.execute(stmt)
            credential = result.scalar_one_or_none()

            cert_ref = str(cert_path)
            password_hash = hashlib.sha256(password.encode()).hexdigest()

            if credential:
                # Actualizar existente
                if country == "EC":
                    credential.sri_cert_ref = cert_ref
                    credential.sri_key_ref = password_hash  # En prod usar encryption
                    credential.sri_env = os.getenv("SRI_ENV", "staging")
                elif country == "ES":
                    credential.sii_cert_ref = cert_ref
                    credential.sii_key_ref = password_hash
                    credential.sii_agency = "AEAT"
            else:
                # Crear nuevo
                new_credential = EinvoicingCredentials(tenant_id=tenant_id, country=country)
                if country == "EC":
                    new_credential.sri_cert_ref = cert_ref
                    new_credential.sri_key_ref = password_hash
                    new_credential.sri_env = os.getenv("SRI_ENV", "staging")
                elif country == "ES":
                    new_credential.sii_cert_ref = cert_ref
                    new_credential.sii_key_ref = password_hash
                    new_credential.sii_agency = "AEAT"

                db.add(new_credential)

            db.commit()
            return cert_ref

        except Exception as e:
            db.rollback()
            # Limpiar archivo si falla DB
            if cert_path.exists():
                cert_path.unlink()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al guardar en base de datos: {str(e)}",
            )
        finally:
            db.close()

    async def get_certificate(self, tenant_id: UUID, country: str) -> dict[str, Any] | None:
        """
        Recupera información del certificado.

        Args:
            tenant_id: ID del tenant
            country: Código de país

        Returns:
            Dict con información del certificado o None si no existe
        """
        db_gen = get_db()
        db: Session = next(db_gen)
        try:
            stmt = select(EinvoicingCredentials).where(
                EinvoicingCredentials.tenant_id == tenant_id,
                EinvoicingCredentials.country == country,
            )
            result = db.execute(stmt)
            credential = result.scalar_one_or_none()

            if not credential:
                return None

            cert_ref = None
            if country == "EC" and credential.sri_cert_ref:
                cert_ref = credential.sri_cert_ref
            elif country == "ES" and credential.sii_cert_ref:
                cert_ref = credential.sii_cert_ref

            if not cert_ref:
                return None

            cert_path = Path(cert_ref)
            if not cert_path.exists():
                return None

            return {
                "cert_ref": cert_ref,
                "country": country,
                "exists": True,
                "created_at": credential.created_at.isoformat() if credential.created_at else None,
            }

        finally:
            db.close()

    async def delete_certificate(self, tenant_id: UUID, country: str) -> bool:
        """
        Elimina un certificado.

        Args:
            tenant_id: ID del tenant
            country: Código de país

        Returns:
            True si se eliminó correctamente
        """
        cert_path = self._get_cert_path(tenant_id, country)

        # Eliminar archivo físico
        if cert_path.exists():
            try:
                cert_path.unlink()
            except Exception:
                pass  # Continuar aunque falle eliminar archivo

        # Eliminar referencia en DB
        db_gen = get_db()
        db: Session = next(db_gen)
        try:
            stmt = select(EinvoicingCredentials).where(
                EinvoicingCredentials.tenant_id == tenant_id,
                EinvoicingCredentials.country == country,
            )
            result = db.execute(stmt)
            credential = result.scalar_one_or_none()

            if credential:
                if country == "EC":
                    credential.sri_cert_ref = None
                    credential.sri_key_ref = None
                elif country == "ES":
                    credential.sii_cert_ref = None
                    credential.sii_key_ref = None

                db.commit()
                return True

            return False

        except Exception:
            db.rollback()
            return False
        finally:
            db.close()

    async def get_certificate_for_signing(
        self, tenant_id: UUID, country: str
    ) -> tuple[bytes, str] | None:
        """
        Obtiene el certificado y password para firma digital.

        Args:
            tenant_id: ID del tenant
            country: Código de país

        Returns:
            Tupla (cert_data, password) o None si no existe

        Note:
            En producción, el password debe estar encriptado en DB
        """
        cert_info = await self.get_certificate(tenant_id, country)
        if not cert_info:
            return None

        cert_path = Path(cert_info["cert_ref"])
        if not cert_path.exists():
            return None

        try:
            with open(cert_path, "rb") as f:
                cert_data = f.read()

            # En producción, recuperar password encriptado de DB
            # Por ahora, retornar None (el password debe pasarse en cada request)
            return (cert_data, None)  # type: ignore

        except Exception:
            return None


# Instancia global
certificate_manager = CertificateManager()
