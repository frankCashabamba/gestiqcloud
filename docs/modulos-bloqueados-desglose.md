# Modulos Bloqueados - Desglose Tecnico

Fecha: 2026-05-01
Ultima revision: 2026-05-01, contrastada contra el codigo local.
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

1. Conectar todos los nombres de Celery y flujos de endpoint al worker XAdES real.
2. Unificar SII: el endpoint de export usa un flujo de FacturaE y el envio SII usa otro XML.
3. `workers/einvoicing_tasks.py` sigue fijando `<ambiente>` SRI en `"1"` dentro del XML generado; el entorno debe venir de settings del tenant.
4. Falta UI y endpoint operativo para crear/actualizar `EInvoicingCountrySettings` y subir certificado `.p12` por tenant.
5. Sin certificado real BCE/FNMT y pruebas sandbox homologadas no es operable legalmente.

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

1. Asientos automaticos incompletos: `expenses` integra `create_posted_entry()`, pero ventas, compras, POS/caja y cierres no contabilizan automaticamente todo el ciclo.
2. Falta cierre/apertura/regularizacion contable.
3. Permisos granulares contables siguen pendientes.
4. Los reportes son tecnicamente utiles, pero solo reflejan lo contabilizado; sin automatismos quedan parciales.

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

1. `SalesReportGenerator` y `ReportContext` siguen consultando `sales_orders`; si esa tabla no coincide con el flujo real, el reporte falla o no representa ventas/POS reales.
2. Falta Celery beat para scheduled reports y recalculo nocturno de snapshots.
3. Falta validar migraciones de `reports`/`scheduled_reports` en deploy.
4. Reportes avanzados grandes pueden seguir cargando memoria si se usan fuera de los limites ya parcheados.

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

1. No existe flujo de quotes/proformas: borrador -> aprobacion -> conversion a venta/factura.
2. No hay SpainPack/EspanaPack ni validacion fiscal espanola.
3. No hay frontend tenant dedicado de Documents/Quotes; hoy esta integrado parcialmente desde billing/POS.

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

1. Cierre/cobro real no existe; debe integrarse con POS, caja y facturacion.
2. `tax_total = 0.0` sigue hardcodeado.
3. Sin KDS real.
4. La busqueda de productos no filtra menu/venta; puede mostrar materias primas.
5. El codigo posterior al `raise HTTPException(501)` en `close_order` queda inaccesible y no debe considerarse flujo valido.

### Decision

No activar para produccion. Mantener como beta oculta hasta integrar POS/facturacion, impuestos y KDS.

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

1. Sin feedback de progreso en frontend para uploads largos.
2. El procesamiento pandas sigue en thread pool de Uvicorn; para volumen alto conviene Celery/background job.

### Decision

Listo para beta. No esta bloqueado por seguridad core, pero no debe venderse como importador masivo avanzado hasta mejorar progreso y carga en background.

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
3. `complete_production` usa fallback de `user_id` al `order_id` para crear gasto de produccion si no hay `user_id`; conviene fallar claro o registrar usuario de sistema.
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
| 3 | Restaurant | Mantener manifest deshabilitado y bloquear cualquier exposicion de close/cobro |
| 4 | Accounting | Definir automatismos minimos de asientos para ventas, compras y caja |
| 5 | Production | Anadir/ejecutar tests de ciclo completo con stock, lote, merma y gasto |

### Media

| # | Modulo | Accion |
|---|--------|--------|
| 6 | Reconciliation | Implementar upload CSV/OFX y validar payloads reales de proveedores |
| 7 | Reports | Implementar Celery beat para schedules y recalculo nocturno |
| 8 | Documents | Implementar SpainPack y flujo Quotes/Proformas |
| 9 | Historical | Progreso frontend y background job para cargas grandes |
| 10 | Analytics | Definir alcance de producto o dejarlo oculto |

### Baja / externa

| # | Modulo | Accion |
|---|--------|--------|
| 11 | Einvoicing | Gestion de certificados BCE/FNMT por tenant |
| 12 | AI Agent | Sandbox aislada para auto-resolve |
| 13 | Restaurant | KDS y filtro de menu/productos vendibles |

### Bloqueantes externos

- Certificados fiscales por tenant para Ecuador/Espana.
- Homologacion/pruebas con SRI/SII/AEAT donde aplique.
- Workers Celery/beat activos en deploy para webhooks, reports, notifications y tareas programadas.
