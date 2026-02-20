"""
Tenant Onboarding Service
Auto-setup de recursos necesarios al crear un tenant nuevo
"""

import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def auto_setup_tenant(
    db: Session,
    tenant_id: str,
    country: str = "EC",
    sector_template_id: str | None = None,
) -> dict:
    """
    Configura automáticamente un nuevo tenant con:
    - Series de numeración (backoffice + POS)
    - Al menos 1 registro POS por defecto
    - Configuración inicial
    - Plantilla de sector (si se proporciona)

    Args:
        db: Sesión de base de datos
        tenant_id: UUID del tenant
        country: Código país (ES/EC)
        sector_plantilla_id: ID de plantilla de sector (opcional)

    Returns:
        dict con resumen de recursos creados
    """
    try:
        logger.info(f"🚀 Auto-setup iniciado para tenant {tenant_id}")

        result = {
            "tenant_id": tenant_id,
            "pos_register_created": False,
            "series_created": [],
            "errors": [],
        }

        # 1. Crear registro POS por defecto
        try:
            default_register_name = "Caja Principal"

            existing = db.execute(
                text(
                    "SELECT id FROM pos_registers WHERE tenant_id = :tid AND name = :name LIMIT 1"
                ),
                {"tid": tenant_id, "name": default_register_name},
            ).scalar()

            if existing:
                logger.info("ℹ️ Registro POS ya existía")
                result["pos_register_id"] = existing
            else:
                create_register_sql = text(
                    """
                    INSERT INTO pos_registers (tenant_id, name, active, created_at)
                    VALUES (:tenant_id, :name, TRUE, NOW())
                    RETURNING id
                """
                )

                reg_result = db.execute(
                    create_register_sql,
                    {"tenant_id": tenant_id, "name": default_register_name},
                )

                register_id = reg_result.scalar()

                if register_id:
                    result["pos_register_created"] = True
                    result["pos_register_id"] = register_id
                    logger.info(f"✅ Registro POS creado: {register_id}")

        except Exception as e:
            logger.error(f"Error creando registro POS: {e}")
            try:
                db.rollback()
            except Exception:
                pass
            result["errors"].append(f"POS register: {str(e)}")

        # 2. Crear series de numeración
        try:
            from app.services.numbering import create_default_series

            # Series backoffice
            create_default_series(db, tenant_id, register_id=None)
            result["series_created"].append("backoffice")

            # Series POS (si se creó el registro)
            # Nota: register_id es int (serial), no UUID
            if result.get("pos_register_id"):
                create_default_series(db, tenant_id, register_id=result["pos_register_id"])
                result["series_created"].append("pos")

            logger.info(f"✅ Series creadas: {result['series_created']}")

        except Exception as e:
            logger.error(f"Error creando series: {e}")
            try:
                db.rollback()
            except Exception:
                pass
            result["errors"].append(f"Series: {str(e)}")

        # 3. Aplicar plantilla de sector (si se proporciona)
        if sector_template_id:
            try:
                from app.services.sector_templates import apply_sector_template

                logger.info(f"🎨 Aplicando plantilla de sector {sector_template_id}")
                template_result = apply_sector_template(
                    db, tenant_id, sector_template_id, override_existing=True
                )

                result["sector_template_applied"] = template_result
                logger.info(
                    f"✅ Plantilla de sector aplicada: {template_result.get('sector_plantilla')}"
                )

            except Exception as e:
                logger.error(f"Error aplicando plantilla de sector: {e}")
                try:
                    db.rollback()
                except Exception:
                    pass
                result["errors"].append(f"Sector template: {str(e)}")

        # 4. NO hacer commit - dejar que el caller lo maneje
        # db.commit()

        logger.info(f"✅ Auto-setup completado para tenant {tenant_id}")
        return result

    except Exception as e:
        logger.error(f"❌ Error en auto-setup: {e}")
        # NO hacer rollback - dejar que el caller lo maneje
        # db.rollback()
        raise


def ensure_tenant_ready(db: Session, tenant_id: str) -> bool:
    """
    Verifica si un tenant tiene la configuracion minima.
    Si no, ejecuta auto_setup_tenant.

    Returns:
        True si el tenant esta listo o se configuro exitosamente
    """
    try:
        # Verificar si existe al menos 1 registro POS
        check_sql = text(
            """
            SELECT COUNT(*) FROM pos_registers
            WHERE tenant_id = :tenant_id
        """
        )

        result = db.execute(check_sql, {"tenant_id": tenant_id}).scalar()

        if result == 0:
            logger.info(f"Tenant {tenant_id} sin configuracion, ejecutando auto-setup...")
            # Obtener pais del tenant
            country_sql = text("SELECT country FROM tenants WHERE id = :id")
            country = db.execute(country_sql, {"id": tenant_id}).scalar() or "EC"

            auto_setup_tenant(db, tenant_id, country)
            return True

        # Asegurar series de numeracion por si faltan (backoffice + POS)
        try:
            from app.services.numbering import create_default_series

            backoffice_count = db.execute(
                text(
                    """
                    SELECT COUNT(*) FROM doc_series
                    WHERE tenant_id = :tenant_id AND register_id IS NULL
                """
                ),
                {"tenant_id": tenant_id},
            ).scalar()

            if backoffice_count == 0:
                create_default_series(db, tenant_id, register_id=None)

            registers = db.execute(
                text("SELECT id FROM pos_registers WHERE tenant_id = :tenant_id"),
                {"tenant_id": tenant_id},
            ).fetchall()

            for row in registers:
                reg_id = row[0]
                reg_count = db.execute(
                    text(
                        """
                        SELECT COUNT(*) FROM doc_series
                        WHERE tenant_id = :tenant_id AND register_id = :register_id
                    """
                    ),
                    {"tenant_id": tenant_id, "register_id": reg_id},
                ).scalar()
                if reg_count == 0:
                    create_default_series(db, tenant_id, register_id=reg_id)
        except Exception as e:
            logger.error(f"Error asegurando series por tenant {tenant_id}: {e}")
            try:
                db.rollback()
            except Exception:
                pass

        return True

    except Exception as e:
        logger.error(f"Error verificando tenant ready: {e}")
        return False
