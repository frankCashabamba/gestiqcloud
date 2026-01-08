# Contratos de API y cambios

Contratos mínimos por módulo. Mantener sincronizados con `apps/packages/api-types` y `apps/packages/endpoints`.

## Auth / Identity
- **Admin** (base `/api/v1/admin/auth`)
  - `POST /login` `{ identificador, password }` → `200 { access_token, token_type:"bearer", scope:"admin" }` + cookies `access_token` (Lax) y `refresh_token` (HttpOnly, path `/admin/auth/refresh`). Errores: 401 credenciales inválidas, 429 rate-limit, 500 refresh_family_error.
  - `POST /refresh` (cookie) → `200 { access_token, token_type:"bearer" }` o 401 reuse.
  - `POST /logout` → `{ ok:true }` (revoca familia best-effort y borra cookies).
  - `GET /csrf` → `{ ok:true, csrfToken }` + cookie legible `csrf_token`.
- **Tenant** (base `/api/v1/tenant/auth`)
  - `POST /login` `{ identificador, password }` → `200 { access_token, token_type:"bearer", scope:"tenant", tenant_id, empresa_slug?, is_company_admin }` + cookies (refresh path `/tenant/auth/refresh`).
  - `POST /refresh` (cookie) → `200 { access_token, expires_in }` o 401 reuse.
  - `POST /logout`, `GET /csrf` análogo a admin.
  - `POST /set-password` `{ token, password }` → `{ ok:true }` o `400 invalid_or_expired_token|weak_password`, `404 user_not_found`.
- **Compat**: añadir nuevos claims como opcionales; cambios en paths/cookies son breaking. Ver `apps/backend/app/api/v1/{tenant,admin}/auth.py`.

## Company Settings (base `/api/v1/company/settings`)
- `GET/PUT /general` `{ locale, timezone, currency, ... }`
- `GET/PUT /branding` `{ logo_url?, color_primario?, ... }`
- `GET/PUT /fiscal` `{ tax:{ enabled, default_rate }, ... }` (PUT requiere `is_company_admin`).
- `GET/PUT /pos` `{ tax:{ enabled, default_rate }, receipt_width_mm?, ... }` (`is_company_admin`).
- `GET/PUT /horarios`, `GET/PUT /limites` (JSON libre).
- `GET /fields?module=clientes&empresa=<slug>` → `{ module, empresa?, items:[{field,visible,required,ord,label?,help?}] }`
- `GET /theme?empresa=<slug>` → tokens de UI `{ colors, brand, typography, sector }`
- **Admin field-config** (base `/api/v1/admin/field-config`):
  - `GET/PUT /sector` (campos por sector), `PUT /tenant`, `PUT /tenant/mode`, `GET /ui-plantillas`, `GET /ui-plantillas/health`.
- **Errores**: 401/403 sin claims o sin `is_company_admin`, 400 si falta module/sector, 404 empresa no encontrada.
- **Compat**: nuevos campos deben ser opcionales; defaults seguros en `theme` para no romper front. Reflejar en `api-types/settings.ts`.

## Ventas / POS (base `/api/v1/tenant/pos`)
- `GET /registers` → lista cajas `{id,name,code,...}`.
- `POST /registers` `{ name, code?, default_warehouse_id?, metadata? }` → 201 `{ id, ... }`.
- `POST /shifts` `{ register_id, opening_float }` → `{ shift_id, status:"open" }`; `POST /shifts/{id}/close` `{ cash_counted, notes? }` → arqueo y cierre.
- `POST /receipts` `{ shift_id, register_id, lines:[{product_id,qty,unit_price,tax_rate?,discount_pct?}], payments:[{method,amount,ref?}], notes? }` → 201 `{ id, status, total, balance, payments, lines }`.
- `POST /receipts/{id}/checkout` `{ payments:[...], totals? }` → aplica pagos y actualiza saldo.
- `POST /receipts/{id}/to_invoice` / `/refund` / `/post` (movimientos stock) / `/print` (HTML ticket).
- `GET /shifts` y `/receipts` con filtros (fecha, status, register_id); `GET /health` simple.
- **Errores**: 400 validación (qty>0, stock move), 401 claims ausentes, 409 stock negativo o estado inválido.
- **Compat**: respeta `pos.tax.default_rate` y `fiscal.tax.default_rate`. Nuevos campos de línea deben ser opcionales. Ver `app/modules/pos/interface/http/tenant.py`.

## Payments / Reconciliation (base `/api/v1/reconciliation`)
- `POST /link` `{ bank_transaction_id:int, invoice_id:int, amount:float }` → `{ ok:true, invoice_id, paid_total, status }` (actualiza `payments` y estado factura).
- `GET /suggestions?since&until&tolerance` → lista de sugerencias `{ bank_transaction_id, invoice_id, score, amount, days_diff }`.
- **Errores**: 404 bank_tx/invoice no encontrado, 400 validación. Compat: no idempotencia estricta, evitar doble `link` sobre misma factura.

## Facturación (base `/api/v1/tenant/facturacion`)
- `GET /` lista facturas (filtros `estado|q|desde|hasta`).
- `POST /` `InvoiceCreate` → crea factura en borrador.
- `PUT /{id}` actualiza borrador; `DELETE /{id}` anula (no `paid`).
- `POST /{id}/emitir` → cambia estado (usa `factura_crud`), `GET /{id}` detalle, `GET /{id}/pdf` → PDF (WeasyPrint/Jinja2; 501 si falta).
- `POST /{id}/send_email` → `{ ok:true }` (usa email cliente; 404 si falta).
- **Compat**: campos nuevos opcionales; PDF depende de template `INVOICE_PDF_TEMPLATE`.

## E-Invoicing (base `/api/v1/tenant/einvoicing`)
- `POST /send/{invoice_id}` `{ country:"EC|ES", period? }` → 202 `{ task_id }` o respuesta síncrona si no hay Celery.
- `GET /status/{kind}/{ref}` (`kind`: `sri|sii`) → `{ id, status, error? }`.
- `POST /explain_error` `{ kind, id }` → `{ explanation }`.
- **Errores**: 400 `unsupported_country|kind`, 404 no encontrado. Compat: mantener `country`/`kind` valores actuales; nuevas integraciones deben versionarse.

## Inventario (base `/api/v1/tenant/inventory`)
- `GET /warehouses` → `[ { id, code, name, is_active, metadata } ]`
- `POST /warehouses` → 201 `{ id,... }`; `PUT/GET/DELETE /warehouses/{id}` (204 delete).
- `GET /stock?warehouse_id?&product_id?` → movimientos/stock agregados.
- `POST /stock/adjust` `{ product_id, warehouse_id, qty_delta, reason? }` → `{ id, qty }`
- `POST /stock/transfer` `{ from_warehouse_id, to_warehouse_id, product_id, qty }` → `{ ok:true }`
- `POST /stock/cycle_count` `{ warehouse_id, product_id, counted_qty }` → actualiza stock.
- Alertas: `GET/POST /alerts/configs`, `PUT /alerts/configs/{id}`, `DELETE /alerts/configs/{id}`, `POST /alerts/test/{id}`, `POST /alerts/check`, `GET /alerts/history`.
- **Errores**: 400 validación, 404 warehouse/stock no encontrado, 409 saldo negativo si reglas lo impiden.

## Normas recomendadas
- Introducir campos nuevos como opcionales primero; volverlos obligatorios solo tras adaptar front.
- Mantener compatibilidad temporal y documentar deprecaciones.
- Probar admin/tenant con backend nuevo antes de desplegar.

## Cómo proponer cambios (checklist)
- Crear issue con: qué cambia, por qué, consumidores afectados (admin/tenant/terceros) y riesgos de compatibilidad.
- Marcar si es breaking change y plan de rollout (campo opcional -> obligatorio, endpoints nuevos vs deprecados).
- Adjuntar ejemplos de request/response antes/después, incluyendo campos opcionales y defaults.
- Añadir tests de contrato (unit + e2e/mock) y, si aplica, fixtures de `apps/packages/api-types`.
- Avisar a front (admin/tenant) y coordinar fecha de despliegue; versionar si rompe compatibilidad.

## Plantilla mínima por endpoint
```
Ruta: /api/v1/<context>/<recurso> (método)
Auth: <anonimo|tenant|admin|scope> ; Headers especiales si aplica
Request: { ...campos, opcionales/obligatorios, defaults }
Response 2xx: { ...payload, paginación/metadata } ; códigos 201/202 si aplica
Errores: 400 (validación), 401/403 (auth), 404, 409 (conflicto), 422 (schema), 500
Notas: idempotencia, límites, side-effects, dependencias de settings/feature flags
Tests: caso feliz, validación, permisos, estados límite
Consumidores: admin/<feature>, tenant/<feature>, terceros
```

## Matriz de compatibilidad sugerida
- Campos nuevos: opcionales >=1 sprint; logs de uso para decidir cuándo hacerlos obligatorios.
- Endpoints nuevos: agregar versiones coexistiendo con los actuales; deprecar cuando front esté migrado.
- Cambios de schema: publicar PR en `apps/packages/api-types` + aviso en Slack/Changelog.
- Webhooks: mantener versionado por header (`X-Webhook-Version`) o path si aplica; validar firma siempre.

## Lista de pendientes a documentar
- Completar contratos por módulo (ver `docs/modules-index.md`) y reflejarlos en `apps/packages/api-types`.
- Incluir headers de seguridad exactos para webhooks de pagos/einvoicing/imports.
