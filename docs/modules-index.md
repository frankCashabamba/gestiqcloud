# Índice de módulos backend

Referencias rápidas por dominio. Completar detalles en README de cada módulo.

## Identidad y seguridad
- `identity`: login/refresh, perfiles, tokens. (README pendiente)
- `users`: gestión de usuarios; relaciona con roles/empresas. (README pendiente)
- `settings`: configuración de módulos/campos por tenant/sector (documentado en `app/modules/settings/README.md`).
- `modulos`: catálogo/asignación de módulos por tenant. (README pendiente)
- `admin_config`: catálogos globales (sectores, tipos negocio/empresa, países, monedas, timezones, idiomas, plantillas UI, horarios). (README pendiente)

## Core negocio
- `products`: catálogo de productos/categorías. (README pendiente)
- `sales` y `pos`: ventas, POS, recibos, pagos. (README pendiente)
- `purchases`: compras y líneas. (README pendiente)
- `expenses`: gastos. (README pendiente)
- `finanzas`: caja/bancos. (README pendiente)
- `accounting`/`contabilidad`: plan de cuentas, asientos, reportes contables. (README pendiente)
- `invoicing` y `einvoicing`: facturación y facturación electrónica. (README pendiente)
- `inventory` (inventario): stock, movimientos, alertas. (README pendiente)
- `production`: órdenes de producción, recetas. (README pendiente)
- `suppliers`: proveedores. (README pendiente)
- `clients`/`crm`: clientes, leads, oportunidades. (README pendiente)
- `templates`: plantillas email/UI/pdf. (README pendiente)
- `registry`: registro de empresas/tenants. (README pendiente)
- `export`: exportaciones. (README pendiente)
- `reconciliation`/`payments`: pagos (Stripe/Payphone/Kushki). (README pendiente)
- `webhooks`: integración saliente (documentado en `app/modules/webhooks/README.md`).

## Operaciones y AI
- `imports`: pipeline de importación (OCR/AI/preview/publish), múltiples guías internas. (README pendiente)
- `ai_agent`/`copilot`: endpoints/servicios de asistencia (si se usan). (README pendiente)
- `shared`: servicios y repositorios reutilizables. (sin README propio)

## Cómo leer cada módulo
- Estructura típica: `application/` (casos de uso), `infrastructure/` (repositorios/adapters), `interface/http` (routers), `domain/` (entidades) si aplica.
- Modelos/dto: en `schemas.py` o `domain` según módulo.
- Endpoints: `interface/http/{tenant,admin,public}.py` con prefix; montados en `app/platform/http/router.py`.
- Migraciones: verificar `alembic/versions` para cambios del módulo.

## Qué documentar en cada módulo
- Propósito y alcance: qué problema resuelve, qué no cubre.
- Endpoints expuestos (ruta, método, auth, request/response, errores comunes).
- Modelos/tablas clave y relaciones (referencias a migraciones relevantes).
- Casos de uso principales (application/use_cases) y eventos/tasks si los hay.
- Dependencias externas (servicios, colas, proveedores) y configuración/env vars.
- Checklists de pruebas (unit/integration/e2e) y datos semilla si existen.

### Boilerplate para un módulo nuevo
```
modules/<nuevo_modulo>/
├── application/
│   ├── use_cases.py      # lógica de negocio
│   ├── ports.py          # interfaces para repositorios/adapters
│   └── dto.py            # DTOs/request/response internos
├── domain/ (opcional)    # entidades de dominio
├── infrastructure/
│   └── repositories.py   # acceso a DB/externos
├── interface/http/
│   ├── tenant.py         # APIRouter prefix="/<nuevo>"
│   └── admin.py          # (si aplica) prefix="/admin/<nuevo>"
├── schemas.py            # Pydantic schemas compartidos
└── README.md             # propósito, endpoints, componentes, notas
```

## Pendientes
- Añadir README en módulos marcados como "pendiente" arriba; incluir endpoints clave, modelos principales y migraciones relevantes (`alembic/versions`).
- Enlazar contratos de API actualizados (`docs/api-contracts.md`) y tipos en `apps/packages/api-types` cuando existan.
