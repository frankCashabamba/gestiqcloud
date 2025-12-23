# Settings Module - Sistema de Configuración Modular

Config multi-tenant de módulos/campos. No cubre catálogos globales (ver `admin_config`) ni permisos/roles.

## Alcance rápido
- Cubre: settings generales/branding/fiscal/POS/horarios/limites por tenant (`tenant/settings/*`), catalogo de modulos, field-config por sector/tenant (admin), theming tokens y form modes.
- No cubre: gestión de módulos obligatorios (se valida en `SettingsManager` pero no expone admin público), migraciones de datos legacy.
- Fuente de datos: `/api/v1/company/settings` y `/api/v1/tenants/{tenant_id}/settings` leen/escriben `company_settings` (alias `TenantSettings` para compat).

## Endpoints relevantes (`app/modules/settings/interface/http/tenant.py`)
- Base tenant: `/api/v1/tenant/settings/*`
  - `GET/PUT /general`, `/branding`, `/fiscal`, `/pos`, `/horarios`, `/limites`
  - `GET /fields?module=clientes&empresa=<slug>` → devuelve visibilidad/orden de campos (resuelve defaults por sector); `PUT` no expuesto en tenant (solo admin).
  - `GET /theme?empresa=<slug>` → tokens de UI (colores, logo, sector).
- Admin field-config (sin prefijo tenant): `/api/v1/admin/field-config/*`
  - `GET /sector?module=<mod>&sector=<slug>` / `PUT /sector`
  - `PUT /tenant` (override por empresa/slug), `PUT /tenant/mode` (form_mode `mixed|tenant|sector|basic`)
  - `GET /ui-plantillas` y `/ui-plantillas/health`

### Ejemplos
```
GET /api/v1/tenant/settings/general
→ 200 { "locale": "<db>", "timezone": "<db>", "currency": "<db>", ... }

PUT /api/v1/tenant/settings/pos
{ "tax": { "enabled": true, "default_rate": 0.12 }, "receipt_width_mm": 58 }
→ 200 { "ok": true }

GET /api/v1/admin/field-config/sector?module=clientes&sector=retail
→ 200 { "module":"clientes","sector":"retail","items":[{"field":"nombre","visible":true,...}, ...] }
```

### Errores comunes
- `401` si faltan claims, `403 admin_required` al modificar fiscal/pos sin `is_company_admin`, `400` si faltan `module/sector`, `404 empresa not found` en overrides por tenant.

## Modelos/DB y migraciones
- Tabla principal: `company_settings` (sustituye a la legacy `tenant_settings`, ver migración `2025-12-03_000_migrate_tenant_settings_to_company`). Field-config: `tenant_field_config`, `sector_field_default`, `tenant_module_settings`, `ui_template`.
- Repositorio principal: `SettingsRepo` (JSONB por key). Field config usa `TenantFieldConfig` y `SectorFieldDefault`.

## Flujos críticos
- `SettingsRepo.get/put` lee/escribe JSONB por clave (general/branding/fiscal/pos/horarios/limites) scoped por tenant_id (vía claims/GUC).
- `fields`: resuelve defaults por sector (`_default_fields_by_sector`) → aplica overrides de `SectorFieldDefault` → overrides por tenant (`TenantFieldConfig`).
- `theme`: compone tokens desde `ConfiguracionEmpresa` y `Tenant`, normaliza sector; si no hay branding, retorna `null`.
- `pos` y `fiscal` se usan por POS para validar impuestos y tasas configuradas.

## Dependencias y env vars
- DB (`DATABASE_URL`) con RLS (usa `ensure_rls` en montado).
- Se apoya en `app/services/field_config.py` y modelos `Tenant`, `ConfiguracionEmpresa`.
- Entornos: ver `docs/entornos.md` (RLS flags, dominios).

## Pruebas mínimas
- Feliz: `GET/PUT /general` persiste cambios; `GET /fields` devuelve config según sector; `GET /theme` entrega tokens con logo/color si empresa existe.
- Validación: `PUT /fiscal` con usuario sin `is_company_admin` → 403; `PUT /tenant` sin `module` → error.
- Auth/tenancy: llamadas sin claims → 401; overrides por empresa slug desconocido → 404.
- Estados límite: `pos.tax.default_rate` >1 se normaliza a porcentaje; `theme` con empresa sin logos retorna `null`.
- Idempotencia: `PUT` repetidos con mismo payload no cambian resultado; `GET /ui-plantillas/health` siempre `{ok: true}`.

## Consumidores y compatibilidad
- Front tenant: módulos POS/inventory/settings leen `general/fiscal/pos/fields`.
- Admin: panel de field-config usa rutas `/api/v1/admin/field-config/*`.
- Documentar nuevos campos como opcionales y reflejar en `apps/packages/api-types/settings.ts` y `docs/api-contracts.md` antes de volverlos obligatorios.

## Estructura

```
app/modules/settings/
├── application/
│   ├── modules_catalog.py   # Catálogo de módulos disponibles
│   └── use_cases.py         # SettingsManager (lógica de negocio)
└── README.md
```

## Uso Básico

### 1. Obtener Configuración Completa

```python
settings = manager.get_all_settings(tenant_id)

# Devuelve:
{
    "id": "uuid-settings",
    "tenant_id": "uuid-tenant",
    "locale": "<db>",
    "timezone": "<db>",
    "currency": "<db>",
    "modules": {
        "pos": {"enabled": True, "receipt_width_mm": 58, ...},
        "inventory": {"enabled": True, ...},
        ...
    },
    "updated_at": "2025-01-27T12:00:00Z"
}
```

### 2. Configuración de Módulo Específico

```python
# Obtener config de POS
pos_config = manager.get_module_settings(tenant_id, "pos")

# Actualizar config
manager.update_module_settings(
    tenant_id=tenant_id,
    module="pos",
    config={
        "receipt_width_mm": 80,
        "auto_print_receipt": False
    }
)
```

### 3. Habilitar/Deshabilitar Módulos

```python
# Habilitar módulo (valida dependencias)
result = manager.enable_module(tenant_id, "einvoicing")
if result["success"]:
    print(f"Módulo {result['module_name']} habilitado")
else:
    print(f"Error: {result['message']}")

# Deshabilitar módulo (valida que no haya dependientes)
result = manager.disable_module(tenant_id, "hr")
```

### 4. Listar Módulos Disponibles

```python
# Sin tenant_id (solo catálogo)
modules = manager.get_available_modules()

# Con tenant_id (incluye estado enabled)
modules = manager.get_available_modules(tenant_id)

for module in modules:
    print(f"{module['icon']} {module['name']}: {module['is_enabled']}")
```

## Módulos Disponibles

| Módulo | Nombre | Categoría | Obligatorio | Disponible |
|--------|--------|-----------|-------------|---------|
| `pos` | Punto de Venta | sales | No | ✅ |
| `inventory` | Inventario | operations | No | ✅ |
| `invoicing` | Facturación | finance | **Sí** | ✅ |
| `einvoicing` | Facturación Electrónica | finance | No | ✅ |
| `purchases` | Compras | operations | No | ✅ |
| `expenses` | Gastos | finance | No | ✅ |
| `finance` | Finanzas | finance | **Sí** | ✅ |
| `hr` | Recursos Humanos | people | No | ⬜ |
| `sales` | Ventas | sales | No | ✅ |
| `crm` | CRM | sales | No | ✅ |
| `imports` | Importaciones | operations | No | ✅ |
| `reports` | Reportes | analytics | No | ✅ |
| `manufacturing` | Fabricación | operations | No | ⬜ |
| `projects` | Proyectos | operations | No | ⬜ |
| `ecommerce` | E-Commerce | sales | No | ⬜ |

## Dependencias entre Módulos

- **POS** → requiere `inventory`, `invoicing`
- **E-invoicing** → requiere `invoicing`
- **Purchases** → requiere `inventory`
- **Sales** → requiere `inventory`, `invoicing`
- **Manufacturing** → requiere `inventory`
- **E-commerce** → requiere `inventory`, `sales`

## Ejemplo de Configuración POS

```python
{
    "enabled": True,
    "receipt_width_mm": 58,           # 58 o 80
    "print_mode": "system",            # 'system', 'escpos', 'pdf'
    "tax_included": True,
    "default_tax_rate": 0.21,
    "show_tax_breakdown": True,
    "allow_negative_stock": False,
    "require_customer_for_invoice": True,
    "return_window_days": 15,
    "store_credit": {
        "enabled": True,
        "single_use": True,
        "expiry_months": 12,
        "min_amount": 5.00
    },
    "payment_methods": ["cash", "card", "store_credit", "link"],
    "auto_print_receipt": True,
    "barcode_scanner": {
        "enabled": True,
        "mode": "camera"
    },
    "cash_drawer": {
        "enabled": False,
        "kick_code": "ESC p 0 25 250"
    }
}
```

## Validación de Dependencias

El sistema valida automáticamente:

1. **Al habilitar módulo**: Verifica que dependencias estén activas
2. **Al deshabilitar módulo**: Verifica que no haya módulos dependientes activos
3. **Módulos obligatorios**: No se pueden deshabilitar (`invoicing`, `finance`)

## Integración con RLS

Los settings son multi-tenant automáticamente:

```python
# El tenant_id está en la foreign key
settings = CompanySettings(
    tenant_id=tenant_uuid,
    settings={...}
)
```

## API REST (Próximo)

```
GET    /api/v1/settings                      # Toda la config
GET    /api/v1/settings/modules              # Módulos disponibles
GET    /api/v1/settings/modules/:module      # Config de módulo
PUT    /api/v1/settings/modules/:module      # Actualizar módulo
POST   /api/v1/settings/modules/:module/enable
POST   /api/v1/settings/modules/:module/disable
```

## Notas Técnicas

- **JSONB**: Configuración flexible y extendible
- **No hardcoded defaults**: Los valores deben existir en DB (`company_settings` / catálogos admin)
- **Validation**: Dependencias y módulos obligatorios validados

---

**Versión**: 1.0.0
**Fecha**: Enero 2025
**Mantenedor**: GestiQCloud Team
