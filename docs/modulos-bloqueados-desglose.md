# Módulos Bloqueados — Desglose Técnico

Fecha: 2026-04-30
Última revisión: 2026-04-30 (auditoría completa de código sobre commit actual, main)
Fuente: auditoría de código sobre commit actual (main)

Este documento detalla qué falta exactamente en cada módulo bloqueado para llegar a producción,
con estimación de esfuerzo y riesgos reales si se activara hoy.

---

## Resumen ejecutivo

| Módulo         | Estado                                              | Esfuerzo               | Riesgo principal                                          |
|----------------|-----------------------------------------------------|------------------------|-----------------------------------------------------------|
| Einvoicing     | Parcial (firma XAdES real, tasks legacy cerrados)   | Grande + externo       | Worker fiscal real no conectado a todos los flujos        |
| Accounting     | CRUD funcional, faltan reportes y asientos automáticos | Mediano             | Contabilidad incompleta; bug de variable `status`         |
| Reconciliation | Funcional pero sin verificación de firma webhook    | Mediano                | Cualquiera puede marcar facturas como pagadas vía webhook  |
| Reports        | 3 generadores funcionales, scheduled sin Celery     | Mediano                | Reportes programados nunca se ejecutan                    |
| Documents/Quotes | Funcional solo para Ecuador, sin quotes           | Pequeño-Mediano        | Documentos España con formato Ecuador incorrecto          |
| AI Agent       | Funcional con credenciales, auto-resolve es mock    | Mediano                | Incidentes marcados como resueltos sin serlo              |
| Restaurant     | Router montado; CRUD funcional, sin integración fiscal/caja | Grande           | Comandas no generan comprobante fiscal; impuestos a cero  |
| Historical     | Funcional, RLS+async+hash dedupe completos; pendiente UX progreso | Pequeño     | Sin feedback progreso en frontend; riesgo de re-upload    |
| Analytics      | Backend KPIs por sector implementados, sin frontend | Pequeño-Mediano        | API disponible pero sin UI tenant que la consuma          |

---

## 1. Einvoicing

### A) Qué está implementado

- Router completo con endpoints: `GET /facturae/{id}/export`, `POST /send-sii`, `POST /sri/send`, `GET /sri/{id}/status`, `GET /sri/{id}/ride`, `POST /einvoice/{id}/retry`.
- `SIIService` (España): validación CIF/NIF, XML básico, envío HTTP real, parsing SOAP.
- `SRIService` (Ecuador): validación RUC/cédula con algoritmo módulo 11, envelopes SOAP para `RecepcionComprobantesOffline` y `AutorizacionComprobantesOffline`.
- Firma XAdES-BES real en `app/workers/einvoicing_tasks.py`: carga P12, RSA-SHA256, C14N, `xades:QualifyingProperties` — implementación técnicamente correcta.
- Generación de `clave_acceso` de 49 dígitos con módulo 11.
- Celery tasks con retry exponencial y circuit-breaker en `tasks.py`.
- Frontend: `EInvoicingDashboard.tsx`, pantalla de estado y envío.

### B) Qué falta o está roto

1. **[PARCHEADO 2026-04-30] Tasks legacy ya no simulan éxito fiscal**: `einvoicing/tasks.py` ya no marca SRI como `AUTHORIZED` ni SII como `ACCEPTED`; ahora falla explícitamente con `TASK_DISABLED`. Sigue pendiente conectar los nombres de Celery al worker XAdES real.

2. **[PARCHEADO 2026-04-30] `infrastructure/einvoice_service.py` ya no firma fake**: `sign_xml()` ahora lanza `NotImplementedError` en vez de marcar como firmado un SHA256 que no es firma XML válida. Sigue pendiente conectar siempre con el worker XAdES real.

3. **[PARCHEADO 2026-04-30] PDF legacy desactivado explícitamente**: `export_to_pdf()` ya no usa `pdf_buffer = None`; ahora lanza `NotImplementedError` y fuerza usar el pipeline de renderizado de documentos.

4. **XML SII incorrecto**: `SIIService.generate_xml()` genera `<factura version="3.2.1">` sin la estructura real de FacturaE 3.2.1 (`<FileHeader>`, `<Parties>`, etc.). `facturae_xml.py` sí implementa el formato real pero solo lo usa el endpoint de export, no el de envío SII.

5. **Campo `<ambiente>` hardcodeado**: `workers/einvoicing_tasks.py` línea 101 fija `ambiente = "1"` (pruebas) en el XML SRI. El campo `env` llega del request al endpoint `/sri/send` pero NO se propaga al worker XAdES; facturas reales siempre se envían al entorno de pruebas del SRI. Verificado en auditoría 2026-04-30.

6. **Sin UI para certificado digital**: no hay pantalla para subir el `.p12` del tenant. Solo existe una clave i18n `certUploaded` en `settings.json` sin componente React asociado. La firma XAdES-BES necesita `cert_data["p12_base64"]` desde `EInvoicingCountrySettings`, que no tiene formulario de creación.

7. **`EInvoicingCountrySettings` no tiene endpoint de creación**: si el tenant no tiene settings, `POST /sri/send` devuelve HTTP 422 "SRI settings not configured" sin guía de resolución. No existe ningún endpoint `POST /einvoicing/settings` ni similar. Verificado en auditoría 2026-04-30.

### C) Estimación de esfuerzo

**Grande (semanas) + Bloqueante-externo**: La firma XAdES-BES existe pero requiere pruebas reales con el SRI sandbox. Cada tenant necesita certificado digital emitido por el BCE (Ecuador) o FNMT (España) — proceso externo de días a semanas.

### D) Riesgos si se activa hoy

- Los tasks legacy ya no autorizan en falso; quedan desactivados hasta conectar el worker XAdES real.
- Campo `<ambiente>="1"` envía facturas reales al sandbox del SRI — inválidas legalmente.
- Sin `EInvoicingCountrySettings`, el módulo es completamente inoperativo con un 422 opaco.

---

## 2. Accounting

### A) Qué está implementado

- Router completo (1022 líneas): CRUD plan de cuentas jerárquico, seed de 42 cuentas estándar, CRUD de asientos con líneas (libro diario), contabilización (`POST /journal-entries/{id}/post`), recálculo de saldos.
- Configuración contable POS: GET/PUT `/pos/settings`, CRUD `/pos/payment-methods`.
- `journal_service.py`: `create_posted_entry()` con validación de cuadre (débito=crédito), actualización incremental de saldos.
- Frontend: `ChartOfAccountsList`, `JournalEntriesList`, `JournalEntryForm`, `DashboardContable`, `LibroDiario`, `LibroMayor`, `PerdidasGanancias`, `PlanContable`, `PosAccountingSettings`.

### B) Qué falta o está roto

1. **[HECHO 2026-04-30] Libro Mayor con endpoint propio**: existe `GET /accounting/chart-of-accounts/{id}/ledger` con saldo inicial, movimientos `POSTED` en rango y saldo corrido. `LibroMayor.tsx` ya consume este endpoint en vez de agrupar todos los asientos client-side.

2. **[HECHO 2026-04-30] Balance y P&G con endpoints de backend**: `GET /accounting/reports/profit-loss` (rango de fechas, agrupa por cuenta INCOME/EXPENSE con asientos POSTED, valida rango ≤366 días) y `GET /accounting/reports/balance-sheet` (fecha de corte, agrupa ASSET/LIABILITY/EQUITY, verifica ecuación contable con warning en log). `PerdidasGanancias.tsx` reescrito para consumir el endpoint; nuevo componente `BalanceSituacion.tsx` creado. Schemas Pydantic `ReportAccountLine`, `ProfitLossReportResponse`, `BalanceSheetReportResponse` añadidos a `app/schemas/accounting.py`. Ruta `/balance` añadida en Routes.tsx y Panel.tsx.

3. **Asientos automáticos no integrados**: solo el módulo `expenses` llama a `create_posted_entry()` automáticamente. Ventas (`modules/sales`), compras (`modules/purchases`) y caja (`modules/pos`) no generan asientos — la contabilidad siempre queda incompleta sin disciplina manual. Verificado en auditoría 2026-04-30.

4. **[HECHO 2026-04-30] Variable `status` renombrada internamente**: el query param público sigue siendo `status`, pero el parámetro Python ahora es `entry_status` para evitar shadowing con `fastapi.status`.

5. **[HECHO 2026-04-30] Recálculo de saldos normalizado**: `_recalcular_saldos_cuenta` ya actualiza `debit_balance`/`credit_balance`/`balance`, igual que `journal_service.py`; se elimina el intento de escribir campos inexistentes `saldo_debe`/`saldo_haber`.

### C) Estimación de esfuerzo

**Mediano (semanas)**: La capa CRUD es sólida. Los reportes P&G y Balance ya tienen endpoints de backend y componentes frontend. Falta: integración automática de asientos con ventas/compras/caja, asientos de cierre/apertura/regularización, y permisos granulares.

### D) Riesgos si se activa hoy

- Contabilidad siempre incompleta si el usuario no crea asientos manualmente por cada transacción.
- Los reportes P&G y Balance muestran solo lo que esté contabilizado; sin asientos automáticos los saldos son parciales.

---

## 3. Reconciliation

### A) Qué está implementado

- Router con 9 endpoints: importar extracto, listar, detalle, líneas, auto-match, match manual, summary, reconcile-payment, pending.
- `AutoMatchUseCase`: match por referencia exacta y por monto ±3 días.
- `reconciliation_service.py`: SQL real para match, status y pending.
- `payments.py`: pasarelas Stripe, Kushki, Payphone — creación de links, webhooks, refunds.
- Frontend: `ReconciliationDashboard`, `StatementDetail`, `ImportForm`.

### B) Qué falta o está roto

1. **[HECHO 2026-04-30] RLS añadido a rutas autenticadas**: el router tenant de conciliación usa `with_access_claims`, `require_scope("tenant")` y `ensure_rls`; las rutas autenticadas de pagos también ejecutan `ensure_rls`. El webhook público queda protegido por firma de proveedor.

2. **[HECHO 2026-04-30] Webhooks de pago fallan cerrado sin firma/secret**: Stripe, Kushki y PayPhone rechazan webhooks sin secret configurado o sin header de firma. Queda pendiente validar con payloads reales de cada proveedor.

3. **[PARCHEADO 2026-04-30] JSON inválido en webhooks falla explícitamente**: `_safe_json_loads()` lanza `invalid_webhook_json` si el payload no es JSON objeto; ya no convierte errores en `{}`.

4. **Sin upload de extractos CSV/OFX**: `ImportForm.tsx` existe pero no hay endpoint de upload — `ImportStatementUseCase.execute()` recibe `transactions: list` (JSON ya parseado), no un `UploadFile`. El endpoint `POST /statements` acepta únicamente un body JSON con líneas ya estructuradas. Verificado en auditoría 2026-04-30.

### C) Estimación de esfuerzo

**Mediano (semanas)**: El matching funciona. Bloqueantes restantes: upload de extractos y validación formal de providers/refunds.

### D) Riesgos si se activa hoy

- Los webhooks de pago ya fallan cerrado sin firma/secret; queda pendiente validarlos contra payloads reales de Stripe, Kushki y PayPhone.
- El aislamiento RLS queda añadido en rutas autenticadas; falta validarlo en pruebas de integración con Postgres/RLS activo.

---

## 4. Reports

### A) Qué está implementado

- Endpoints: `POST /generate`, `GET /` (list), `POST /export`, `GET /sales`, `GET /inventory`, `GET /financial`, `POST /schedule`, `GET /scheduled`, `DELETE /scheduled/{id}`.
- 3 generadores reales: `SalesReportGenerator`, `InventoryReportGenerator`, `FinancialReportGenerator`.
- Exportadores: CSV, JSON, Excel (`openpyxl`), PDF (`reportlab`), HTML.
- `ScheduleReportUseCase`: persiste config en `scheduled_reports`.
- Frontend: `ReportsDashboard`, `SalesReport`, `FinancialReport`, `InventoryReport`, `MarginsDashboard`, `RealProfitReport`.

### B) Qué falta o está roto

1. **[PARCHEADO 2026-04-30] Scheduled reports bloqueados por defecto**: `POST /reports/schedule` devuelve HTTP 503 salvo que `REPORTS_SCHEDULER_ENABLED=true`. Sigue faltando Celery beat real que ejecute y envíe los reportes.

1b. **[PARCHEADO 2026-04-30] Rango máximo de reportes tenant**: `generate`, `export`, `sales`, `financial` y `schedule` rechazan rangos mayores a 366 días o invertidos.

2. **`SalesReportGenerator` usa tabla `sales_orders`**: si la tabla no existe (ventas van por POS o `sales`), lanza excepción que ya NO se silencia — el endpoint devuelve HTTP 500 con `"Error generating report"` (ya no retorna datos vacíos sin advertencia). El problema de fondo (tabla errónea) sigue sin resolver. Verificado en auditoría 2026-04-30.

3. **[PARCHEADO 2026-04-30] Persistencia de historial no se silencia**: si la tabla `reports` no existe o falla, la respuesta incluye `persisted: false` y `persistence_error: "reports_table_unavailable"` en vez de aparentar persistencia correcta.

4. **[HECHO 2026-04-30] RLS añadido al router tenant**: el router usa `with_access_claims`, `require_scope("tenant")` y `ensure_rls`.

5. **[PARCHEADO 2026-04-30] `RealProfitReport.tsx` ahora usa endpoint de snapshots con costo real**: el frontend llama a `GET /reports/profit` y `POST /reports/recalculate`. El `RecalculationService` calcula COGS usando `recipe.unit_cost` o `product.cost_price` por producto. Sigue pendiente que Celery beat recalcule snapshots automáticamente cada noche (hoy solo se recalcula bajo demanda con el botón).

### C) Estimación de esfuerzo

**Mediano (semanas)**: Generadores básicos funcionan. Falta: confirmar nombres de tablas, migraciones de `reports`/`scheduled_reports` y Celery beat para envíos.

### D) Riesgos si se activa hoy

- Reportes programados no deben activarse hasta implementar Celery beat real. El endpoint de creación queda cerrado por defecto para evitar falsas alertas.
- `SalesReportGenerator` devuelve HTTP 500 explícito si `sales_orders` no existe (ya no retorna datos vacíos sin advertencia), pero la causa sigue sin resolverse — la tabla de ventas correcta es `invoices` o `pos_receipts`.

---

## 5. Documents / Quotes

### A) Qué está implementado

- Endpoints: `POST /documents/sales/draft`, `POST /documents/sales/issue`, `GET /documents/{id}/render`, `GET /documents/{id}/print`.
- `DocumentOrchestrator`: pipeline draft/issue completo con `EcuadorPack`, cálculo de impuestos, numeración secuencial, clave_acceso-less.
- `TemplateEngine`: renderizado HTML de documentos.
- `document_storage.py`: almacenamiento de documentos emitidos.
- RLS correcto: usa `ensure_rls` + `ensure_guc_from_request`.

### B) Qué falta o está roto

1. **[PARCHEADO 2026-04-30] Solo soporta Ecuador y falla cerrado**: `DocumentOrchestrator` instancia `EcuadorPack()` y ahora rechaza `cfg.country != "EC"` con `documents_country_not_supported` para no generar documentos españoles con formato ecuatoriano.

2. **Sin flujo de Quotes/Proformas**: el módulo se llama "Documents/Quotes" pero solo tiene draft/issue de facturas. No existe proforma → aprobación → conversión a factura.

3. **[HECHO 2026-04-30] Endpoint de listado montado**: `document_storage.py` (prefix `/documents/storage`) ahora está montado en `platform/http/router.py` bajo `/tenant`. Los endpoints `GET /tenant/documents/storage`, `GET /tenant/documents/storage/{document_id}` y `POST /tenant/documents/storage/upload` son accesibles con scope tenant + RLS.

4. **Sin frontend dedicado**: las funciones de documento están integradas en `billing/` — el módulo `documents/` no tiene pantallas propias en el tenant.

### C) Estimación de esfuerzo

**Pequeño-Mediano (días a semanas)**: El núcleo draft/issue con RLS está bien implementado. Falta: soporte España, endpoint de listado, flujo de quotes.

### D) Riesgos si se activa hoy

- Tenants no Ecuador reciben error explícito en vez de documentos con formato fiscal incorrecto.

---

## 6. AI Agent

### A) Qué está implementado

- `analyzer.py`: `analyze_incident_with_ia()` — llama a `AIService.query()`, persiste en `incident.ia_analysis`.
- `suggest_fix()` — sugerencia de código via IA.
- `auto_resolve_incident()` — intento de auto-resolución.
- `notifier.py`: email (aiosmtplib), WhatsApp (Twilio), Telegram (Bot API), Slack (webhook y bot token) — funcionales con credenciales configuradas, fallback mock sin ellas.
- Invocado internamente desde `support/interface/http/incidents.py` — sin router propio de tenant.

### B) Qué falta o está roto

1. **[PARCHEADO 2026-04-30] `auto_resolve_incident()` ya no resuelve en mock**: devuelve `success: false` indicando que falta sandbox seguro, sin marcar la incidencia como resuelta.

2. **[PARCHEADO 2026-04-30] Fallback de análisis mock eliminado**: si el proveedor IA falla, el análisis devuelve error explícito y no persiste un diagnóstico genérico.

3. **[PARCHEADO 2026-04-30] Notificaciones sin credenciales fallan explícitamente**: email, WhatsApp, Telegram y Slack ya no devuelven `"sent (mock)"` si faltan credenciales o dependencias.

4. **[PARCHEADO 2026-04-30] Sin destinatarios hardcodeados**: WhatsApp y Telegram requieren destinatario configurado; ya no usan `+1234567890` ni `mock_chat_id`.

5. **Sin router de tenant**: solo accesible por admins vía `/api/v1/admin/incidents`.

### C) Estimación de esfuerzo

**Mediano (semanas)**: Integraciones reales funcionales con credenciales. El auto-resolve requiere diseño de sandbox aislada — trabajo significativo.

### D) Riesgos si se activa hoy

- Auto-resolve queda desactivado hasta tener sandbox real.
- Notificaciones sin credenciales fallan explícitamente; queda pendiente configurar canales reales por tenant.

---

## 7. Restaurant

### A) Qué está implementado

- Router completo: CRUD mesas, comandas, items, send-kitchen, close.
- Modelos ORM: `RestaurantTable`, `RestaurantOrder`, `RestaurantOrderItem`.
- Lógica de negocio: estado de mesa (available → occupied → cleaning), numeración CMD-NNNNNN, cálculo de totales.
- RLS parcial: `ensure_guc_from_request` y `ensure_rls` presentes en el router.
- Frontend: `TablesView.tsx` (grid con colores por estado, auto-refresh 30s), `OrderView.tsx` (comanda con búsqueda de productos).

### B) Qué falta o está roto

1. **[HECHO 2026-04-30] Router montado en `platform/http/router.py`**: `app.modules.restaurant.interface.http.tenant` ahora está registrado con prefix `/tenant`. Los endpoints `/api/v1/tenant/restaurant/tables`, `/api/v1/tenant/restaurant/orders`, etc. son accesibles. El módulo sigue con `enabled: false` en el manifest frontend hasta completar integración fiscal/caja.

1b. **[PARCHEADO 2026-04-30] Manifest frontend deshabilitado por defecto**: `apps/tenant/src/modules/restaurant/manifest.ts` incluye `enabled: false` para evitar exposición accidental mientras el backend y el flujo fiscal/caja siguen incompletos.

2. **`_recalculate_order_totals()` línea 702**: `tax_total = 0.0` hardcodeado — impuestos siempre cero. Verificado en auditoría 2026-04-30: sin cambios.

3. **[PARCHEADO 2026-04-30] Cierre de comanda bloqueado**: `POST /orders/{id}/close` devuelve HTTP 501 `restaurant_close_requires_pos_billing_integration` para no marcar comandas como pagadas sin POS/facturación.

4. **Sin flujo de pago**: cerrar comanda no toma método de pago ni monto — el estado va directo a `"paid"` sin pasar por caja.

5. **`OrderView.tsx` línea 39**: búsqueda de productos sin filtro de menú — el personal ve todos los productos del sistema (materias primas, etc.).

6. **Sin Kitchen Display System (KDS)**: no hay pantalla ni endpoint para que cocina vea las comandas en preparación.

### C) Estimación de esfuerzo

**Grande (meses)**: El CRUD existe pero el módulo es inaccesible, no tiene integración fiscal/caja, y le faltan flujos core (pago, KDS, impuestos). Registrar el router es trivial; integrar con POS y facturación es el esfuerzo real.

### D) Riesgos si se activa hoy

- El módulo no responde (404) al no estar registrado.
- Si se registra manualmente, cerrar comandas no genera comprobante fiscal — incumplimiento legal.

---

## 8. Historical

### A) Qué está implementado

- Router completo: `GET/DELETE /imports`, `GET /imports/{id}`, `POST /upload`, `GET /sales`, `GET /purchases`, `GET /stock`, `GET /daily-sales`, `GET /dashboard`.
- `UploadHistoricalFileUseCase`: parseo CSV/XLSX con pandas, detección automática de columnas por alias, importación a `hist_sales`, `hist_purchases`, `hist_stock`, `hist_daily_sales`.
- Dashboard con métricas agregadas.
- Migración SQL: `2026-04-06_000_historical_module/up.sql` confirmada.
- Frontend completo: `DashboardPage`, `SalesPage`, `PurchasesPage`, `StockPage`, `ImportsPage`, `UploadPage`.

### B) Qué falta o está roto

1. **[HECHO 2026-04-30] RLS añadido al router**: `interface/http/tenant.py` ahora usa `with_access_claims`, `require_scope("tenant")` y `ensure_rls`.

2. **[HECHO 2026-04-30] Upload no bloqueante con `asyncio.to_thread`**: el endpoint `POST /upload` ahora delega `UploadHistoricalFileUseCase.execute()` a un thread de I/O via `asyncio.to_thread`, liberando el event loop de FastAPI durante el procesamiento pandas. Se abre una sesión SQLAlchemy dedicada en el thread con el contexto RLS copiado de la sesión de request.

3. **[PARCHEADO 2026-04-30] Upsert de maestros ya no silencia errores**: los fallos de maestros en ventas/compras se registran con `logger.warning(..., exc_info=True)`; el import principal sigue su curso, pero el error queda trazable.

4. **[HECHO 2026-04-30] Límite de tamaño de archivo añadido**: `POST /upload` rechaza archivos de más de 10 MB con HTTP 413. Sigue pendiente mover el procesamiento a background/Celery.

5. **[HECHO 2026-04-30] Sin default a `date.today()`**: si una fila no tiene fecha válida, falla esa fila con `missing_fecha` en vez de importarse con la fecha actual.

6. **[HECHO 2026-04-30] Deduplicación fuerte por hash SHA-256**: se calcula `hashlib.sha256(file_bytes).hexdigest()` antes de procesar; se consulta `hist_imports` por `(tenant_id, file_hash, status IN ('processing','completed'))`. Si hay coincidencia se rechaza con HTTP 409 `duplicate_file_hash`. El hash se persiste en la columna `file_hash VARCHAR(64)` (migración `2026-04-30_001_historical_file_hash`). Se mantiene también el fallback por nombre/tamaño para imports anteriores sin hash.

7. **Sin feedback de progreso en frontend**: para archivos grandes el usuario no sabe si el upload sigue procesando — puede re-subir creyendo que falló, duplicando datos.

### C) Estimación de esfuerzo

**Pequeño-Mediano**: El núcleo de importación funciona. Los dos bloqueantes principales (upload asíncrono y deduplicación fuerte por hash) quedan resueltos. Bloqueante restante: feedback de progreso en el frontend para archivos grandes.

### D) Riesgos si se activa hoy

- Sin feedback de progreso en frontend: el usuario puede re-subir creyendo que el proceso falló (el hash evita duplicados pero la UX sigue siendo pobre para archivos grandes).
- El procesamiento pandas corre en el thread pool del proceso uvicorn; picos de uploads masivos paralelos podrían saturar workers — suficiente para el volumen esperado, Celery queda como mejora futura.

---

## 9. Analytics

### A) Qué está implementado

- Router `dashboard/kpis` con queries SQL reales por sector: `panaderia` (ventas, stock crítico, merma, producción, ingredientes próximos a caducar), `taller` (facturación, repuestos bajos, trabajos), `retail/todoa100` (ventas, rotación de stock, reposición), `default` (ventas POS + facturas). Montado en `platform/http/router.py` vía shim `app.routers.dashboard_stats`.
- Router `/api/v1/admin/stats` con estadísticas de tenants, usuarios y módulos.
- Scope y `ensure_rls` correctos en `dashboard/kpis`.
- Migración `2026-02-14_002_profit_snapshots` para `product_profit_snapshots` y `profit_snapshots_daily`.

### B) Qué falta o está roto

1. **Sin definición funcional cerrada como módulo**: `dashboard/kpis` es un endpoint de KPIs por sector accesible, pero no existe un módulo `analytics/` dedicado en el frontend (`apps/tenant/src/modules/analytics/` no existe). Ningún componente React llama a `/api/v1/tenant/dashboard/kpis`. Los KPIs están implementados en backend pero no consumidos desde una UI de analytics. Verificado en auditoría 2026-04-30.

2. **[PARCHEADO 2026-04-30] Rutas de analytics protegidas**: `dashboard/kpis` exige scope tenant y `ensure_rls`; `/api/v1/admin/stats` exige scope admin. Sigue pendiente: frontend dedicado, validación funcional con datos reales, pruebas de integración.

3. **Riesgo de registro prematuro**: si se registra como módulo disponible, el usuario puede ver una funcionalidad vacía o incompleta — la API existe pero no hay UI que la consuma.

### C) Estimación de esfuerzo

**Pequeño-Mediano** si solo se desactiva/oculta. **Mediano o mayor** si se quiere convertir en módulo productivo con métricas, permisos, endpoints y pruebas.

### D) Riesgos si se activa hoy

- Módulo visible sin valor real para el usuario.
- Falsa señal comercial de que existe analítica avanzada cuando todavía no está especificada ni validada.

---

## Plan de acción por prioridad

### Prioridad ALTA (bloqueos de seguridad)

| # | Módulo | Acción | Fichero |
|---|--------|--------|---------|
| 1 | Reconciliation | [HECHO 2026-04-30] Añadir verificación HMAC/fail-closed en webhooks Stripe/Kushki/PayPhone | `services/payments/*_provider.py` |
| 2 | Historical | [HECHO 2026-04-30] Añadir `ensure_rls` al router | `modules/historical/interface/http/tenant.py` |
| 3 | Reports | [HECHO 2026-04-30] Añadir `ensure_rls` al router | `modules/reports/interface/http/tenant.py` |
| 4 | Einvoicing | Conectar tasks Celery al worker real ([PARCHEADO 2026-04-30] stubs fallan cerrado) | `modules/einvoicing/tasks.py` |
| 5 | Einvoicing | [PARCHEADO 2026-04-30] Eliminar `einvoice_service.sign_xml()` fake | `infrastructure/einvoice_service.py` |

### Prioridad MEDIA (funcionalidad core)

| # | Módulo | Acción |
|---|--------|--------|
| 6 | Restaurant | [HECHO 2026-04-30] Registrar router en `platform/http/router.py` |
| 7 | Restaurant | Integrar `close` con módulo de caja/facturación |
| 8 | Accounting | [HECHO 2026-04-30] Endpoints P&G y Balance de situación creados (`/reports/profit-loss`, `/reports/balance-sheet`); frontend actualizado |
| 9 | Accounting | Integrar asientos automáticos con ventas/compras/caja |
| 10 | Historical | [HECHO 2026-04-30] Upload asíncrono con `asyncio.to_thread` (libera event loop; Celery queda como mejora futura) |
| 11 | Historical | [HECHO 2026-04-30] Deduplicación fuerte por hash SHA-256 con columna `file_hash` y migración `2026-04-30_001_historical_file_hash` |
| 12 | Reports | Implementar Celery beat para scheduled reports y recalculation nocturna de snapshots ([PARCHEADO 2026-04-30] creación cerrada por defecto; recalculation manual disponible) |
| 13 | Documents | Añadir soporte España (EspañaPack) |
| 13b | Documents | [HECHO 2026-04-30] Montar `document_storage` router en `platform/http/router.py` — endpoints `GET/POST /tenant/documents/storage` ya accesibles |

### Prioridad BAJA (mejoras y bloqueantes externos)

| # | Módulo | Acción |
|---|--------|--------|
| 14 | Einvoicing | UI para subir certificado .p12 por tenant |
| 15 | Einvoicing | Hacer `<ambiente>` configurable por tenant (pruebas/producción) |
| 16 | Documents | Implementar flujo Quotes/Proformas |
| 17 | AI Agent | Diseñar sandbox aislada para auto-resolve (Docker/VM) ([PARCHEADO 2026-04-30] mock desactivado) |
| 18 | AI Agent | Configurar credenciales reales (SMTP, Twilio, Telegram) ([PARCHEADO 2026-04-30] mocks de envío desactivados) |
| 19 | Restaurant | Implementar Kitchen Display System (KDS) |
| 20 | Accounting | [HECHO 2026-04-30] Corrección bug variable `status` shadowing |
| 21 | Analytics | Definir alcance o mantener oculto por feature flag |

### Bloqueantes externos (no dependen solo de código)

- **Einvoicing Ecuador**: cada tenant necesita certificado digital del BCE — proceso externo al desarrollo.
- **Einvoicing España**: certificado FNMT + homologación AEAT — proceso externo.
- **Celery workers**: confirmar que están activos en el entorno de deploy (`render.yaml`, `requirements-celery.txt`).
