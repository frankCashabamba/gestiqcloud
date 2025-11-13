# Settings Module - Sistema de Configuración Modular

Sistema completo de gestión de configuración por tenant y módulo para GestiQCloud ERP.

## Estructura

```
app/modules/settings/
├── application/
│   ├── defaults.py          # Configuración por defecto ES/EC
│   ├── modules_catalog.py   # Catálogo de módulos disponibles
│   └── use_cases.py         # SettingsManager (lógica de negocio)
└── README.md
```

## Uso Básico

### 1. Inicializar Settings para un Tenant

```python
from app.modules.settings.application.use_cases import SettingsManager

manager = SettingsManager(db)

# Crear settings con defaults según país
result = manager.init_default_settings(
    tenant_id=tenant_uuid,
    country="ES"  # o "EC"
)
```

### 2. Obtener Configuración Completa

```python
settings = manager.get_all_settings(tenant_id)

# Devuelve:
{
    "id": "uuid-settings",
    "tenant_id": "uuid-tenant",
    "locale": "es_ES",
    "timezone": "Europe/Madrid",
    "currency": "EUR",
    "modules": {
        "pos": {"enabled": True, "receipt_width_mm": 58, ...},
        "inventory": {"enabled": True, ...},
        ...
    },
    "updated_at": "2025-01-27T12:00:00Z"
}
```

### 3. Configuración de Módulo Específico

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

### 4. Habilitar/Deshabilitar Módulos

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

### 5. Listar Módulos Disponibles

```python
# Sin tenant_id (solo catálogo)
modules = manager.get_available_modules()

# Con tenant_id (incluye estado enabled)
modules = manager.get_available_modules(tenant_id)

for module in modules:
    print(f"{module['icon']} {module['name']}: {module['is_enabled']}")
```

## Defaults por País

### España (ES)

- **Moneda**: EUR
- **Timezone**: Europe/Madrid
- **IVA**: 21% (general), 10% (reducido), 4% (superreducido)
- **E-factura**: Facturae 3.2.2
- **Formato facturas**: `{year}-{series}-{number:05d}`
- **Retención IRPF**: 15%

### Ecuador (EC)

- **Moneda**: USD
- **Timezone**: America/Guayaquil
- **IVA**: 15%
- **E-factura**: SRI XML
- **Formato facturas**: `{establishment}-{point}-{number:09d}` (001-001-000000001)
- **Retenciones**: IVA (30%, 70%, 100%), IR (1%, 2%, 8%, 10%)

## Módulos Disponibles

| Módulo | Nombre | Categoría | Obligatorio | Default |
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

## Seed Script

Para crear settings por defecto para todos los tenants existentes:

```bash
# Crear settings
python scripts/seed_default_settings.py

# Solo verificar
python scripts/seed_default_settings.py --verify
```

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
settings = TenantSettings(
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
- **Auto-create**: Settings se crean automáticamente si no existen
- **Type-safe defaults**: Configuración completa para todos los módulos
- **Country-aware**: Defaults específicos para ES/EC
- **Validation**: Dependencias y módulos obligatorios validados

---

**Versión**: 1.0.0  
**Fecha**: Enero 2025  
**Mantenedor**: GestiQCloud Team
