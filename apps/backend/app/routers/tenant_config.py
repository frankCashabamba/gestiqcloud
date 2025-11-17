"""
Tenant Configuration Router - Configuración por tenant
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.middleware.tenant import ensure_tenant

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


@router.get("/tenant")
def get_tenant_settings(db: Session = Depends(get_db), tenant_id: str = Depends(ensure_tenant)):
    """
    Obtener configuración del tenant (moneda, IVA, POS, etc.)
    """
    query = text(
        """
        SELECT
            currency,
            locale,
            timezone,
            settings,
            pos_config,
            invoice_config
        FROM tenant_settings
        WHERE tenant_id = :tenant_id
        LIMIT 1
    """
    )

    result = db.execute(query, {"tenant_id": tenant_id}).first()

    if not result:
        # Crear configuración por defecto si no existe
        insert_query = text(
            """
            INSERT INTO tenant_settings (
                tenant_id,
                currency,
                locale,
                timezone,
                settings,
                pos_config
            ) VALUES (
                :tenant_id,
                'USD',
                'es-EC',
                'America/Guayaquil',
                '{"iva_tasa_defecto": 15, "pais": "EC"}'::jsonb,
                '{"tax": {"price_includes_tax": true, "default_rate": 0.15}}'::jsonb
            )
            RETURNING currency, locale, timezone, settings, pos_config, invoice_config
        """
        )

        result = db.execute(insert_query, {"tenant_id": tenant_id}).first()
        db.commit()

    return {
        "currency": result[0],
        "locale": result[1],
        "timezone": result[2],
        "settings": result[3] or {},
        "pos_config": result[4] or {},
        "invoice_config": result[5] or {},
    }


@router.put("/tenant")
def update_tenant_settings(
    settings: dict,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(ensure_tenant),
):
    """
    Actualizar configuración del tenant
    """
    # Extraer campos permitidos
    currency = settings.get("currency")
    locale = settings.get("locale")
    timezone = settings.get("timezone")
    general_settings = settings.get("settings", {})
    pos_config = settings.get("pos_config", {})
    invoice_config = settings.get("invoice_config", {})

    # Construir UPDATE dinámicamente
    updates = []
    params = {"tenant_id": tenant_id}

    if currency:
        updates.append("currency = :currency")
        params["currency"] = currency

    if locale:
        updates.append("locale = :locale")
        params["locale"] = locale

    if timezone:
        updates.append("timezone = :timezone")
        params["timezone"] = timezone

    if general_settings:
        updates.append("settings = :settings::jsonb")
        import json

        params["settings"] = json.dumps(general_settings)

    if pos_config:
        updates.append("pos_config = :pos_config::jsonb")
        import json

        params["pos_config"] = json.dumps(pos_config)

    if invoice_config:
        updates.append("invoice_config = :invoice_config::jsonb")
        import json

        params["invoice_config"] = json.dumps(invoice_config)

    if not updates:
        raise HTTPException(400, "No settings to update")

    update_sql = f"""
        UPDATE tenant_settings
        SET {", ".join(updates)}, updated_at = NOW()
        WHERE tenant_id = :tenant_id
    """

    db.execute(text(update_sql), params)
    db.commit()

    return {"ok": True}
