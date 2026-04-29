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
- Importador OCR: cache incluye tenant.
- Webhooks: validacion anti-SSRF basica.
- Inventory: ajustes negativos bloqueados; cycle count y sync requieren permisos especificos.
- Products: purge destructivo por DELETE bloqueado; purge real exige POST con permiso y confirmacion; merge de duplicados exige permiso y solo actualiza tablas con `tenant_id`; deteccion de similares queda limitada por `scan_limit`.
- Suppliers: `PUT` acepta payload parcial, IBAN se normaliza y valida con checksum, y `tax_id` duplicado por tenant devuelve 409.
- Billing frontend: `customer_name`, `description` y `notes` ya se envian al backend al crear/editar factura.

## Modulos candidatos a produccion con parches

### POS

Estado: candidato fuerte.

Parches pendientes:

- Revisar devolucion parcial si es requerida para el primer release; si no, documentar como fuera de alcance.
- Alinear permisos frontend con backend para acciones sensibles.
- Revisar datos personales en `localStorage` del frontend POS.
- Eliminar o aislar `tpv_pro.html` legacy del build/productivo.

Condicion para subir: pruebas de venta, checkout, descuento de stock, cierre de turno e impresion.

### Inventory

Estado: candidato fuerte.

Parches pendientes:

- Exponer o documentar valorizacion de inventario si el negocio la necesita en v1.
- Confirmar scheduler de alertas o dejar solo ejecucion manual documentada.
- Revisar UI para permisos nuevos: `inventory.stock.adjust`, `inventory.cycle_count.manage`, `inventory.stock.sync`.
- Confirmar que `get_stock` no muestra warehouses cross-tenant en consultas con joins.

Condicion para subir: pruebas de ajuste, transferencia, cycle count, stock move y stock item.

### Sales

Estado: candidato con advertencias.

Parches pendientes:

- Definir si el estado `paid` se maneja desde checkout/factura o crear endpoint formal de pago.
- Agregar paginacion real a listados de ordenes.
- Evitar fallback de auditoria con UUID aleatorio en checkout si falta `user_id`.
- Marcar use cases stub como deprecated o conectarlos al flujo real para evitar usos futuros incorrectos.

Condicion para subir: crear, confirmar, cancelar, checkout, factura y promociones probados.

### Purchases

Estado: candidato con parches.

Parches pendientes:

- Evitar hard delete si la compra ya tuvo recepciones o stock moves.
- Agregar filtros/busqueda basicos.
- Definir flujo de aprobacion antes de recibir o dejarlo fuera de alcance.
- Validar selector de proveedor en frontend para que `supplier_id` sea real.

Condicion para subir: crear compra con lineas, recibir mercancia, validar stock y costos.

### Products

Estado: candidato parcial.

Parches pendientes:

- Unificar mecanismo de tenant/auth en endpoints que aun usen helpers antiguos.
- Agregar pruebas especificas para `duplicates/similar`, `duplicates/merge` y `POST /purge`.
- Definir si el permiso de purge debe ser solo owner/admin o si `products.delete` es suficiente para v1.

Condicion para subir: CRUD, stock visible, categorias, bulk operations y merge seguro por tenant.

### Clients

Estado: candidato.

Parches pendientes:

- Agregar busqueda por nombre/email/identificacion.
- Tipar dominio con UUID para evitar deuda futura.
- Definir si historial de compras y saldo/credito entran en v1 o fase posterior.

Condicion para subir: CRUD, paginacion, tenant isolation, update y delete con referencias.

### Suppliers

Estado: candidato con advertencias.

Parches pendientes:

- Validar coincidencia `iban_confirmacion` tambien en frontend.
- Enmascarar IBAN tambien en vistas donde no sea estrictamente necesario.
- Definir constraint DB de `tax_id` unico por tenant.
- Evaluar cifrado en reposo para IBAN antes de usar datos reales.

Condicion para subir: no exponer IBAN completo en listados y validar datos bancarios.

### Expenses

Estado: candidato.

Parches pendientes:

- Agregar paginacion.
- Agregar filtros por fecha/categoria/estado.
- Sacar migraciones/commits automaticos de `GET /expenses` a una tarea explicita.
- Adjuntos y aprobacion pueden quedar fuera de v1 si se documenta.

Condicion para subir: CRUD, asiento contable, bloqueo de gastos de produccion y supplier tenant validation.

### Billing

Estado: candidato si Stripe esta configurado.

Parches pendientes:

- Manejar `invoice.payment_failed`.
- Agregar auditoria de operaciones administrativas.
- Confirmar que webhook falla cerrado si falta `STRIPE_WEBHOOK_SECRET`.
- Corregir frontend para enviar `description` y `customer_name`.

Condicion para subir: checkout, cambio de plan, cancelacion, portal y webhooks firmados.

### Notifications

Estado: candidato.

Parches pendientes:

- Documentar que no hay retry automatico o agregar job de retry.
- Evitar fallback SMTP global si se requiere separacion estricta por tenant.
- Aclarar que canal SMS actual es WhatsApp/Twilio, no SMS real.

Condicion para subir: email/in-app/telegram con configuracion por tenant verificada.

### Webhooks

Estado: candidato con confirmacion operativa.

Parches pendientes:

- Confirmar worker Celery de deliveries en despliegue.
- Guardar secreto de webhook de forma segura o limitar exposicion.
- Agregar rotacion/visualizacion controlada del signing secret.

Condicion para subir: delivery real, retry, firma HMAC y proteccion anti-SSRF.

### CRM

Estado: candidato.

Parches pendientes:

- Manejar tenant sin moneda configurada sin romper dashboard.
- Exponer boton de convertir lead si frontend lo requiere.

Condicion para subir: CRUD leads/oportunidades, dashboard y conversion.

### Importador

Estado: candidato parcial.

Parches pendientes:

- Aislar aprendizaje ML por tenant en `imp_filename_pattern` e `imp_header_doc_type`.
- Revisar encoding corrupto en `DocumentDetail.tsx`.
- Confirmar que cache OCR tenant-aware esta en todos los caminos.

Condicion para subir: permitir OCR/revision/guardado, pero bloquear aprendizaje global si no se corrige.

## Modulos que NO deben subir a produccion todavia

### Einvoicing

Motivo: funcionalidad fiscal core incompleta.

Bloqueos:

- Firma XAdES-BES/PKCS#12 no completa.
- SRI/SII con implementaciones paralelas e inconsistentes.
- Stubs que simulan envios.
- PDF y credenciales cifradas pendientes de resolver.

Decision: no activar en produccion real. Solo sandbox/demo interno.

### Accounting completo

Motivo: riesgo contable.

Bloqueos:

- Numeracion concurrente de asientos.
- Permisos granulares incompletos.
- Cierre/apertura/regularizacion no implementados.
- Reportes contables formales faltantes.

Decision: permitir solo configuracion basica/POS accounting si las rutas estan protegidas. No venderlo como contabilidad completa.

### Reports avanzado

Motivo: scheduler, limites y exactitud incompletos.

Bloqueos:

- Reportes programados sin worker confirmado.
- Rangos sin limite y reportes grandes en memoria.
- Algunos filtros de fecha incompletos.
- Faltan libro mayor, aging, flujo de caja, gastos avanzados.

Decision: habilitar solo reportes simples si tienen rango acotado. No activar schedules.

### Reconciliation

Motivo: auth/modelos/flujo bancario no cerrados.

Bloqueos:

- Auth paralela pendiente de homogeneizar.
- Modelos paralelos con Finance.
- Refund y provider validation incompletos.
- Falta desmatching y conciliacion formal.

Decision: no activar como modulo productivo completo. Puede quedar en beta interna.

### Documents / Quotes

Motivo: presupuestos no implementados y country packs incompletos.

Bloqueos:

- `quote_to_sales_order` no implementado.
- Solo EcuadorPack; falta EspanaPack si se opera en Espana.

Decision: no ofrecer presupuestos ni validacion fiscal multi-pais hasta fase aparte.

### AI Agent

Motivo: riesgo reputacional/operativo.

Bloqueos:

- Fallback de analisis mock puede devolver informacion falsa.
- Stack traces por email/Telegram.
- Falta control robusto de destinatarios y permisos.

Decision: mantener desactivado o solo admin interno.

### Analytics

Motivo: modulo vacio.

Decision: no registrar como modulo productivo.

### Restaurant

Motivo: frontend/backend MVP incompleto.

Bloqueos:

- Prompt nativo, API hardcodeada, sin i18n.
- Cobro/cierre de cuenta no cerrado.

Decision: beta o desactivado por feature flag.

### Historical

Motivo: UX y RLS pendientes.

Bloqueos:

- `alert/confirm` nativos.
- Router historico sin `ensure_rls` segun auditoria.

Decision: no activar hasta hardening.

## Frontend transversal antes de produccion

Parches recomendados:

- Reemplazar `prompt/confirm/alert` nativos en HR, Restaurant, Historical, Products y Users.
- Corregir `billing/Form.tsx` para enviar `description` y `customer_name`.
- Revisar datos personales POS en `localStorage`.
- Eliminar componentes legacy o muertos que puedan entrar al bundle.
- Reducir/limpiar `console.log/error/warn` productivos.
- Alinear visibilidad de botones con permisos backend nuevos.

## Infraestructura antes de produccion

Parches recomendados:

- Rate limiting distribuido con Redis para login y Copilot.
- Rotar JWT secret si logs antiguos salieron de entorno real.
- Rotar/eliminar logs historicos con secretos.
- Confirmar Celery workers para webhooks, reports, notifications y tareas programadas.
- Definir `ENVIRONMENT=production` y variables obligatorias en deploy.
- Agregar limites de exportacion y rangos maximos de reportes.

## Orden recomendado de trabajo

1. Cerrar parches de seguridad ya identificados en modulos candidatos.
2. Alinear permisos frontend/backend.
3. Ejecutar pruebas enfocadas por flujo: POS, Inventory, Sales, Purchases, Clients, Suppliers, Expenses, Billing.
4. Desactivar por feature flag los modulos bloqueados.
5. Preparar checklist de release con migraciones, variables de entorno, workers y smoke tests.

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
