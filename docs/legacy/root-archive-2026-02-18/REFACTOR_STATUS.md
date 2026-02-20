# Refactor Status

> Documento consolidado del estado del refactor del proyecto GestiqCloud.
> Última actualización: Enero 2025

## Estado General

| Aspecto | Estado |
|---------|--------|
| **Fase** | En curso |
| **Fecha objetivo de cierre** | Por definir (sugerido: 3 semanas) |
| **Score actual** | 6.3/10 (Borderline production) |
| **Bloqueante principal** | Routers legacy no migrados a módulos |

---

## Módulos Migrados (Patrón Moderno)

Los siguientes 33 módulos ya están en `apps/backend/app/modules/` con estructura modular:

| # | Módulo | API HTTP | UI Tenant | UI Admin | Notas |
|---|--------|----------|-----------|----------|-------|
| 1 | accounting | ✅ | ✅ contabilidad | ❌ | |
| 2 | admin_config | ✅ | ❌ | ✅ configuracion | Solo admin |
| 3 | ai_agent | ❌ | ❌ | ❌ | Servicio interno |
| 4 | clients | ✅ | ✅ clientes | ❌ | |
| 5 | company | ✅ | ❌ | ❌ | Config en admin |
| 6 | copilot | ✅ | ✅ copilot | ❌ | |
| 7 | country_packs | ❌ | ❌ | ✅ country-packs | Solo admin |
| 8 | crm | ❌ | ✅ crm | ❌ | |
| 9 | documents | ✅ | ❌ | ❌ | Servicio interno |
| 10 | einvoicing | ✅ | 🟡 einvoicing | ❌ | Placeholder |
| 11 | expenses | ✅ | ✅ gastos | ❌ | |
| 12 | export | ✅ | ❌ | ❌ | Servicio descarga |
| 13 | finanzas | ✅ | ✅ finanzas | ❌ | |
| 14 | hr | ✅ | ✅ rrhh | ❌ | |
| 15 | identity | ✅ | ❌ | ❌ | Auth interno |
| 16 | imports | ✅ | ✅ importador | ❌ | |
| 17 | inventario | ✅ | ✅ inventario | ❌ | |
| 18 | invoicing | ✅ | ✅ facturacion | ❌ | |
| 19 | modulos | ✅ | ❌ | ✅ modulos | Solo admin |
| 20 | pos | ✅ | ✅ pos | ❌ | |
| 21 | printing | ✅ | ❌ | ❌ | Config en settings |
| 22 | production | ✅ | ✅ produccion | ❌ | |
| 23 | products | ✅ | ✅ productos | ❌ | |
| 24 | purchases | ✅ | ✅ compras | ❌ | |
| 25 | reconciliation | ✅ | 🟡 reconciliation | ❌ | Placeholder |
| 26 | registry | ✅ | ❌ | ❌ | Servicio interno |
| 27 | sales | ✅ | ✅ ventas | ❌ | |
| 28 | settings | ✅ | ✅ settings | ❌ | |
| 29 | shared | ❌ | - | - | Utilidades |
| 30 | suppliers | ✅ | ✅ proveedores | ❌ | |
| 31 | templates | ✅ | ✅ templates | ❌ | |
| 32 | users | ✅ | ✅ usuarios | ❌ | |
| 33 | webhooks | ✅ | ✅ webhooks | ❌ | |

---

## Módulos Pendientes (Routers Legacy)

Los siguientes routers en `apps/backend/app/routers/` deben migrarse al patrón modular:

| Router | Descripción | Prioridad |
|--------|-------------|-----------|
| admin_scripts.py | Scripts de administración | Media |
| admin_sector_config.py | Configuración de sectores | Media |
| admin_stats.py | Estadísticas admin | Baja |
| business_categories.py | Categorías de negocio | Alta |
| categories.py | Categorías generales | Alta |
| company_settings_public.py | Settings públicos de empresa | Media |
| company_settings.py | Settings de empresa | Alta |
| dashboard_kpis.py | KPIs del dashboard | Media |
| dashboard_stats.py | Estadísticas del dashboard | Media |
| general_listings.py | Listados generales | Baja |
| home.py | Página de inicio | Baja |
| incidents.py | Gestión de incidentes | Media |
| initial_config.py | Configuración inicial | Alta |
| migrations.py | Migraciones | Alta |
| notifications.py | Notificaciones | Alta |
| onboarding_init.py | Onboarding | Alta |
| payments.py | Pagos | Alta |
| protected.py | Rutas protegidas | Alta |
| roles.py | Gestión de roles | Alta |
| router_admins.py | Router de admins | Media |
| sector_plantillas.py | Plantillas de sector | Media |
| sectors.py | Sectores | Media |
| settings_router.py | Router de settings | Media |

**Subdirectorios pendientes:**
- `routers/admin/` - Routers específicos de admin
- `routers/tenant/` - Routers específicos de tenant

---

## UI Status (Matriz Simplificada)

### Tenant (apps/tenant)

| Estado | Módulos |
|--------|---------|
| ✅ Completo | clientes, ventas, compras, productos, inventario, facturacion, pos, gastos, finanzas, rrhh, produccion, proveedores, usuarios, settings |
| 🆕 Nuevo | copilot, templates, webhooks, crm, importador, contabilidad |
| 🟡 Placeholder | einvoicing, reconciliation |
| ❌ Sin UI (no requiere) | documents, export, identity, printing, registry (servicios internos) |

### Admin (apps/admin)

| Estado | Módulos |
|--------|---------|
| ✅ Completo | configuracion, modulos |
| 🆕 Nuevo | country-packs |
| ❌ Sin UI | La mayoría de módulos no requieren UI en admin |

---

## Criterios de Cierre

- [ ] **Routers migrados**: Todos los routers de `apps/backend/app/routers/` migrados a `modules/`
- [ ] **Tests pasando**: CI bloquea merges con tests fallando
- [ ] **Documentación actualizada**: Sin documentos ANALISIS_/RESUMEN_/TRACKING_ activos
- [ ] **CI/CD funcionando**: Deploy automático a staging en merges a main

### Criterios adicionales:

- [ ] Cobertura frontend >= 30%
- [ ] E2E con Playwright configurado (mínimo 3 flujos)
- [ ] Contratos API unificados y versionados
- [ ] Sin código legacy huérfano (electric_conflicts.py, normalize_models.py)

---

## Próximos Pasos

1. **Migrar routers de alta prioridad** - Comenzar con `payments.py`, `roles.py`, `notifications.py`
2. **Consolidar documentación** - Eliminar/archivar documentos ANALISIS_/RESUMEN_/TRACKING_
3. **Configurar E2E** - Implementar Playwright con flujos críticos (login, ventas, importación)
4. **Auditar código legacy** - Decidir sobre `electric_conflicts.py` y `normalize_models.py`
5. **Definir fecha de cierre** - Establecer deadline y responsables

---

## Referencias

- [PLAN_REMEDIACION_DEBILIDADES.md](../PLAN_REMEDIACION_DEBILIDADES.md) - Plan detallado de remediación
- [API_CENTRALIZATION_PATTERN.md](../API_CENTRALIZATION_PATTERN.md) - Patrón de API a seguir
- [GUIA_MIGRACIONES.md](../GUIA_MIGRACIONES.md) - Guía para migrar routers
