"""Generic audit service for the entire system."""

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


class AuditJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for non-serializable types."""

    def default(self, obj):
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, (bytes, bytearray)):
            return obj.hex()
        return super().default(obj)


class AuditService:
    """Centralized service to register audit actions."""

    @staticmethod
    def log_action(
        db: Session,
        action_type: str,  # CREATE, UPDATE, DELETE, etc.
        entity_type: str,  # 'company', 'user', 'product', etc.
        entity_id: str | None = None,
        old_data: dict[str, Any] | None = None,
        new_data: dict[str, Any] | None = None,
        user_id: str | None = None,
        user_email: str | None = None,
        user_role: str | None = None,
        tenant_id: UUID | None = None,  # tenant UUID
        tenant_legacy_id: int | None = None,  # legacy tenant id if any
        description: str | None = None,
        notes: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,  # reservado, se guarda en props
        request_id: str | None = None,
    ) -> None:
        """Register an action in audit_log."""

        # Armar props JSONB
        props: dict[str, Any] = {
            "action_type": action_type.upper(),
            "entity_type": entity_type,
            "entity_id": entity_id,
            "user_email": user_email,
            "user_role": user_role,
            "request_id": request_id,
            "description": description,
            "notes": notes,
            "tenant_legacy_id": tenant_legacy_id,
        }
        if user_agent:
            props["user_agent"] = user_agent
        if old_data is not None:
            props["old_data"] = old_data
        if new_data is not None:
            props["new_data"] = new_data

        payload = {
            "tenant_id": str(tenant_id) if tenant_id else None,
            "source": entity_type,
            "name": action_type.lower(),
            "user_id": str(user_id) if user_id is not None else None,
            "ip": ip_address,
            "props": json.dumps(props, cls=AuditJSONEncoder),
        }

        sql = text("""
            INSERT INTO audit_log (tenant_id, source, name, user_id, ip, props)
            VALUES (:tenant_id, :source, :name, :user_id, :ip, CAST(:props AS jsonb))
            """)

        try:
            db.execute(sql, payload)
            db.commit()
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass

    @staticmethod
    def _calculate_changes(
        old_data: dict[str, Any], new_data: dict[str, Any]
    ) -> dict[str, dict[str, Any]]:
        """Calcula los campos que cambiaron entre old_data y new_data."""
        changes: dict[str, dict[str, Any]] = {}

        # Buscar campos modificados
        all_keys = set(old_data.keys()) | set(new_data.keys())
        for key in all_keys:
            old_value = old_data.get(key)
            new_value = new_data.get(key)
            if old_value != new_value:
                changes[key] = {"old": old_value, "new": new_value}
        return changes

    @staticmethod
    def log_delete_company(
        db: Session,
        company_data: dict[str, Any],
        related_data: dict[str, Any],  # {'users': [...], 'products': [...], etc.}
        user_id: int | None = None,
        user_email: str | None = None,
        user_role: str = "admin",
        ip_address: str | None = None,
        tenant_uuid: UUID | None = None,
        tenant_legacy_id: int | None = None,
    ) -> None:
        """Helper to register company deletion with cascades."""

        # Registro de empresa borrada
        AuditService.log_action(
            db=db,
            action_type="DELETE",
            entity_type="company",
            entity_id=str(tenant_legacy_id) if tenant_legacy_id is not None else None,
            old_data={
                "company": company_data,
                "related_entities": {k: len(v) for k, v in related_data.items()},
            },
            user_id=str(user_id) if user_id is not None else None,
            user_email=user_email,
            user_role=user_role,
            tenant_id=tenant_uuid,
            tenant_legacy_id=tenant_legacy_id,
            description=f'Company "{company_data.get("name")}" deleted with '
            f"{sum(len(v) for v in related_data.values())} related records",
            ip_address=ip_address,
        )

        # Registros de cascada
        for etype, entities in related_data.items():
            if not entities:
                continue
            AuditService.log_action(
                db=db,
                action_type="DELETE",
                entity_type=f"company_cascade_{etype}",
                old_data={"items": entities, "count": len(entities)},
                user_id=str(user_id) if user_id is not None else None,
                user_email=user_email,
                user_role=user_role,
                tenant_id=tenant_uuid,
                tenant_legacy_id=tenant_legacy_id,
                description=f"{len(entities)} registro(s) de {etype} eliminados en cascada",
                ip_address=ip_address,
            )


def serialize_model(obj: Any) -> dict[str, Any]:
    """Serializa un modelo SQLAlchemy a dict JSON-compatible."""
    if obj is None:
        return {}

    result: dict[str, Any] = {}

    if hasattr(obj, "__table__"):
        for column in obj.__table__.columns:
            value = getattr(obj, column.name, None)
            if isinstance(value, datetime):
                result[column.name] = value.isoformat()
            elif isinstance(value, UUID):
                result[column.name] = str(value)
            elif isinstance(value, (bytes, bytearray)):
                result[column.name] = value.hex()
            else:
                result[column.name] = value

    return result
