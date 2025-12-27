"""
Servicio de aplicación de plantillas de sector
Aplica configuración completa de un SectorPlantilla a un Tenant
"""

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.company.company import SectorPlantilla
from app.models.tenant import Tenant
from app.schemas.sector_plantilla import SectorConfigJSON

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
    1. Aplica branding (color_primario, plantilla_inicio)
    2. Guarda la plantilla aplicada en CompanySettings.settings.template_config
    3. Crea configuracion de TenantSettings
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
                tenant_template_code = getattr(sector, "code", None)
                if not tenant_template_code:
                    tenant_template_code = (getattr(sector, "name", None) or "default")
                tenant.sector_template_name = str(tenant_template_code).strip().lower()
            except Exception:
                tenant.sector_template_name = None

            # Configuración general
            if config.defaults.currency:
                tenant.base_currency = config.defaults.currency
                result["changes"].append(f"Moneda: {config.defaults.currency}")

                        # Guardar template_config en CompanySettings
            try:
                from app.models.company.company_settings import CompanySettings

                company_settings = (
                    db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_id).first()
                )
                default_language = config.defaults.locale
                timezone = config.defaults.timezone
                currency = config.defaults.currency
                if not default_language:
                    raise ValueError("default_language_required")
                if not timezone:
                    raise ValueError("timezone_required")
                if not currency:
                    raise ValueError("currency_required")
                primary_color = config.branding.color_primario
                secondary_color = config.branding.color_secundario
                if not primary_color:
                    raise ValueError("primary_color_required")
                if not secondary_color:
                    raise ValueError("secondary_color_required")
                if not company_settings:
                    company_settings = CompanySettings(
                        tenant_id=tenant_id,
                        default_language=default_language,
                        timezone=timezone,
                        currency=currency,
                        primary_color=primary_color,
                        secondary_color=secondary_color,
                    )
                    db.add(company_settings)
                    db.flush()
                else:
                    if not company_settings.default_language:
                        company_settings.default_language = default_language
                    if not company_settings.timezone:
                        company_settings.timezone = timezone
                    if not company_settings.currency:
                        company_settings.currency = currency
                    if not company_settings.primary_color:
                        company_settings.primary_color = primary_color
                    if not company_settings.secondary_color:
                        company_settings.secondary_color = secondary_color

                current_settings = company_settings.settings or {}
                if not isinstance(current_settings, dict):
                    current_settings = {}
                current_settings["template_config"] = sector.template_config
                company_settings.settings = current_settings
                result["changes"].append("Template config guardado en CompanySettings")
            except Exception as e:
                logger.error(f"Error guardando template_config en CompanySettings: {e}")
                result["errors"].append(f"CompanySettings template_config: {str(e)}")

            logger.info("Tenant branding actualizado")

        except Exception as e:
            logger.error(f"Error actualizando tenant: {e}")
            result["errors"].append(f"Tenant update: {str(e)}")

        # In design-only mode, skip modules/categories/settings changes
        if design_only:
            logger.info("Design-only sector template applied (branding + slug)")
            return result

        # 4. Crear/actualizar CompanySettings
        try:
            from app.models.company.company_settings import CompanySettings

            # Buscar settings existentes
            company_settings = (
                db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_id).first()
            )

            settings_config = {
                "pos": config.pos.model_dump(),
                "inventory": config.inventory.model_dump(),
                "modules": {k: v.model_dump() for k, v in config.modules.items()},
                "defaults": config.defaults.model_dump(),
                "branding": config.branding.model_dump(),
                "template_config": sector.template_config,
            }

            default_language = config.defaults.locale
            timezone = config.defaults.timezone
            currency = config.defaults.currency
            if not default_language:
                raise ValueError("default_language_required")
            if not timezone:
                raise ValueError("timezone_required")
            if not currency:
                raise ValueError("currency_required")
            primary_color = config.branding.color_primario
            secondary_color = config.branding.color_secundario
            if not primary_color:
                raise ValueError("primary_color_required")
            if not secondary_color:
                raise ValueError("secondary_color_required")
            if not company_settings:
                # Crear nuevo
                company_settings = CompanySettings(
                    tenant_id=tenant_id,
                    default_language=default_language,
                    timezone=timezone,
                    currency=currency,
                    settings=settings_config,
                    pos_config=config.pos.model_dump(),
                    secondary_color=secondary_color,
                    primary_color=primary_color,
                    allow_custom_roles=True,
                    user_limit=10,
                    operation_type="sales",
                )
                db.add(company_settings)

                result["changes"].append("CompanySettings creado")
                logger.info("✅ CompanySettings creado")
            else:
                # Actualizar existente
                company_settings.default_language = default_language
                company_settings.timezone = timezone
                company_settings.currency = currency
                company_settings.primary_color = primary_color
                company_settings.secondary_color = secondary_color
                current_settings = company_settings.settings or {}
                if not isinstance(current_settings, dict):
                    current_settings = {}
                current_settings.update(settings_config)
                company_settings.settings = current_settings
                company_settings.pos_config = config.pos.model_dump()

                result["changes"].append("CompanySettings actualizado")
                logger.info("✅ CompanySettings actualizado")

        except Exception as e:
            logger.error(f"Error actualizando CompanySettings: {e}")
            result["errors"].append(f"CompanySettings: {str(e)}")

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
                            "color_secundario": config.branding.color_secundario,
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
