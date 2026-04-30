# Plan de Produccion: Parches vs Bloqueos

Fecha: 2026-04-29

Objetivo: dejar listos para produccion los modulos que estan cerca del 100%, aplicando parches acotados. Los modulos con trabajo estructural, legal, fiscal o de arquitectura quedan fuera del pase a produccion hasta completar una fase aparte.

## Criterio de decision

Un modulo puede subir a produccion si:

- Tiene aislamiento por tenant en las rutas principales.
- No expone secretos, datos bancarios completos ni datos cross-tenant.
- Sus flujos principales persisten datos reales y tienen pruebas basicas.
- Los bugs pendientes se resuelven con parches pequenos o medianos.
- No depende de integraciones fiscales, legales o workers no implementados.

Un modulo queda fuera de produccion si:

- Tiene stubs en funcionalidad core.
- Requiere firma fiscal/electronica real.
- Tiene auth/RLS paralela o incompleta.
- Necesita redisenar modelos, workers, schedulers o permisos.
- Puede producir datos contables/fiscales incorrectos.

## Ya mitigado en sesion 2026-04-29 (segunda tanda)

- Sales backend: paginacion real en `list_orders` (default 50, max 200, param `skip`); checkout ya no genera UUID aleatorio si falta `user_id` (devuelve 401/400); `ApproveSalesOrderUseCase`, `GetSalesOrderUseCase` y `CancelSalesOrderUseCase` marcados como STUB con comentario explicito.
- Purchases backend: `delete_purchase` bloquea con 409 si hay `StockMove` asociados; `list_purchases` acepta `supplier_id`, `status`, `date_from`, `date_to`, `search`, `skip`, `limit` (max 200).
- Expenses backend: `list_expenses` es ahora read-only (eliminado `db.commit()` del GET); acepta `skip`, `limit`, `date_from`, `date_to`, `category`, `status`, `supplier_id`.
- Clients backend: busqueda por nombre/email/identificacion via `search` (ILIKE OR); limite maximo corregido de 1000 a 200; documentado que historial y credito son FASE 2.
- CRM backend: `_resolve_tenant_currency()` ya no lanza 500 si el tenant no tiene moneda — retorna "USD" como fallback.
- Suppliers modelo: `UniqueConstraint("tenant_id", "tax_id")` anadido al modelo SQLAlchemy; mensaje 409 en espanol.
- Billing backend: webhook ya no usa codigo interno en error de secret — mensaje legible; handler `invoice.payment_failed` anadido (pone `status = 'past_due'`); endpoints admin `subscribe`, `change-plan` y `cancel` emiten log AUDIT con tenant_id, user_id y timestamp.

## Ya mitigado en las ultimas tandas

- Identity: eliminado log del secreto JWT, `ensure_rls` ya no falla silenciosamente, cambio de password revoca sesiones.
- Settings frontend: MFA ya no debe enviar el secreto TOTP a un servicio externo.
- POS backend: turnos y resumen filtrados por tenant; ticket fallback escapa HTML.
- Sales backend: confirmacion y delivery corregidos; promo code incrementa `usage_count`; Telegram escapa HTML.
- Purchases backend: alta con lineas, numero requerido, validacion de productos/warehouse por tenant.
- Suppliers backend: listado ya no expone IBAN completo.
- Clients backend: tenant UUID validado, `identificacion_tipo` conservado, delete bloqueado con documentos relacionados.
- Finance backend: rates y balances filtrados por tenant.
- Invoicing backend: busqueda por texto y JSONB webhook corregidos.
- Reconciliation backend: varios SQL viejos y UUID runtime corregidos.
- Reports backend: referencias rotas a `purchase_orders` corregidas donde aplicaba.
- Reports backend: [HECHO 2026-04-30] router tenant protegido con `ensure_rls`.
- Reports backend: [PARCHEADO 2026-04-30] `POST /reports/schedule` devuelve 503 por defecto salvo `REPORTS_SCHEDULER_ENABLED=true`.
- Importador OCR: cache incluye tenant.
- Webhooks: validacion anti-SSRF basica.
- Inventory: ajustes negativos bloqueados; cycle count y sync requieren permisos especificos.
- Products: purge destructivo por DELETE bloqueado; purge real exige POST con permiso y confirmacion; merge de duplicados exige permiso y solo actualiza tablas con `tenant_id`; deteccion de similares queda limitada por `scan_limit`.
- Suppliers: `PUT` acepta payload parcial, IBAN se normaliza y valida con checksum, y `tax_id` duplicado por tenant devuelve 409.
- Billing frontend: `customer_name`, `description` y `notes` ya se envian al backend al crear/editar factura.
- Branches: `assign-warehouse` y `assign-register` validan que sucursal y recurso pertenezcan al tenant antes de enlazar.
- Users: email/username se validan por tenant y `check-username` deja de ser publico anonimo.
- Export: CSV/XLSX tienen `limit` con maximo y los joins de stock filtran `warehouses`/`products` por tenant.
- HR frontend: rechazo de vacaciones ya usa modal React en vez de `window.prompt`; `updateNomina` y delete de nomina fueron verificados contra el estado actual del codigo.
- POS frontend: eliminado `tpv_pro.html` legacy y el draft local ya no persiste identificacion, nombre ni email del comprador.
- Frontend legacy/dialogs: eliminados listados muertos de Products/Users con `confirm()`; Historical y Restaurant usan modales React en vez de `confirm`/`alert`/`prompt`.
- Historical backend: [HECHO 2026-04-30] router tenant protegido con `ensure_rls` y upload limitado a 10 MB.
- Accounting backend: [HECHO 2026-04-30] query param `status` mantiene compatibilidad externa pero internamente se renombra a `entry_status` para evitar shadowing.
- Reconciliation payments: [HECHO 2026-04-30] Stripe, Kushki y PayPhone rechazan webhooks sin secret configurado o sin firma.

## Modulos candidatos a produccion con parches

### POS

Estado: candidato fuerte.

Parches pendientes:

- [DECISION v1] Devolucion parcial queda fuera de alcance del primer release. FASE 2.
- [HECHO 2026-04-29] Alinear permisos frontend con backend para acciones sensibles. (ShiftManager, RefundModal y POSPaymentBar usan ProtectedButton con permiso granular)
- [HECHO 2026-04-29] Revisar datos personales en `localStorage` del frontend POS. (selectedCustomerName eliminado del draft persistido)
- [HECHO sesion anterior] Eliminar o aislar tpv_pro.html legacy del build/productivo.

Condicion para subir: pruebas de venta, checkout, descuento de stock, cierre de turno e impresion.

### Inventory

Estado: candidato fuerte.

Parches pendientes:

- [DECISION v1] Valorizacion de inventario queda fuera de v1. Solo visible en reports internos cuando este implementado. FASE 2.
- [DECISION v1] Alertas de stock minimo solo por ejecucion manual en v1. Scheduler Celery queda para FASE 2.
- [HECHO 2026-04-30] Revisar UI para permisos nuevos: `inventory.stock.adjust`, `inventory.cycle_count.manage`, `inventory.stock.sync`. (StockListFixed.tsx: botones Sync y Quick Adjust protegidos con ProtectedButton; cycle count sin UI todavia)
- [HECHO 2026-04-29] Confirmar que `get_stock` no muestra warehouses cross-tenant en consultas con joins. (joins reforzados con filtro tenant_id en Product y Warehouse)

Condicion para subir: pruebas de ajuste, transferencia, cycle count, stock move y stock item.

### Sales

Estado: candidato con advertencias.

Parches pendientes:

- [HECHO 2026-04-29] Definir si el estado `paid` se maneja desde checkout/factura o crear endpoint formal de pago. (endpoint POST /{order_id}/mark-paid con permiso sales.order.pay)
- [HECHO 2026-04-29] Agregar paginacion real a listados de ordenes.
- [HECHO 2026-04-29] Evitar fallback de auditoria con UUID aleatorio en checkout si falta `user_id`.
- [HECHO 2026-04-29] Marcar use cases stub como deprecated o conectarlos al flujo real para evitar usos futuros incorrectos.

Condicion para subir: crear, confirmar, cancelar, checkout, factura y promociones probados.

### Purchases

Estado: candidato con parches.

Parches pendientes:

- [HECHO 2026-04-29] Evitar hard delete si la compra ya tuvo recepciones o stock moves.
- [HECHO 2026-04-29] Agregar filtros/busqueda basicos.
- [HECHO 2026-04-29] Definir flujo de aprobacion antes de recibir o dejarlo fuera de alcance. (DECISION v1: fuera de alcance, documentado en comentario del router)
- [HECHO 2026-04-30] Validar selector de proveedor en frontend para que `supplier_id` sea real. (Form.tsx reemplaza input libre por select cargado desde API; validacion en submit)

Condicion para subir: crear compra con lineas, recibir mercancia, validar stock y costos.

### Products

Estado: candidato parcial.

Parches pendientes:

- [HECHO 2026-04-29] Unificar mecanismo de tenant/auth en endpoints que aun usen helpers antiguos. (12 endpoints migrados a get_current_tenant_id; _empresa_id_from_request conservado solo en public.py)
- [HECHO 2026-04-30] Agregar pruebas especificas para `duplicates/similar`, `duplicates/merge` y `POST /purge`. (12 tests en tests/test_products_advanced.py)
- [HECHO 2026-04-29] Definir si el permiso de purge debe ser solo owner/admin o si `products.delete` es suficiente para v1. (cambiado a permiso products.purge separado)

Condicion para subir: CRUD, stock visible, categorias, bulk operations y merge seguro por tenant.

### Clients

Estado: candidato.

Parches pendientes:

- [HECHO 2026-04-29] Agregar busqueda por nombre/email/identificacion.
- [TODO FASE 2] Tipar dominio con UUID para evitar deuda futura. (impacto >5 modulos cruzados; documentado en entities.py con TODO)
- [HECHO 2026-04-29] Definir si historial de compras y saldo/credito entran en v1 o fase posterior. (Decision: FASE 2, documentado en el router)

Condicion para subir: CRUD, paginacion, tenant isolation, update y delete con referencias.

### Suppliers

Estado: candidato con advertencias.

Parches pendientes:

- [HECHO 2026-04-29] Validar coincidencia `iban_confirmacion` tambien en frontend. (Form.tsx muestra error inline y bloquea submit si IBANs no coinciden)
- [HECHO 2026-04-29] Enmascarar IBAN tambien en vistas donde no sea estrictamente necesario. (Detail.tsx muestra ****XXXX)
- [HECHO 2026-04-29] Definir constraint DB de `tax_id` unico por tenant. (UniqueConstraint anadido al modelo; 409 en espanol)
- [DECISION v1] Cifrado IBAN en reposo queda para FASE 2. En v1 no almacenar IBANs reales hasta implementar cifrado. Documentado en onboarding.

Condicion para subir: no exponer IBAN completo en listados y validar datos bancarios.

### Expenses

Estado: candidato.

Parches pendientes:

- [HECHO 2026-04-29] Agregar paginacion.
- [HECHO 2026-04-29] Agregar filtros por fecha/categoria/estado.
- [HECHO 2026-04-29] Sacar migraciones/commits automaticos de `GET /expenses` a una tarea explicita. (GET es ahora read-only)
- [DECISION v1] Adjuntos y aprobacion de gastos fuera de alcance en v1. FASE 2.

Condicion para subir: CRUD, asiento contable, bloqueo de gastos de produccion y supplier tenant validation.

### Billing

Estado: candidato si Stripe esta configurado.

Parches pendientes:

- [HECHO 2026-04-29] Manejar `invoice.payment_failed`. (pone status = 'past_due' en tenant_subscriptions)
- [HECHO 2026-04-29] Agregar auditoria de operaciones administrativas. (log AUDIT en subscribe/change-plan/cancel)
- [HECHO 2026-04-29] Confirmar que webhook falla cerrado si falta `STRIPE_WEBHOOK_SECRET`. (error 500 con mensaje legible)
- [HECHO sesion anterior] Corregir frontend para enviar `description` y `customer_name`.

Condicion para subir: checkout, cambio de plan, cancelacion, portal y webhooks firmados.

### Notifications

Estado: candidato.

Parches pendientes:

- [DECISION v1] No hay retry automatico en v1. Los envios fallidos se logean. Retry Celery queda para FASE 2.
- [HECHO 2026-04-29] Evitar fallback SMTP global si se requiere separacion estricta por tenant. (guard con ALLOW_GLOBAL_SMTP_FALLBACK; log warning si se usa el global)
- [DECISION v1] El canal SMS usa WhatsApp via Twilio, no SMS directo. Documentado en INTEGRATION.md.

Condicion para subir: email/in-app/telegram con configuracion por tenant verificada.

### Webhooks

Estado: candidato con confirmacion operativa.

Parches pendientes:

- [REQUISITO DEPLOY] Worker Celery debe estar activo para deliveries. Ver requirements-celery.txt y render.yaml.
- [HECHO 2026-04-29] Guardar secreto de webhook de forma segura o limitar exposicion. (GET normal oculta secreto con ***; GET /{id}/secret requiere permiso webhooks.secret.view)
- [HECHO 2026-04-29] Agregar rotacion/visualizacion controlada del signing secret. (endpoint POST /{id}/rotate-secret con permiso webhooks.secret.rotate)

Condicion para subir: delivery real, retry, firma HMAC y proteccion anti-SSRF.

### CRM

Estado: candidato.

Parches pendientes:

- [HECHO 2026-04-29] Manejar tenant sin moneda configurada sin romper dashboard. (_resolve_tenant_currency retorna "USD" como fallback)
- [HECHO 2026-04-29] Exponer boton de convertir lead si frontend lo requiere. (boton visible en estados new/qualified en List.tsx y Form.tsx)

Condicion para subir: CRUD leads/oportunidades, dashboard y conversion.

### Importador

Estado: candidato parcial.

Parches pendientes:

- [HECHO 2026-04-29] Aislar aprendizaje ML por tenant en `imp_filename_pattern` e `imp_header_doc_type`. (INSERTs bloqueados por defecto; requieren ML_LEARNING_ENABLED=true en env)
- [HECHO 2026-04-29] Revisar encoding corrupto en `DocumentDetail.tsx`. (6 instancias de mojibake corregidas)
- [HECHO 2026-04-29] Confirmar que cache OCR tenant-aware esta en todos los caminos. (verificado: clave incluye tenant_id:hash)

Condicion para subir: permitir OCR/revision/guardado, pero bloquear aprendizaje global si no se corrige.

## Modulos que NO deben subir a produccion todavia

### Einvoicing

Motivo: funcionalidad fiscal core incompleta.

Bloqueos:

- Firma XAdES-BES real existe en worker, pero los Celery tasks registrados siguen siendo stubs que pueden marcar facturas como `AUTHORIZED` sin envio real.
- SRI/SII con implementaciones paralelas e inconsistentes: el endpoint de export usa un flujo y el envio usa otro.
- `infrastructure/einvoice_service.py` conserva firma fake con `hashlib.sha256` y PDF incompleto.
- Falta UI/endpoints de configuracion por tenant para certificado `.p12` y settings SRI/SII.
- El campo SRI `<ambiente>` queda hardcodeado a pruebas en el XML generado.

Decision: no activar en produccion real. Solo sandbox/demo interno.

### Accounting completo

Motivo: riesgo contable.

Bloqueos:

- Numeracion concurrente de asientos.
- Permisos granulares incompletos.
- Cierre/apertura/regularizacion no implementados.
- Reportes contables formales faltantes.
- Asientos automaticos de ventas, compras y caja no integrados.
- [HECHO 2026-04-30] Bug por variable `status`/shadowing corregido. Sigue pendiente validar saldos con nombres de campos inconsistentes.

Decision: permitir solo configuracion basica/POS accounting si las rutas estan protegidas. No venderlo como contabilidad completa.

### Reports avanzado

Motivo: scheduler, limites y exactitud incompletos.

Bloqueos:

- [PARCHEADO 2026-04-30] Creacion de reportes programados cerrada por defecto; falta worker/scheduler real antes de activar `REPORTS_SCHEDULER_ENABLED=true`.
- Reportes grandes pueden seguir ejecutandose en memoria aunque exports CSV/XLSX ya tengan limite operativo.
- Algunos filtros de fecha incompletos.
- Faltan libro mayor, aging, flujo de caja, gastos avanzados.
- [HECHO 2026-04-30] RLS añadido al router tenant.
- `SalesReportGenerator` depende de tablas que pueden no existir o no coincidir con el flujo POS/ventas real.

Decision: habilitar solo reportes simples si tienen rango acotado. No activar schedules.

### Reconciliation

Motivo: auth/modelos/flujo bancario no cerrados.

Bloqueos:

- Auth paralela pendiente de homogeneizar.
- Modelos paralelos con Finance.
- Refund y provider validation incompletos.
- Falta desmatching y conciliacion formal.
- [HECHO 2026-04-30] Webhooks de pago fallan cerrado sin secret/firma. Pendiente validar payloads reales de proveedor.
- RLS/tenant isolation pendiente segun desglose tecnico.
- Importacion de extractos no acepta upload CSV/OFX real; espera JSON ya parseado.

Decision: no activar como modulo productivo completo. Puede quedar en beta interna.

### Documents / Quotes

Motivo: presupuestos no implementados y country packs incompletos.

Bloqueos:

- `quote_to_sales_order` no implementado.
- Solo EcuadorPack; falta EspanaPack si se opera en Espana.
- Faltan endpoints de listado/detalle de documentos.
- No hay frontend dedicado para Documents/Quotes como modulo tenant.

Decision: no ofrecer presupuestos ni validacion fiscal multi-pais hasta fase aparte.

### AI Agent

Motivo: riesgo reputacional/operativo.

Bloqueos:

- Fallback de analisis mock puede devolver informacion falsa.
- Auto-resolve es mock y puede marcar incidentes como resueltos sin aplicar cambios reales.
- Notificaciones pueden devolver `sent (mock)` si faltan credenciales, ocultando fallos operativos.
- Stack traces por email/Telegram.
- Falta control robusto de destinatarios y permisos.

Decision: mantener desactivado o solo admin interno.

### Analytics

Motivo: modulo vacio.

Bloqueos:

- Alcance funcional no definido para v1.
- Sin evidencia validada de router, permisos, tenant isolation, migraciones, frontend productivo o pruebas.

Decision: no registrar como modulo productivo. Mantener oculto por feature flag hasta definir alcance y validar implementacion.

### Restaurant

Motivo: frontend/backend MVP incompleto.

Bloqueos:

- Router no montado en `platform/http/router.py`: los endpoints pueden devolver 404 aunque el frontend exista.
- Cobro/cierre de cuenta no cerrado.
- Cierre de comanda marca `paid` sin flujo de caja, metodo de pago ni comprobante fiscal.
- Impuestos hardcodeados a cero.
- Falta Kitchen Display System (KDS).

Decision: beta o desactivado por feature flag.

### Historical

Motivo: hardening de seguridad y carga pendiente.

Bloqueos:

- [HECHO 2026-04-30] Router historico con `ensure_rls`.
- Upload CSV/XLSX bloqueante en el hilo principal.
- [HECHO 2026-04-30] Limite de tamano de archivo de 10 MB.
- Sin deduplicacion por hash/constraint; re-subir el mismo CSV duplica datos.
- Fechas faltantes se sustituyen por `date.today()`, corrompiendo historicos.

Decision: no activar hasta hardening.

## Frontend transversal antes de produccion

Parches recomendados:

- [HECHO 2026-04-30] Reemplazar `prompt/confirm/alert` nativos en HR, Restaurant, Historical, Products y Users.
- [HECHO sesion anterior] Corregir `billing/Form.tsx` para enviar `description` y `customer_name`.
- [HECHO 2026-04-29] Revisar datos personales POS en `localStorage`.
- [HECHO sesion anterior] Eliminar componentes legacy o muertos que puedan entrar al bundle.
- Reducir/limpiar `console.log/error/warn` productivos.
- Alinear visibilidad de botones con permisos backend nuevos.

## Infraestructura antes de produccion

Parches recomendados:

- [VERIFICADO 2026-04-30] Rate limiting distribuido con Redis para login y Copilot. (ya existian 3 capas: RateLimitMiddleware global, EndpointRateLimiter por IP, y login_rate_limit.py Redis-backed; Copilot tiene _check_ai_rate_limit por tenant)
- [OPERACIONAL] Rotar JWT secret si logs antiguos salieron de entorno real. (accion manual en deploy)
- [OPERACIONAL] Rotar/eliminar logs historicos con secretos. (accion manual en deploy)
- [REQUISITO DEPLOY] Confirmar Celery workers para webhooks, reports, notifications y tareas programadas. (ver requirements-celery.txt y render.yaml)
- [HECHO 2026-04-30] Definir `ENVIRONMENT=production` y variables obligatorias en deploy. (guard en main.py: falla en arranque si faltan SECRET_KEY, DATABASE_URL o ENVIRONMENT)
- [HECHO 2026-04-30] Agregar limites de exportacion y rangos maximos de reportes. (export CSV/XLSX: limit default 5000, max 5000)

## Orden recomendado de trabajo

1. Cerrar parches de seguridad ya identificados en modulos candidatos.
2. Alinear permisos frontend/backend.
3. Ejecutar pruebas enfocadas por flujo: POS, Inventory, Sales, Purchases, Clients, Suppliers, Expenses, Billing.
4. Desactivar por feature flag los modulos bloqueados.
5. Preparar checklist de release con migraciones, variables de entorno, workers y smoke tests.

## Matriz unificada de decision v1

| Modulo | Decision v1 | Bloqueo principal | Accion minima |
|--------|-------------|-------------------|---------------|
| POS | Candidato | Pruebas de flujo pendientes | Smoke test venta/checkout/stock/turno/impresion |
| Inventory | Candidato | Pruebas de flujo pendientes | Smoke test ajuste/transferencia/cycle count/stock item |
| Sales | Candidato con advertencias | Validacion de flujo completo | Smoke test crear/confirmar/cancelar/checkout/factura/promos |
| Purchases | Candidato con parches | Validacion de recepcion y costos | Smoke test compra con lineas, recepcion, stock y costos |
| Products | Candidato parcial | Validar bulk/merge/purge seguro | Ejecutar tests avanzados y smoke CRUD |
| Clients | Candidato | Validar referencias en update/delete | Smoke CRUD, paginacion y tenant isolation |
| Suppliers | Candidato con advertencias | IBAN real sin cifrado en reposo | No almacenar IBAN real en v1 hasta cifrado |
| Expenses | Candidato | Flujo contable y supplier validation | Smoke CRUD, asiento contable y bloqueo produccion |
| Billing | Candidato si Stripe esta configurado | Dependencia operativa Stripe | Probar checkout, cambio plan, cancelacion, portal y webhook firmado |
| Notifications | Candidato | Credenciales por tenant | Probar email/in-app/Telegram y logs de fallo |
| Webhooks | Candidato con requisito deploy | Worker Celery | Confirmar delivery real, retry, firma HMAC y anti-SSRF |
| CRM | Candidato | Pruebas de conversion | Smoke CRUD leads/oportunidades/dashboard/conversion |
| Importador | Candidato parcial | Aprendizaje ML global desactivado | Probar OCR/revision/guardado con ML_LEARNING_ENABLED=false |
| Settings | Candidato transversal | Variables/secretos | Validar configuracion production |
| Users | Candidato transversal | Permisos y sesiones | Validar auth, roles y revocacion |
| Einvoicing | No subir | Stubs fiscales y certificados | Mantener sandbox/demo interno |
| Accounting completo | No subir completo | Reportes/asientos/cierres incompletos | Solo configuracion basica/POS accounting protegida |
| Reconciliation | No subir | RLS/provider validation/refunds pendientes | Beta interna o feature flag |
| Reports avanzado | No subir schedules | Scheduler/exactitud | Solo reportes simples acotados; schedules cerrados por defecto |
| Documents/Quotes | No subir | Quotes y country packs incompletos | Mantener fuera de oferta v1 |
| AI Agent | No subir tenant | Mocks operativos y destinatarios | Solo admin interno si se mantiene |
| Analytics | No subir | Modulo sin alcance validado | Ocultar por feature flag |
| Restaurant | No subir | Router/checkout/fiscal/KDS incompletos | Beta o feature flag |
| Historical | No subir | Upload async/deduplicacion/fechas pendientes | Hardening antes de activar |

## Lista corta para primer pase a produccion

Subir si pasan pruebas y permisos:

- POS
- Inventory
- Sales
- Purchases
- Products
- Clients
- Suppliers
- Expenses
- Billing
- Notifications
- Webhooks
- CRM
- Importador
- Settings
- Users

No subir todavia:

- Einvoicing
- Accounting completo
- Reconciliation
- Reports programados/avanzados
- Documents/Quotes
- AI Agent
- Analytics
- Restaurant
- Historical

## Estado de completitud por modulo (2026-04-29)

| Modulo       | Parches backend | Parches frontend | Decision pendiente | Listo para pruebas |
|--------------|----------------|-----------------|-------------------|-------------------|
| POS          | COMPLETO        | COMPLETO         | pendiente         | SI                 |
| Inventory    | COMPLETO        | COMPLETO         | pendiente         | SI                 |
| Sales        | COMPLETO        | N/A              | pendiente         | SI                 |
| Purchases    | COMPLETO        | COMPLETO         | pendiente         | SI                 |
| Products     | COMPLETO        | N/A              | COMPLETO (12)     | SI                 |
| Clients      | COMPLETO        | N/A              | pendiente         | SI                 |
| Suppliers    | COMPLETO        | COMPLETO         | pendiente         | SI                 |
| Expenses     | COMPLETO        | N/A              | pendiente         | SI                 |
| Billing      | COMPLETO        | COMPLETO         | pendiente         | SI                 |
| Notifications| COMPLETO        | N/A              | pendiente         | SI                 |
| Webhooks     | COMPLETO        | N/A              | pendiente         | SI                 |
| CRM          | COMPLETO        | COMPLETO         | pendiente         | SI                 |
| Importador   | COMPLETO        | COMPLETO         | pendiente         | SI                 |
