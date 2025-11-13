"""
Servicio de aplicación de plantillas de sector
Aplica configuración completa de un SectorPlantilla a un Tenant
"""

import json
import logging
from typing import Any

from app.models.empresa.empresa import SectorPlantilla
from app.models.tenant import Tenant
from app.schemas.sector_plantilla import SectorConfigJSON
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def apply_sector_template(
    db: Session,
    tenant_id: str,
    sector_plantilla_id: int,
    override_existing: bool = False,
    design_only: bool = True,
) -> dict[str, Any]:
    """
    Aplica una plantilla de sector completa a un tenant.

    Acciones realizadas:
    1. Actualiza Tenant.config_json con la configuración del sector
    2. Aplica branding (color_primario, plantilla_inicio)
    3. Crea configuración de TenantSettings
    4. Habilita/deshabilita módulos según la plantilla
    5. Crea categorías por defecto

    Args:
        db: Sesión de base de datos
        tenant_id: UUID del tenant
        sector_plantilla_id: ID de la plantilla a aplicar
        override_existing: Si True, sobreescribe configuración existente

    Returns:
        dict con resumen de cambios aplicados
    """
    try:
        logger.info(f"🎨 Aplicando plantilla de sector {sector_plantilla_id} a tenant {tenant_id}")

        # 1. Obtener plantilla de sector
        sector = db.get(SectorPlantilla, sector_plantilla_id)
        if not sector:
            raise ValueError(f"Plantilla de sector {sector_plantilla_id} no encontrada")

        # Validar template_config con Pydantic
        try:
            config = SectorConfigJSON(**sector.template_config)
        except Exception as e:
            logger.error(f"❌ Config inválido en plantilla {sector_plantilla_id}: {e}")
            raise ValueError(f"Configuración de plantilla inválida: {e}")

        # 2. Obtener tenant
        tenant = db.get(Tenant, tenant_id)
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} no encontrado")

        result = {
            "tenant_id": tenant_id,
            "sector_plantilla": sector.sector_name,
            "changes": [],
            "modules_enabled": [],
            "modules_disabled": [],
            "categories_created": [],
            "errors": [],
        }

        # 3. Actualizar configuración del tenant
        try:
            # Branding
            if config.branding.color_primario:
                tenant.primary_color = config.branding.color_primario
                result["changes"].append(f"Color primario: {config.branding.color_primario}")

            if config.branding.plantilla_inicio:
                tenant.default_template = config.branding.plantilla_inicio
                result["changes"].append(f"Plantilla inicio: {config.branding.plantilla_inicio}")
            # Guardar nombre humano de la plantilla aplicada para interfaces administrativas
            try:
                # Persistir el slug de la plantilla de sector en el campo moderno del modelo
                # Normaliza a minúsculas y sin espacios finales
                tenant.sector_template_name = (
                    (getattr(sector, "sector_name", None) or "default").strip().lower()
                )
            except Exception:
                tenant.sector_template_name = None

            # Configuración general
            if config.defaults.currency:
                tenant.base_currency = config.defaults.currency
                result["changes"].append(f"Moneda: {config.defaults.currency}")

            # Guardar template_config completo en el tenant
            if override_existing or not tenant.config_json:
                tenant.config_json = sector.template_config
                result["changes"].append("Configuración actualizada")
            else:
                # Merge parcial
                existing_config = tenant.config_json or {}
                existing_config.update(
                    {
                        "sector_template_applied": sector.sector_name,
                        "branding": config.branding.model_dump(),
                        "defaults": config.defaults.model_dump(),
                    }
                )
                tenant.config_json = existing_config
                result["changes"].append("Configuración mergeada")

            logger.info("✅ Configuración del tenant actualizada")

        except Exception as e:
            logger.error(f"Error actualizando tenant: {e}")
            result["errors"].append(f"Tenant update: {str(e)}")

        # In design-only mode, skip modules/categories/settings changes
        if design_only:
            logger.info("Design-only sector template applied (branding + slug)")
            return result

        # 4. Crear/actualizar TenantSettings
        try:
            # Buscar settings existentes
            settings = db.execute(
                text("SELECT id FROM tenant_settings WHERE tenant_id = :tid"),
                {"tid": tenant_id},
            ).scalar()

            settings_config = {
                "pos": config.pos.model_dump(),
                "inventory": config.inventory.model_dump(),
                "modules": {k: v.model_dump() for k, v in config.modules.items()},
            }

            if not settings:
                # Crear nuevo
                create_settings_sql = text(
                    """
                    INSERT INTO tenant_settings (tenant_id, settings, pos_config, locale, timezone, currency)
                    VALUES (:tenant_id, :settings, :pos_config, :locale, :timezone, :currency)
                """
                )

                db.execute(
                    create_settings_sql,
                    {
                        "tenant_id": tenant_id,
                        "settings": json.dumps(settings_config),
                        "pos_config": json.dumps(config.pos.model_dump()),
                        "locale": config.defaults.locale,
                        "timezone": config.defaults.timezone,
                        "currency": config.defaults.currency,
                    },
                )

                result["changes"].append("TenantSettings creado")
                logger.info("✅ TenantSettings creado")
            else:
                # Actualizar existente
                update_settings_sql = text(
                    """
                    UPDATE tenant_settings
                    SET settings = :settings,
                        pos_config = :pos_config,
                        locale = :locale,
                        timezone = :timezone,
                        currency = :currency,
                        updated_at = NOW()
                    WHERE tenant_id = :tenant_id
                """
                )

                db.execute(
                    update_settings_sql,
                    {
                        "tenant_id": tenant_id,
                        "settings": json.dumps(settings_config),
                        "pos_config": json.dumps(config.pos.model_dump()),
                        "locale": config.defaults.locale,
                        "timezone": config.defaults.timezone,
                        "currency": config.defaults.currency,
                    },
                )

                result["changes"].append("TenantSettings actualizado")
                logger.info("✅ TenantSettings actualizado")

        except Exception as e:
            logger.error(f"Error creando TenantSettings: {e}")
            result["errors"].append(f"TenantSettings: {str(e)}")

        # 5. Procesar módulos habilitados/deshabilitados
        for module_key, module_config in config.modules.items():
            if module_config.enabled:
                result["modules_enabled"].append(module_key)
            else:
                result["modules_disabled"].append(module_key)

        logger.info(
            f"✅ Módulos: {len(result['modules_enabled'])} habilitados, {len(result['modules_disabled'])} deshabilitados"
        )

        # 6. Crear categorías por defecto
        if config.defaults.categories:
            try:
                for category_name in config.defaults.categories:
                    # Verificar si ya existe
                    exists = db.execute(
                        text(
                            """
                            SELECT id FROM categories
                            WHERE tenant_id = :tid AND name = :name
                        """
                        ),
                        {"tid": tenant_id, "name": category_name},
                    ).scalar()

                    if not exists:
                        db.execute(
                            text(
                                """
                                INSERT INTO categories (tenant_id, name, created_at)
                                VALUES (:tenant_id, :name, NOW())
                            """
                            ),
                            {"tenant_id": tenant_id, "name": category_name},
                        )
                        result["categories_created"].append(category_name)

                if result["categories_created"]:
                    logger.info(f"✅ {len(result['categories_created'])} categorías creadas")
                    result["changes"].append(
                        f"{len(result['categories_created'])} categorías creadas"
                    )

            except Exception as e:
                logger.warning(f"⚠️ Error creando categorías: {e}")
                result["errors"].append(f"Categories: {str(e)}")

        # 7. Commit (el caller debe manejar esto)
        # db.commit()

        logger.info(
            f"✅ Plantilla '{sector.sector_name}' aplicada exitosamente a tenant {tenant_id}"
        )
        return result

    except Exception as e:
        logger.error(f"❌ Error aplicando plantilla de sector: {e}")
        raise


def get_available_templates(db: Session) -> list:
    """
    Obtiene todas las plantillas de sector disponibles.

    Returns:
        Lista de diccionarios con información de las plantillas
    """
    try:
        templates = db.query(SectorPlantilla).all()

        result = []
        for template in templates:
            # Validar y parsear template_config
            try:
                config = SectorConfigJSON(**template.template_config)

                # Contar módulos habilitados
                modules_enabled = sum(1 for mod in config.modules.values() if mod.enabled)

                result.append(
                    {
                        "id": template.id,
                        "name": template.sector_name,
                        "tipo_empresa_id": template.business_type_id,
                        "tipo_negocio_id": template.business_category_id,
                        "branding": {
                            "color_primario": config.branding.color_primario,
                            "plantilla_inicio": config.branding.plantilla_inicio,
                        },
                        "modules_count": modules_enabled,
                        "categories": config.defaults.categories,
                        "currency": config.defaults.currency,
                    }
                )
            except Exception as e:
                logger.warning(f"⚠️ Plantilla {template.id} tiene config inválido: {e}")
                continue

        return result

    except Exception as e:
        logger.error(f"Error obteniendo plantillas: {e}")
        return []


def get_template_preview(db: Session, sector_plantilla_id: int) -> dict[str, Any]:
    """
    Obtiene vista previa detallada de una plantilla.

    Returns:
        Diccionario con toda la configuración de la plantilla
    """
    try:
        sector = db.get(SectorPlantilla, sector_plantilla_id)
        if not sector:
            raise ValueError(f"Plantilla {sector_plantilla_id} no encontrada")

        config = SectorConfigJSON(**sector.template_config)

        return {
            "id": sector.id,
            "nombre": sector.sector_name,
            "tipo_empresa_id": sector.business_type_id,
            "tipo_negocio_id": sector.business_category_id,
            "config": config.model_dump(),
            "modules": {
                k: {"enabled": v.enabled, "order": v.order} for k, v in config.modules.items()
            },
        }

    except Exception as e:
        logger.error(f"Error obteniendo preview: {e}")
        raise
