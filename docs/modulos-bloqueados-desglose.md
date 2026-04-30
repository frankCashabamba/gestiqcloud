# Módulos Bloqueados — Desglose Técnico

Fecha: 2026-04-30
Fuente: auditoría de código sobre commit actual (main)

Este documento detalla qué falta exactamente en cada módulo bloqueado para llegar a producción,
con estimación de esfuerzo y riesgos reales si se activara hoy.

---

## Resumen ejecutivo

| Módulo         | Estado                                              | Esfuerzo               | Riesgo principal                                          |
|----------------|-----------------------------------------------------|------------------------|-----------------------------------------------------------|
| Einvoicing     | Parcial (firma XAdES real, tasks SRI/SII son stubs) | Grande + externo       | Facturas marcadas AUTHORIZED sin enviarse al SRI          |
| Accounting     | CRUD funcional, faltan reportes y asientos automáticos | Mediano             | Contabilidad incompleta; bug de variable `status`         |
| Reconciliation | Funcional pero sin verificación de firma webhook    | Mediano                | Cualquiera puede marcar facturas como pagadas vía webhook  |
| Reports        | 3 generadores funcionales, scheduled sin Celery     | Mediano                | Reportes programados nunca se ejecutan                    |
| Documents/Quotes | Funcional solo para Ecuador, sin quotes           | Pequeño-Mediano        | Documentos España con formato Ecuador incorrecto          |
| AI Agent       | Funcional con credenciales, auto-resolve es mock    | Mediano                | Incidentes marcados como resueltos sin serlo              |
| Restaurant     | Router no montado — inaccesible desde API           | Grande                 | 404 en todo el módulo; sin integración fiscal             |
| Historical     | Funcional, RLS añadido, upload aún bloqueante       | Mediano                | Upload grande puede bloquear servidor                     |
| Analytics      | Módulo vacío / no validado como producto            | Pequeño-Mediano        | Registrar un módulo sin funcionalidad real                |

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

1. **`einvoicing/tasks.py` líneas 109 y 146**: los tasks Celery registrados como `einvoicing.tasks.sign_and_send` y `einvoicing.tasks.build_and_send_sii` son **stubs explícitos** que hacen `UPDATE sri_submissions SET status='AUTHORIZED'` sin llamar al worker real. El worker real en `app/workers/einvoicing_tasks.py` no coincide en nombre de tarea con lo registrado en `einvoicing/tasks.py`.

2. **[PARCHEADO 2026-04-30] `infrastructure/einvoice_service.py` ya no firma fake**: `sign_xml()` ahora lanza `NotImplementedError` en vez de marcar como firmado un SHA256 que no es firma XML válida. Sigue pendiente conectar siempre con el worker XAdES real.

3. **`einvoice_service.py` línea 358**: `export_to_pdf()` asigna `pdf_buffer = None` — crash `NoneType` garantizado si se invoca.

4. **XML SII incorrecto**: `SIIService.generate_xml()` genera `<factura version="3.2.1">` sin la estructura real de FacturaE 3.2.1 (`<FileHeader>`, `<Parties>`, etc.). `facturae_xml.py` sí implementa el formato real pero solo lo usa el endpoint de export, no el de envío SII.

5. **Campo `<ambiente>` hardcodeado**: `einvoicing_tasks.py` línea 101 fija `ambiente = "1"` (pruebas) en el XML SRI. El campo `env` llega del request pero no se aplica al XML generado — facturas reales siempre se envían al entorno de pruebas del SRI.

6. **Sin UI para certificado digital**: no hay pantalla para subir el `.p12` del tenant. La firma XAdES-BES necesita `cert_data["p12_base64"]` desde `EInvoicingCountrySettings`, que no tiene formulario de creación.

7. **`EInvoicingCountrySettings` no tiene endpoint de creación**: si el tenant no tiene settings, `POST /sri/send` devuelve HTTP 422 "SRI settings not configured" sin guía de resolución.

### C) Estimación de esfuerzo

**Grande (semanas) + Bloqueante-externo**: La firma XAdES-BES existe pero requiere pruebas reales con el SRI sandbox. Cada tenant necesita certificado digital emitido por el BCE (Ecuador) o FNMT (España) — proceso externo de días a semanas.

### D) Riesgos si se activa hoy

- Los tasks stub marcarían todas las facturas como `AUTHORIZED` sin enviarlas al SRI — fraude fiscal involuntario.
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

1. **Libro Mayor sin endpoint propio**: `LibroMayor.tsx` existe pero no hay `GET /accounting/chart-of-accounts/{id}/ledger`. El frontend filtra client-side — no escala.

2. **Balance y P&G sin endpoint de backend**: `PerdidasGanancias.tsx` calcula en frontend con datos del libro diario (`utils/reportesContables.ts`). Exactitud no garantizada para cierres contables reales.

3. **Asientos automáticos no integrados**: ventas, compras y caja no llaman a `create_posted_entry()` automáticamente — el usuario crea asientos manualmente. Contabilidad siempre desactualizda si no hay disciplina manual.

4. **[HECHO 2026-04-30] Variable `status` renombrada internamente**: el query param público sigue siendo `status`, pero el parámetro Python ahora es `entry_status` para evitar shadowing con `fastapi.status`.

5. **Inconsistencia de nombres de campos**: `_recalcular_saldos_cuenta` usa `saldo_debe`/`saldo_haber` (español); `journal_service.py` usa `debit_balance`/`credit_balance` (inglés). Pueden ser campos distintos o aliases — introduce riesgo de saldos duplicados o no actualizados.

### C) Estimación de esfuerzo

**Mediano (semanas)**: La capa CRUD es sólida. Falta: endpoints de reportes financieros (P&G, balance), integración automática con ventas/compras, y corrección del bug de `status`.

### D) Riesgos si se activa hoy

- Contabilidad siempre incompleta si el usuario no crea asientos manualmente por cada transacción.
- El listado de asientos ya no usa `status` como variable interna; quedan pendientes los riesgos contables funcionales.

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

3. **`payments.py` línea 145**: `_safe_json_loads()` devuelve `{}` silenciosamente en errores — el webhook puede procesar payloads vacíos y marcar facturas como pagadas con datos incorrectos.

4. **Sin upload de extractos CSV/OFX**: `ImportForm.tsx` existe pero no hay endpoint de upload — `ImportStatementUseCase` espera JSON ya parseado, no un archivo.

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

2. **`SalesReportGenerator` usa tabla `sales_orders`**: si la tabla no existe (ventas van por POS o `sales`), lanza excepción capturada silenciosamente — el usuario recibe HTTP 500 sin explicación.

3. **Tabla `reports` puede no existir**: `use_cases.py` tiene `try/except` con log `"table may not exist yet"` — confirma que la tabla puede faltar en producción sin migración explícita.

4. **[HECHO 2026-04-30] RLS añadido al router tenant**: el router usa `with_access_claims`, `require_scope("tenant")` y `ensure_rls`.

5. **`RealProfitReport.tsx` sin endpoint de margen real**: el backend calcula `SUM(invoices.total) - SUM(purchases.total)`, no costo real por producto. El margen mostrado es aproximado.

### C) Estimación de esfuerzo

**Mediano (semanas)**: Generadores básicos funcionan. Falta: confirmar nombres de tablas, migraciones de `reports`/`scheduled_reports` y Celery beat para envíos.

### D) Riesgos si se activa hoy

- Reportes programados no deben activarse hasta implementar Celery beat real. El endpoint de creación queda cerrado por defecto para evitar falsas alertas.
- `SalesReportGenerator` puede devolver reportes vacíos sin advertencia si `sales_orders` no existe.

---

## 5. Documents / Quotes

### A) Qué está implementado

- Endpoints: `POST /documents/sales/draft`, `POST /documents/sales/issue`, `GET /documents/{id}/render`, `GET /documents/{id}/print`.
- `DocumentOrchestrator`: pipeline draft/issue completo con `EcuadorPack`, cálculo de impuestos, numeración secuencial, clave_acceso-less.
- `TemplateEngine`: renderizado HTML de documentos.
- `document_storage.py`: almacenamiento de documentos emitidos.
- RLS correcto: usa `ensure_rls` + `ensure_guc_from_request`.

### B) Qué falta o está roto

1. **Solo soporta Ecuador**: `DocumentOrchestrator.__init__()` instancia siempre `EcuadorPack()`. Para tenants españoles genera documentos con formato incorrecto (campo `ruc` en vez de `NIF`, etc.).

2. **Sin flujo de Quotes/Proformas**: el módulo se llama "Documents/Quotes" pero solo tiene draft/issue de facturas. No existe proforma → aprobación → conversión a factura.

3. **Sin endpoint de listado**: no hay `GET /documents/` ni `GET /documents/{id}` — sin historial de documentos desde la API.

4. **Sin frontend dedicado**: las funciones de documento están integradas en `billing/` — el módulo `documents/` no tiene pantallas propias en el tenant.

### C) Estimación de esfuerzo

**Pequeño-Mediano (días a semanas)**: El núcleo draft/issue con RLS está bien implementado. Falta: soporte España, endpoint de listado, flujo de quotes.

### D) Riesgos si se activa hoy

- Tenants españoles recibirían documentos con formato ecuatoriano — incumplimiento de normativa fiscal española.

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

2. **`_mock_analysis_response()` línea 177**: análisis genérico de fallback con `"impact": "Impacto en funcionalidad del sistema (análisis mock)"` — inútil como información para operadores.

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

1. **Router no montado en `platform/http/router.py`**: el módulo no está registrado — **todos los endpoints devuelven 404**. El frontend apunta a `/api/v1/tenant/restaurant/*` que no existe en el servidor.

2. **`_recalculate_order_totals()` líneas 698-699**: `tax_total = 0.0` hardcodeado — impuestos siempre cero.

3. **Sin integración con POS/facturación**: `POST /orders/{id}/close` marca la comanda como `"paid"` pero no genera recibo, factura, ni registra la venta en ventas/caja.

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

2. **Upload bloqueante en hilo principal**: `UploadHistoricalFileUseCase.execute()` es síncrono con pandas. El endpoint `POST /upload` es `async def` pero no usa `run_in_executor` — bloquea el event loop de FastAPI para todos los usuarios durante el upload.

3. **`except Exception: pass` en línea 676**: errores de upsert en maestros silenciados — si hay constraint violation, se pierde en silencio.

4. **[HECHO 2026-04-30] Límite de tamaño de archivo añadido**: `POST /upload` rechaza archivos de más de 10 MB con HTTP 413. Sigue pendiente mover el procesamiento a background/Celery.

5. **[HECHO 2026-04-30] Sin default a `date.today()`**: si una fila no tiene fecha válida, falla esa fila con `missing_fecha` en vez de importarse con la fecha actual.

6. **[PARCHEADO 2026-04-30] Deduplicación básica sin migración**: el importador bloquea re-subidas con mismo tenant, tipo, nombre y tamaño cuando ya existe una importación `processing` o `completed`. Sigue pendiente deduplicación fuerte por hash/constraint.

7. **Sin feedback de progreso en frontend**: para archivos grandes el usuario no sabe si el upload sigue procesando — puede re-subir creyendo que falló, duplicando datos.

### C) Estimación de esfuerzo

**Mediano (semanas)**: El núcleo de importación funciona. Bloqueantes restantes: upload asíncrono con Celery y deduplicación fuerte por hash/constraint.

### D) Riesgos si se activa hoy

- Upload de archivos grandes bloquea el servidor FastAPI causando timeouts generales.
- Doble upload idéntico queda bloqueado por nombre/tamaño/tipo; sigue pendiente deduplicación fuerte por hash.

---

## 9. Analytics

### A) Qué está implementado

- El plan de producción lo identifica como módulo existente en la matriz de módulos bloqueados.
- No hay evidencia en esta auditoría de un flujo funcional listo para tenant, dashboard productivo, endpoints validados ni pruebas de negocio.

### B) Qué falta o está roto

1. **Sin definición funcional cerrada**: no consta qué métricas, dashboards o segmentos son parte del producto v1.

2. **Sin validación técnica en este desglose**: no se ha confirmado router, aislamiento por tenant, permisos, migraciones ni frontend productivo.

3. **Riesgo de registro prematuro**: si se registra como módulo disponible, el usuario puede ver una funcionalidad vacía o incompleta.

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
| 4 | Einvoicing | Conectar tasks Celery al worker real (eliminar stubs) | `modules/einvoicing/tasks.py` |
| 5 | Einvoicing | [PARCHEADO 2026-04-30] Eliminar `einvoice_service.sign_xml()` fake | `infrastructure/einvoice_service.py` |

### Prioridad MEDIA (funcionalidad core)

| # | Módulo | Acción |
|---|--------|--------|
| 6 | Restaurant | Registrar router en `platform/http/router.py` |
| 7 | Restaurant | Integrar `close` con módulo de caja/facturación |
| 8 | Accounting | Crear endpoints P&G y Balance de situación |
| 9 | Accounting | Integrar asientos automáticos con ventas/compras/caja |
| 10 | Historical | Hacer upload asíncrono con Celery ([HECHO 2026-04-30] límite de tamaño) |
| 11 | Historical | Añadir deduplicación por hash de archivo ([PARCHEADO 2026-04-30] dedupe básica nombre/tamaño/tipo) |
| 12 | Reports | Implementar Celery beat para scheduled reports ([PARCHEADO 2026-04-30] creación cerrada por defecto) |
| 13 | Documents | Añadir soporte España (EspañaPack) |

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
