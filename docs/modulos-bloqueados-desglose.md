# Modulos Bloqueados - Desglose Tecnico

Fecha: 2026-05-01
Ultima revision: 2026-05-01, recontrastada contra codigo real por 8 agentes de auditoria paralelos.
Fuente: auditoria de rutas, servicios, workers, manifests frontend y tests existentes.

Este documento lista los modulos que no deben venderse como productivos completos todavia. Distingue entre bloqueos de implementacion, bloqueos operativos y trabajo de pruebas pendiente.

---

## Resumen Ejecutivo

| Modulo | Estado actual | Esfuerzo | Riesgo principal |
|--------|---------------|----------|------------------|
| Einvoicing | Parcial; worker XAdES real existe, tasks legacy fallan cerrado | Grande + externo | Flujo fiscal real no conectado de punta a punta |
| Accounting | CRUD, libro mayor, P&G y balance implementados | Mediano | Contabilidad incompleta sin asientos automaticos de ventas/compras/caja |
| Reconciliation | Matching y pagos funcionales, webhooks fallan cerrado | Mediano | Upload bancario real y validacion contra payloads reales pendientes |
| Reports | Generadores basicos y snapshots; schedules cerrados por defecto | Mediano | `SalesReportGenerator` sigue usando `sales_orders`; schedules sin beat |
| Documents/Quotes | Documentos Ecuador y storage accesible; sin quotes | Pequeno-Mediano | Sin soporte Espana ni flujo proforma/presupuesto |
| AI Agent | Analisis y notificaciones reales si hay credenciales; mocks peligrosos desactivados | Mediano | Auto-resolve sin sandbox real |
| Restaurant | Router montado y CRUD funcional; manifest deshabilitado | Grande | Sin caja/facturacion/impuestos/KDS |
| Analytics | KPIs backend protegidos; sin UI tenant dedicada | Pequeno-Mediano | API visible sin producto funcional cerrado |
| Historical | Listo para beta, no bloqueado por seguridad core | Pequeno | UX de progreso y control de carga masiva pendientes |
| Production | Candidato beta, no bloqueado por ciclo core | Pequeno-Mediano | Requiere pruebas integradas de stock, lote, merma y asiento de gasto |

---

## 1. Einvoicing

### Implementado

- Router tenant con export, envio SII, envio SRI, status, RIDE y retry.
- `SIIService` y `SRIService` con validaciones y llamadas HTTP reales.
- Worker fiscal en `app/workers/einvoicing_tasks.py` con firma XAdES-BES, carga de P12, clave de acceso SRI y polling.
- Tasks legacy en `app/modules/einvoicing/tasks.py` ya no simulan `AUTHORIZED`/`ACCEPTED`; fallan con `TASK_DISABLED`.
- `infrastructure/einvoice_service.py` ya no genera firma SHA256 falsa ni PDF placeholder.

### Falta o esta roto

1. [HECHO 2026-05-01] Helper `_sri_ambiente_code` en `workers/einvoicing_tasks.py` parametriza el entorno SRI desde `EInvoicingCountrySettings.environment` (PRODUCTION→"2", otros→"1"). El modelo unificado es `EInvoicingCountrySettings`, no `SRISettings`.
2. [HECHO 2026-05-01] Endpoints `GET/PUT /admin/companies/{tenant_id}/einvoicing/{sri,sii}/settings` y `POST .../certificate` implementados en `einvoicing/interface/http/admin.py`; secretos y certificados no se exponen en response (solo `has_password: bool`, `has_certificate: bool`).
3. Export SII (FacturaE) y envio SII son flujos distintos por diseño: export = descarga XML local, send = envio real a SII via `SIIService.send_to_sii()`. Legacy `build_and_send_sii` deshabilitado. Separacion aceptable.
4. [PENDIENTE arquitectura] SRI usa Celery async + polling (`sign_and_send_sri_task`); SII usa llamada sincrona en endpoint `POST /send-sii`. Si el servidor SII tarda, bloquea el worker uvicorn. Evaluar mover envio SII a Celery.
5. Sin certificado real BCE/FNMT y pruebas sandbox homologadas no es operable legalmente. (Bloqueante externo)

### Decision

No activar en produccion real. Mantener en sandbox/demo interno hasta cerrar configuracion por tenant, certificado, ambiente y worker real.

---

## 2. Accounting

### Implementado

- CRUD de plan de cuentas y asientos.
- Contabilizacion de asientos y recalculo de saldos.
- Libro mayor por cuenta desde backend.
- Reportes P&G y Balance de Situacion desde backend, con rango acotado.
- Frontend actualizado para libro mayor, P&G y balance.
- Bug de `status` shadowing corregido con alias externo `status` y variable interna `entry_status`.

### Falta o esta roto

1. [HECHO 2026-05-01, verificado] Asientos automaticos hookeados en ventas (`post_sale_entry` en `sales/application/journal.py`: confirm + mark_paid, idempotente) y compras (`post_purchase_entry` en `purchases/application/journal.py`: recepcion, idempotente). [PENDIENTE estructural] `post_cash_movement_entry` en `finance/application/journal.py` esta implementada e idempotente, pero no existe ningun endpoint `POST /finance/cashbox/movements` ni ninguna creacion de `CashMovement` en el codebase; `CashMovementCreate` schema existe sin usar. El hookeo requiere primero crear la feature de registro de movimientos de caja.
2. [HECHO 2026-05-01, verificado] Cierre/apertura/regularizacion con modelo `AccountingPeriod` (`models/accounting/period.py`) y endpoints `POST /periods/close|open|regularize`. `create_posted_entry` rechaza con 409 `periodo_cerrado` via `assert_period_open()`.
3. [HECHO 2026-05-01, verificado] Permisos granulares aplicados en handlers. Excepcion: permiso `accounting.entry.cancel` esta definido en `permissions.py` e importado en `tenant.py` pero no existe endpoint de cancelacion de asientos.
4. POS sigue construyendo `AsientoContable` directo en `shifts.py`; no migrado a `create_posted_entry`. Inconsistencia de patron con el resto del modulo.

### Decision

Permitir solo configuracion basica y POS accounting protegido. No vender como contabilidad completa.

---

## 3. Reconciliation

### Implementado

- Router tenant con importar/listar/detalle/lineas/auto-match/match manual/summary/pending.
- Matching por referencia exacta y por monto con ventana temporal.
- RLS en rutas tenant y rutas autenticadas de pagos.
- Webhooks Stripe, Kushki y PayPhone fallan cerrado si falta secret o firma.
- JSON invalido en webhook devuelve error explicito.
- Refund endpoint registra reembolsos.

### Falta o esta roto

1. No hay upload CSV/OFX de extractos bancarios: el endpoint `POST /statements` recibe JSON ya parseado.
2. Falta validar webhooks contra payloads reales de Stripe, Kushki y PayPhone en entorno de proveedor.
3. Falta prueba de integracion con Postgres/RLS activo.
4. Modelo y experiencia de conciliacion siguen separados de Finance.

### Decision

No activar como modulo productivo completo. Puede quedar en beta interna o feature flag.

---

## 4. Reports

### Implementado

- Endpoints de generacion, listado, export y reportes sales/inventory/financial.
- Exportadores CSV/JSON/Excel/PDF/HTML.
- Router tenant con `ensure_rls`.
- Rango maximo de 366 dias en endpoints tenant principales.
- `POST /reports/schedule` cerrado por defecto salvo `REPORTS_SCHEDULER_ENABLED=true`.
- Respuesta de generacion indica `persisted: false` si la tabla `reports` no esta disponible.
- Profit snapshots con `GET /reports/profit` y `POST /reports/recalculate`; frontend de resultado real consume esos endpoints.

### Falta o esta roto

1. [HECHO 2026-05-01, verificado] `sales_orders` confirmada como tabla canonica (coincide con `SalesOrder.__tablename__`). [BUG POTENCIAL] El SQL crudo en `SalesReportGenerator` (~linea 49 de `report_generator.py`) usa columna `quantity` pero el ORM `SalesOrderItem` declara `qty`; puede fallar con `OperationalError` en runtime. El propio codigo tiene comentario de advertencia. Requiere alinear SQL a `qty`/`line_total`.
2. [HECHO 2026-05-01, verificado] Celery beat `process-scheduled-reports` (cada 5 min) y `recalculate-profit-snapshots-nightly` (03:00 UTC) registrados en `celery_app.py` bajo `REPORTS_SCHEDULER_ENABLED`.
3. [HECHO 2026-05-01, verificado] Migracion `2026-05-01_003_reports_tables` con tablas `reports` y `scheduled_reports` + RLS policies verificada en `ops/migrations/`.
4. [PENDIENTE] `reports_tasks.py` no se importa explicitamente en `_import_task_modules()` de `celery_app.py`; verificar que las tasks se registren al arrancar antes de activar el scheduler.
5. Reportes avanzados (aging, cashflow) pendientes. Reportes grandes pueden seguir cargando memoria fuera de limites parcheados.

### Decision

Habilitar solo reportes simples acotados y snapshots bajo demanda. No activar schedules ni reportes avanzados como producto cerrado.

---

## 5. Documents / Quotes

### Implementado

- Pipeline draft/issue para documentos de venta con `EcuadorPack`.
- Render HTML y almacenamiento en `document_storage`.
- Router `document_storage` montado bajo `/tenant`.
- RLS y tenant scope en rutas de documentos.
- Falla cerrado con `documents_country_not_supported` para paises distintos de Ecuador.

### Falta o esta roto

1. [HECHO 2026-05-01, verificado] Flujo quotes completo: modelo `Quote` (DRAFT/APPROVED/CONVERTED/REJECTED/EXPIRED/CANCELLED), endpoints CRUD en `/tenant/quotes` con permiso `quotes.manage`, y `quote_to_sales_order` en `shared/services/document_converter.py`. El modelo tiene dos estados adicionales (`EXPIRED`, `CANCELLED`) no contemplados en el plan original.
2. [HECHO 2026-05-01, verificado] `EspanaPack` en `modules/country_packs/espana.py` con validacion NIF/NIE/CIF (letra de control) y tasas IVA 21/10/4/0 + EUR. Orchestrator acepta EC y ES; otros paises devuelven `documents_country_not_supported`.
3. [HECHO 2026-05-01, verificado] Frontend `apps/tenant/src/modules/quotes/` con `QuotesList`, `QuoteForm`, `QuoteDetail`, `Routes`, `manifest.ts`, `api.ts`. Router `document_storage` y router `quotes` montados en `platform/http/router.py`.

### Decision

No ofrecer presupuestos ni validacion fiscal multi-pais en v1. Ecuador interno puede avanzar con cautela si se valida fiscalmente.

---

## 6. AI Agent

### Implementado

- Analisis de incidentes con `AIService`.
- Sugerencia de fixes.
- Notificaciones por email, WhatsApp/Twilio, Telegram y Slack si hay credenciales.
- Mocks peligrosos desactivados: sin credenciales o proveedor IA falla explicitamente.
- Sin destinatarios hardcodeados para WhatsApp/Telegram.
- Acceso principalmente desde soporte/admin.

### Falta o esta roto

1. `auto_resolve_incident()` no tiene sandbox aislada para ejecutar cambios de forma segura.
2. Falta control robusto de destinatarios por tenant/equipo.
3. Falta politica de permisos y auditoria para acciones automáticas.

### Decision

Mantener desactivado para tenants. Como maximo, uso admin interno con credenciales reales y sin auto-resolve.

---

## 7. Restaurant

### Implementado

- Router tenant montado bajo `/tenant/restaurant`.
- CRUD de mesas, comandas e items.
- Send-to-kitchen basico.
- RLS en router.
- Frontend de mesas y comanda.
- Manifest frontend con `enabled: false`.
- `POST /orders/{id}/close` devuelve 501 por la integracion pendiente de POS/facturacion.

### Falta o esta roto

1. Cierre/cobro real no existe; `POST /orders/{id}/close` devuelve 501 hasta integrar POS, caja y facturacion.
2. [HECHO 2026-05-01, verificado] `_recalculate_order_totals` calcula impuestos por producto via `product.tax_rate` con fallback `resolve_tenant_default_tax_rate()`. Ya no usa 0.0 hardcodeado.
3. [HECHO 2026-05-01, verificado] KDS basico: `GET /kds/orders`, `POST /kds/items/{id}/ready|served` en backend; `KDSView.tsx` con polling 5s en frontend; ruta `/restaurant/kds` registrada en `Routes.tsx` con `ProtectedRoute(restaurant.kds.view)`.
4. [HECHO 2026-05-01, verificado] `GET /tenant/restaurant/menu` filtra vendibles (`active=true`, `is_raw_material=false`); `MenuPicker.tsx` consumido por `OrderView.tsx`. `add_order_item` valida y devuelve 400 `product_not_sellable`.
5. [HECHO 2026-05-01, verificado] Codigo muerto eliminado de `close_order`; manifests unificados con `enabled:false` en `module.json` y `manifest.ts`.
6. [HECHO] Permisos KDS aplicados: `PERM_RESTAURANT_KDS_VIEW` y `PERM_RESTAURANT_KDS_MANAGE` agregados a `permissions.py`; `require_permission()` aplicado como `dependencies=` en los 3 endpoints KDS de `restaurant/interface/http/tenant.py`.

### Decision

No activar para produccion. Candidato beta cuando se cierre integracion POS/facturacion para reemplazar el 501 de close y se corrija enforcement de permisos KDS.

---

## 8. Historical

### Implementado

- Router completo de imports, upload y consultas historicas.
- RLS en router.
- Upload CSV/XLSX delegado a `asyncio.to_thread` con sesion SQLAlchemy dedicada.
- Limite de archivo de 10 MB.
- Deduplicacion fuerte por SHA-256 en `file_hash`.
- Fechas faltantes fallan con `missing_fecha`.
- Errores de upsert de maestros quedan en logs con `logger.warning(..., exc_info=True)`.

### Falta o esta roto

1. [HECHO 2026-05-01] `UploadPage.tsx` muestra progreso de carga y estado de procesamiento posterior al upload para evitar re-subidas por falta de feedback.
2. El procesamiento pandas sigue en thread pool de Uvicorn; para volumen alto conviene Celery/background job.

### Decision

Listo para beta. No esta bloqueado por seguridad core, pero no debe venderse como importador masivo avanzado hasta mover cargas pesadas a background/Celery.

---

## 9. Analytics

### Implementado

- Endpoint `dashboard/kpis` con queries por sector.
- Router admin stats.
- Scope tenant/admin y RLS donde aplica.
- Migraciones de profit snapshots usadas por reports.

### Falta o esta roto

1. No existe modulo frontend `analytics/` dedicado.
2. Ningun componente tenant consume `/api/v1/tenant/dashboard/kpis` como producto de analytics.
3. Falta definicion funcional, permisos especificos y pruebas con datos reales.

### Decision

No registrar como modulo productivo. Mantener oculto por feature flag o integrarlo como KPIs internos hasta cerrar alcance.

---

## 10. Production

### Implementado

- Router tenant montado bajo `/tenant/production`.
- Recetas, ingredientes, costos, cost drivers, periodos y pasos.
- Ordenes con estados `DRAFT`, `SCHEDULED`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`.
- `start`, `complete` y `cancel`.
- Al completar: consume ingredientes con `StockMove(kind="production_consume")`, crea output con `StockMove(kind="production_output")`, actualiza `StockItem`, asigna lote/batch y registra merma en la orden.
- Frontend de ordenes expone iniciar, completar, cancelar, cantidad producida, merma, motivo y batch.

### Falta o esta roto

1. Falta evidencia de tests integrados del flujo completo: receta -> orden -> start -> complete -> consumo stock -> stock terminado -> lote -> merma.
2. Falta validar que el warehouse resuelto sea correcto para todos los sectores y que no cree stock negativo no deseado.
3. [HECHO 2026-05-01] `complete_production` ya no usa fallback de `user_id` al `order_id`; si falta o es invalido devuelve 401 `production_completion_requires_user`.
4. El asiento/gasto de produccion se intenta crear, pero si falla no bloquea la orden; esto es aceptable para operacion, pero deja coste/contabilidad incompleta si no se monitorea.

### Decision

Candidato beta, no bloqueado por implementacion core. Antes de v1 requiere pruebas de regresion de inventario, lote, merma y coste.

---

## Plan de Accion por Prioridad

### Alta

| # | Modulo | Accion |
|---|--------|--------|
| 1 | Einvoicing | Conectar tasks Celery publicas al worker XAdES real y parametrizar ambiente SRI |
| 2 | Reports | Corregir fuente de ventas (`sales_orders` vs flujo real POS/facturas) |
| 3 | Restaurant | Mantener manifest deshabilitado y close/cobro bloqueado hasta integracion POS/facturacion |
| 4 | Accounting | Definir automatismos minimos de asientos para ventas, compras y caja |
| 5 | Production | Anadir/ejecutar tests de ciclo completo con stock, lote, merma y gasto |

### Media

| # | Modulo | Accion |
|---|--------|--------|
| 6 | Reconciliation | Implementar upload CSV/OFX y validar payloads reales de proveedores |
| 7 | Reports | Implementar Celery beat para schedules y recalculo nocturno |
| 8 | Documents | Implementar SpainPack y flujo Quotes/Proformas |
| 9 | Historical | Background job para cargas grandes |
| 10 | Analytics | Definir alcance de producto o dejarlo oculto |

### Baja / externa

| # | Modulo | Accion |
|---|--------|--------|
| 11 | Einvoicing | Gestion de certificados BCE/FNMT por tenant |
| 12 | AI Agent | Sandbox aislada para auto-resolve |
| 13 | Restaurant | KDS y catalogo/menu dedicado si se activa como modulo real |

### Bloqueantes externos

- Certificados fiscales por tenant para Ecuador/Espana.
- Homologacion/pruebas con SRI/SII/AEAT donde aplique.
- Workers Celery/beat activos en deploy para webhooks, reports, notifications y tareas programadas.
