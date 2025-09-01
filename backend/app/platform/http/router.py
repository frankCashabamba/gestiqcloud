from fastapi import APIRouter, Depends, Response
import logging

logger = logging.getLogger("app.router")


def _mount_empresas(r: APIRouter) -> None:
    try:
        from app.modules.empresa.interface.http.admin import router as emp_admin
        r.include_router(emp_admin)  # /api/v1/admin/empresas
    except Exception as e:
        logger.debug("Skip mounting empresa admin router: %s", e)
    try:
        from app.modules.empresa.interface.http.tenant import router as emp_tenant
        r.include_router(emp_tenant)  # /api/v1/empresa
    except Exception as e:
        logger.debug("Skip mounting empresa tenant router: %s", e)

def _legacy_deprecation_dependency(response: Response):
    from app.config.settings import settings
    response.headers["Deprecation"] = "true"
    sunset = getattr(settings, "LEGACY_SUNSET", None)
    link = getattr(settings, "LEGACY_DEPRECATION_LINK", None)
    if sunset:
        response.headers["Sunset"] = str(sunset)
    if link:
        response.headers["Link"] = f"<{link}>; rel=\"deprecation\""


def _mark_router_deprecated(rt: APIRouter) -> APIRouter:
    try:
        rt.dependencies = [*getattr(rt, "dependencies", []), Depends(_legacy_deprecation_dependency)]
        for route in getattr(rt, "routes", []):
            try:
                route.deprecated = True  # type: ignore[attr-defined]
            except Exception:
                pass
    except Exception as e:
        logger.debug("Could not mark router as deprecated: %s", e)
    return rt


def build_api_router() -> APIRouter:
    """Agrega routers de todos los módulos, con fallback a paths legacy cuando aplique."""
    r = APIRouter()
    # Identity
    try:
        from app.modules.identity.interface.http.admin import router as admin_auth_router
        r.include_router(admin_auth_router, prefix="/admin")
    except Exception as e:
        try:
            from app.api.v1.admin.auth import router as admin_auth_router  # fallback
            r.include_router(admin_auth_router, prefix="/admin")
        except Exception as e2:
            logger.debug("Skip mounting admin auth routers: %s | fallback: %s", e, e2)
    try:
        from app.modules.identity.interface.http.tenant import router as tenant_auth_router
        r.include_router(tenant_auth_router, prefix="/tenant")
    except Exception as e:
        try:
            from app.api.v1.tenant.auth import router as tenant_auth_router
            r.include_router(tenant_auth_router, prefix="/tenant")
        except Exception as e2:
            logger.debug("Skip mounting tenant auth routers: %s | fallback: %s", e, e2)
    try:
        from app.modules.identity.interface.http.profile import router as me_profile_router
        r.include_router(me_profile_router)
    except Exception as e:
        try:
            from app.api.v1.profile import router as me_profile_router
            r.include_router(me_profile_router)
        except Exception as e2:
            logger.debug("Skip mounting profile routers: %s | fallback: %s", e, e2)
    # Generic auth alias (/api/v1/auth/*)
    try:
        from app.api.v1.auth import router as auth_alias_router
        r.include_router(auth_alias_router)
    except Exception as e:
        logger.debug("Skip mounting auth alias router: %s", e)
    try:
        from app.api.v1.me import router as me_router
        r.include_router(me_router)
    except Exception as e:
        logger.debug("Skip mounting me router: %s", e)
    # Telemetry (client events)
    try:
        from app.api.v1.telemetry import router as telemetry_router
        r.include_router(telemetry_router)
    except Exception as e:
        logger.debug("Skip mounting telemetry router: %s", e)
    try:
        from app.modules.identity.interface.http.sessions import router as me_sessions_router
        r.include_router(me_sessions_router, prefix="/tenant")
    except Exception as e:
        try:
            from app.api.v1.tenant.sessions import router as me_sessions_router
            r.include_router(me_sessions_router, prefix="/tenant")
        except Exception as e2:
            logger.debug("Skip mounting sessions routers: %s | fallback: %s", e, e2)
    # Productos
    try:
        from app.modules.productos.interface.http.tenant import router as productos_tenant_router
        r.include_router(productos_tenant_router)
    except Exception as e:
        logger.debug("Skip mounting productos tenant router: %s", e)
    try:
        from app.modules.productos.interface.http.admin import router as productos_admin_router
        r.include_router(productos_admin_router)
    except Exception as e:
        logger.debug("Skip mounting productos admin router: %s", e)
    # Empresas
    _mount_empresas(r)
    # Clientes
    try:
        from app.modules.clients.interface.http.tenant import router as clientes_tenant_router
        r.include_router(clientes_tenant_router)
    except Exception as e:
        logger.debug("Skip mounting clients tenant router: %s", e)
    # Modulos
    try:
        from app.modules.modulos.interface.http.admin import router as mod_admin
        r.include_router(mod_admin)
    except Exception as e:
        logger.debug("Skip mounting modulos admin router: %s", e)
    try:
        from app.modules.modulos.interface.http.tenant import router as mod_tenant
        r.include_router(mod_tenant)
    except Exception as e:
        logger.debug("Skip mounting modulos tenant router: %s", e)
    try:
        from app.modules.modulos.interface.http.public import router as mod_public
        r.include_router(mod_public)
    except Exception as e:
        logger.debug("Skip mounting modulos public router: %s", e)
    # Facturacion
    try:
        from app.modules.facturacion.interface.http.tenant import router as fact_tenant
        r.include_router(fact_tenant)
    except Exception as e:
        logger.debug("Skip mounting facturacion tenant router: %s", e)
    # Imports
    try:
        from app.modules.imports.interface.http.tenant import router as imports_tenant, legacy_router as imports_legacy
        r.include_router(imports_tenant)
        r.include_router(_mark_router_deprecated(imports_legacy), prefix="/legacy")
    except Exception as e:
        try:
            from app.modules.imports.interface.http.tenant import router as imports_tenant
            r.include_router(imports_tenant)
        except Exception as e2:
            logger.debug("Skip mounting imports routers: %s | fallback: %s", e, e2)
    # Contabilidad
    try:
        from app.modules.contabilidad.interface.http.tenant import router as contab_tenant
        r.include_router(contab_tenant)
    except Exception as e:
        logger.debug("Skip mounting contabilidad tenant router: %s", e)
    # Facturae
    try:
        from app.modules.facturae.interface.http.tenant import router as facturae_tenant
        r.include_router(facturae_tenant)
    except Exception as e:
        logger.debug("Skip mounting facturae tenant router: %s", e)
    # Importador Excel
    try:
        from app.modules.importador_excel.interface.http.tenant import router as imp_excel_tenant
        r.include_router(imp_excel_tenant)
    except Exception as e:
        logger.debug("Skip mounting importador_excel tenant router: %s", e)
    # Legacy/admin routers (migrated)
    try:
        from app.legacy.admin.settings_admin.routers import router as admin_settings_router
        r.include_router(_mark_router_deprecated(admin_settings_router), prefix="/legacy/admin")
    except Exception as e:
        logger.debug("Skip mounting legacy admin settings router: %s", e)
    try:
        from app.legacy.admin.moneda.routers import router as admin_moneda_router
        r.include_router(_mark_router_deprecated(admin_moneda_router), prefix="/legacy/admin")
    except Exception as e:
        logger.debug("Skip mounting legacy admin moneda router: %s", e)
    try:
        from app.legacy.admin.tipo_empresa.routers import router as admin_tipo_empresa_router
        r.include_router(_mark_router_deprecated(admin_tipo_empresa_router), prefix="/legacy/admin")
    except Exception as e:
        logger.debug("Skip mounting legacy admin tipo_empresa router: %s", e)
    try:
        from app.legacy.admin.tipo_negocio.routers import router as admin_tipo_negocio_router
        r.include_router(_mark_router_deprecated(admin_tipo_negocio_router), prefix="/legacy/admin")
    except Exception as e:
        logger.debug("Skip mounting legacy admin tipo_negocio router: %s", e)
    try:
        from app.legacy.admin.empresas import router as admin_empresas_router
        # Montar legacy bajo /legacy/admin para evitar colisiones con el router moderno
        r.include_router(_mark_router_deprecated(admin_empresas_router), prefix="/legacy/admin")
    except Exception as e:
        logger.debug("Skip mounting legacy admin empresas router: %s", e)
    try:
        from app.legacy.empresa import router as legacy_empresa_router
        r.include_router(_mark_router_deprecated(legacy_empresa_router), prefix="/legacy")
    except Exception as e:
        logger.debug("Skip mounting legacy empresa router: %s", e)
    # No duplicar legacy bajo /admin para evitar colisiones
    # Other legacy endpoints
    for spec in [
        ("app.legacy.routers.router_admins", "router", "/legacy"),
        ("app.legacy.routers.roles", "router", "/legacy"),
        ("app.legacy.routers.categorias", "router", "/legacy"),
        ("app.legacy.routers.listadosgenerales", "router", "/legacy"),
        ("app.legacy.routers.configuracionincial", "router", "/legacy"),
        ("app.legacy.routers.home", "router", "/ui"),
        ("app.legacy.settings.routes.configuracion_inventario", "router", "/legacy/settings"),
        ("app.legacy.usuarios.routes", "router", "/legacy/usuarios"),
        ("app.legacy.routers.protected", "router", ""),
    ]:
        try:
            mod = __import__(spec[0], fromlist=[spec[1]])
            router_obj = getattr(mod, spec[1])
            r.include_router(router_obj, prefix=spec[2])
        except Exception as e:
            logger.debug("Skip mounting legacy dynamic router %s: %s", spec[0], e)
    return r
