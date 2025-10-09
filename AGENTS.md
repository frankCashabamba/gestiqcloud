# agents.md — Plan de construcción para GestiQCloud (ERP SaaS multi‑tenant)

Este documento describe **agentes** (roles ejecutables por desarrolladores o por una IA de codificación) con **tareas paso a paso**, entradas/salidas, verificaciones y comandos para implementar el SPEC del proyecto.

> **Convenciones**
> - Repo: `gestiqcloud/` (igual al actual).
> - Migraciones: `ops/migrations/` con control `schema_migrations` (SQL plano, orden lexicográfico).
> - Backend: `apps/backend/` (FastAPI). Frontends: `apps/admin/`, `apps/tenant/`.
> - Gateway: Cloudflare **Worker** (dominios `admin.gestiqcloud.com`, `www.gestiqcloud.com`, `api.gestiqcloud.com`).
> - Queue: **Celery + Redis** (SII/SRI). PDFs: **WeasyPrint**. Observabilidad: **OpenTelemetry**.
> - Tenancy: **UUID `tenant_id`** con RLS. Mapeo 1:1 `tenants.id (uuid)` ↔ `core_empresa.id (int)`.

---

## Agente 0 — Orquestador
**Objetivo:** preparar tableros, ramas, pipelines y checklist global.

**Entradas**: este `agents.md` y el `SPEC` del canvas.

**Salidas**: Issues/PR templates, ramas, etiquetas de versiones.

**Pasos**
1. Crear etiquetas GitHub: `M0-Infra`, `M1-Catalog`, `M2-Sales`, `M3-E-Invoicing`, `observability`, `security`.
2. Crear **Issue principal** por Milestone (M0…M5) y subtareas copiadas de cada agente.
3. Rama base: `feat/multitenant-uuid`. Convención de PR: _squash & merge_ con mensajes tipo `feat(rls): force row-level security + policy with check`.

**Hecho cuando**: existe el tablero con issues enlazados y un PR vacío abierto para M0.

---

## Agente 1 — Tenants y mapeo desde Empresa
**Objetivo:** añadir `tenants` (UUID) sin romper FKs existentes.

**Entradas**: modelo `Empresa` (tabla `core_empresa`).

**Salidas**: tabla `tenants`, datos poblados, modelo SQLAlchemy `Tenant`.

**Pasos**
1. Crear migración `ops/migrations/001_tenants.sql`:
   - Tabla `tenants(id uuid pk default gen_random_uuid(), empresa_id int unique not null fk core_empresa, slug unique, base_currency, country_code, created_at)`.
   - `INSERT INTO tenants (empresa_id, slug) SELECT id, slug FROM core_empresa;`
2. Backend: `app/models/tenant.py` con relación 1:1 `empresa`.
3. Añadir dependencia `pgcrypto` si falta.

**Hecho cuando**: `SELECT COUNT(*) FROM tenants` == `core_empresa`.

---

## Agente 2 — Backfill `tenant_id` en tablas de negocio
**Objetivo:** añadir `tenant_id uuid not null` a todas las tablas multi‑tenant y poblar desde `empresa_id`.

**Entradas**: lista de tablas con `empresa_id`.

**Salidas**: columnas `tenant_id` + FKs e índices.

**Pasos** (repetir por tabla, ejemplo `customers`)
1. Migración `ops/migrations/010_add_tenant_uuid_customers.sql`:
   ```sql
   ALTER TABLE customers ADD COLUMN tenant_id uuid;
   UPDATE customers c SET tenant_id = t.id FROM tenants t WHERE t.empresa_id = c.empresa_id;
   ALTER TABLE customers ALTER COLUMN tenant_id SET NOT NULL,
     ADD CONSTRAINT fk_customers_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE;
   CREATE INDEX IF NOT EXISTS ix_customers_tenant ON customers(tenant_id);
   -- (después) DROP COLUMN empresa_id;
   ```
2. Repetir para: `products`, `price_lists`, `price_list_items`, `warehouses`, `stock_items`, `stock_moves`, `customers`, `sales_orders`, `sales_order_items`, `deliveries`, `invoices`, `invoice_lines`, `payments`, `tax_rules`, `sii_submissions`, `sri_submissions`.

**Hecho cuando**: todas las tablas de negocio tienen `tenant_id NOT NULL` con FK y índice.

---

## Agente 3 — RLS a prueba de fugas
**Objetivo:** asegurar **USING + WITH CHECK**, **FORCE RLS** e índice `(tenant_id)` en todas las tablas con `tenant_id`.

**Entradas**: script existente `scripts/py/apply_rls.py` (mejorado en el canvas).

**Salidas**: políticas aplicadas, índice creado, DEFAULT opcional.

**Pasos**
1. Copiar el script **apply_rls.py (enhanced)** del canvas a `scripts/py/apply_rls.py`.
2. Ejecutar:
   ```bash
   export DATABASE_URL=postgres://user:pass@host:5432/db
   python scripts/py/apply_rls.py --schema public --set-default
   ```
3. Verificar que cada tabla:
   - Tiene `ENABLE RLS` + `FORCE RLS`.
   - Posee una política `rls_tenant` con `USING` y `WITH CHECK`.
   - Tiene índice `ix_<tabla>_tenant_id`.

**Hecho cuando**: `SELECT relname FROM pg_class WHERE relrowsecurity;` lista todas las tablas esperadas.

---

## Agente 4 — Middleware y Auth
**Objetivo:** fijar `SET LOCAL app.tenant_id` por request y cookies seguras.

**Entradas**: `apps/backend/prod.py` y auth actual.

**Salidas**: middleware `TenantRLSMiddleware`, JWT con claim `tenant_id`, cookies `access_token` (Lax) y `refresh_token` (None).

**Pasos**
1. Añadir middleware `TenantRLSMiddleware` (ver SPEC) que hace `SET LOCAL app.tenant_id = :tenant` al abrir la sesión DB.
2. En login/refresh, emitir cookies:
   - `access_token`: `Secure; HttpOnly; SameSite=Lax; Domain=.gestiqcloud.com`
   - `refresh_token`: `Secure; HttpOnly; SameSite=None; Domain=.gestiqcloud.com`
3. Añadir validación: `tenant_id` del JWT debe corresponder con el host/subdominio cuando se active `X-Tenant-Slug`.

**Hecho cuando**: peticiones entre tenants retornan 0 filas aunque se intente forzar IDs.

---

## Agente 5 — API Gateway (Cloudflare Worker)
**Objetivo:** publicar `api.gestiqcloud.com` y reforzar seguridad.

**Entradas**: Worker actual del usuario.

**Salidas**: nuevo Worker con: allow‑list por host, CORS restrictivo, reescritura de cookies, `X-Request-Id`, headers de seguridad.

**Pasos**
1. Crear `workers/edge-gateway.js` con la versión **mejorada** del canvas.
2. DNS: `api.gestiqcloud.com` → Worker Routes.
3. Frontends: `.env` → `VITE_API_BASE=https://api.gestiqcloud.com`.
4. Probar login/refresh en admin y tenant.

**Hecho cuando**: los frontends consumen **solo** `https://api.gestiqcloud.com` y CORS funciona.

---

## Agente 6 — Servicios de dominio (Catálogo, Inventario, Ventas)
**Objetivo:** endpoints CRUD y flujos principales con reservas de stock.

**Entradas**: DDL del SPEC.

**Salidas**: routers FastAPI: `products`, `price_lists`, `warehouses`, `stock`, `customers`, `sales_orders`, `deliveries`, `invoices`, `payments`.

**Pasos**
1. `products`: CRUD + búsquedas; `UNIQUE(tenant_id, sku)`.
2. `warehouses`: múltiples; stock por almacén.
3. `sales_orders`: `confirm` → crea reservas/`stock_moves` tentativos; `deliver` → salida real.
4. `invoices`: `post` → llama a `assign_next_number(...)` (transaccional), congela montos y activa **PDF**.

**Hecho cuando**: flujo `pedido → entrega → factura` funciona end‑to‑end y actualiza stock.

---

## Agente 7 — Numeración por series
**Objetivo:** asegurar numeración única por `(tenant, tipo, año, serie)`.

**Entradas**: tablas `doc_series` y función `assign_next_number` del SPEC.

**Salidas**: DDL aplicado y uso en el endpoint de `post` de factura.

**Pasos**
1. Añadir migraciones `040_series.sql` y `041_series_next.sql`.
2. Usar `SELECT assign_next_number(:tenant, 'invoice', :year, :series)` dentro de la transacción de `POST /invoices/{id}/post`.

**Hecho cuando**: dos posts concurrentes nunca repiten número.

---

## Agente 8 — Facturación electrónica SRI (Ecuador, offline)
**Objetivo:** firmar XAdES-BES, enviar a **Recepción** y consultar **Autorización**.

**Entradas**: entorno SRI (WSDL, .p12 base64, password), tablas `sri_submissions`.

**Salidas**: tareas Celery `sign_and_send(invoice_id)` + estado en DB + PDF con timbre.

**Pasos**
1. Dependencias: `signxml`/`xades`, `zeep` (SOAP).
2. Celery app con cola `sri`; tarea que:
   - Construye XML desde `invoice`.
   - Firma XAdES-BES con `.p12`.
   - Envía a Recepción; si `RECIBIDA` → consulta Autorización.
   - Actualiza `sri_submissions` y `invoices` (número/fecha de autorización) y regenera PDF.
3. Variables ENV por tenant: guardar credenciales cifradas/seguras.

**Hecho cuando**: una factura de prueba pasa a `AUTHORIZED` y el PDF muestra el timbre.

---

## Agente 9 — SII (España)
**Objetivo:** libros IVA emitidas/recibidas por SOAP con certificado.

**Entradas**: cert .p12, NIF, entorno pruebas.

**Salidas**: tarea Celery `build_and_send_sii(batch_id)` y tabla `sii_submissions`.

**Pasos**
1. Generar payloads desde facturas posteadas.
2. Enviar lote; registrar `ACCEPTED/REJECTED` y errores parciales.
3. Reintentos con backoff.

**Hecho cuando**: lote de prueba aceptado sin errores.

---

## Agente 10 — PDFs (WeasyPrint)
**Objetivo:** emitir PDFs de presupuesto/albarán/factura con campos fiscales y QR SRI.

**Entradas**: plantillas Jinja2.

**Salidas**: PDFs generados en `apps/backend/var/invoices/` (o S3) con nombre estable.

**Pasos**
1. Dockerfile: dependencias de WeasyPrint (ver SPEC).
2. Plantillas `templates/invoices/*.html` con estilos impresos.
3. Endpoint `GET /invoices/{id}/pdf` (control de acceso por tenant).

**Hecho cuando**: se descargan PDFs correctos para ES y EC.

---

## Agente 11 — Observabilidad
**Objetivo:** trazas, métricas y logs estructurados.

**Entradas**: OTLP endpoint (tempo/jaeger), Prometheus.

**Salidas**: instrumentación FastAPI/SQLAlchemy/Celery, dashboards básicos.

**Pasos**
1. OpenTelemetry SDK + auto‑instrumentación.
2. `X-Request-Id` propagado desde Worker.
3. Dashboards: latencias p50/p95, error rate, colas Celery, tiempos SRI/SII.

**Hecho cuando**: se ven trazas end‑to‑end y métricas en dashboards.

---

## Agente 12 — CI/CD
**Objetivo:** pipelines GitHub Actions para backend, worker y frontends.

**Entradas**: Dockerfiles y wrangler config.

**Salidas**: 3 pipelines funcionando.

**Pasos**
1. `backend.yml`: ruff + mypy + pytest + build/push imagen + deploy Render + correr migraciones.
2. `worker.yml`: publish con Wrangler al Worker.
3. `frontends.yml`: build Vite y deploy (Pages o contenedores Nginx).

**Hecho cuando**: push a `main` despliega y migra sin intervención.

---

## Agente 13 — Frontends (admin/tenant)
**Objetivo:** apuntar a `api.gestiqcloud.com`, login/refresh con cookies y flujo POS ligero.

**Entradas**: `.env` de Vite.

**Salidas**: Admin y Tenant consumiendo API única y mostrando módulos MVP.

**Pasos**
1. `.env`: `VITE_API_BASE=https://api.gestiqcloud.com`.
2. Adaptar servicios a **Bearer access token** y **refresh por cookie**.
3. Vistas: catálogo, clientes, pedidos, entregas, facturas y reportes básicos.

**Hecho cuando**: se puede hacer la demo completa desde UI tenant.

---

## Agente 14 — Seguridad
**Objetivo:** hardening mínimo.

**Entradas**: Worker, backend, DB.

**Salidas**: HSTS, rate‑limit, tamaños máximos, roles DB sin BYPASSRLS.

**Pasos**
1. Worker: `Strict-Transport-Security`, `X-Frame-Options`, `X-Content-Type-Options`.
2. Backend: límite de carga (uploads), validación de tipos, rate‑limit por usuario/tenant.
3. DB: rol de app `NOBYPASSRLS` y backups + restauración verificada.

**Hecho cuando**: escaneo básico SAST/DAST sin hallazgos críticos.

---

## Agente 15 — QA / Pruebas de aceptación
**Objetivo:** garantizar que el MVP cumple requisitos.

**Entradas**: escenarios de usuario.

**Salidas**: plan de pruebas + datos semillas + resultados.

**Pasos**
1. Semillas por tenant ES/EC (series, IVA, moneda, almacén).
2. Escenarios:
   - Crear pedido → entrega → factura (ES y EC) con diferentes tipos de IVA.
   - SRI: factura de prueba `AUTHORIZED` con PDF timbrado.
   - SII: lote aceptado.
   - RLS: tenant A no ve datos de tenant B.

**Hecho cuando**: todos los escenarios pasan y quedan capturas/artefactos.

---

## Comandos útiles / Makefile (sugerido)
```makefile
.PHONY: db-migrate db-rls api worker admin tenant

DB?=$(DATABASE_URL)

db-migrate:
	psql "$(DB)" -v ON_ERROR_STOP=1 -f ops/migrations/apply.sql

db-rls:
	DATABASE_URL="$(DB)" python scripts/py/apply_rls.py --schema public --set-default

api:
	uvicorn apps.backend.prod:app --host 0.0.0.0 --port 8000

worker:
	celery -A apps.backend.celery_app worker -Q sri,sii -l info

admin tenant:
	npm run --prefix apps/$@ dev
```

---

## Checklist de entrega (MVP)
- [ ] `tenants` + backfill `tenant_id` aplicado.
- [ ] RLS `USING` + `WITH CHECK` + **FORCE** + índices.
- [ ] Gateway en `api.gestiqcloud.com` con cookies seguras y CORS.
- [ ] Flujo ventas/inventario/facturas + numeración atómica.
- [ ] PDFs WeasyPrint.
- [ ] SRI `AUTHORIZED` y SII lote aceptado.
- [ ] OTEL + dashboards básicos.
- [ ] CI/CD (3 pipelines) + backups verificados.

---

## Notas finales
- Mantén `empresa_id` durante 1–2 releases; luego elimina columnas legacy.
- Cualquier `UNIQUE(code)` global → pásalo a `UNIQUE(tenant_id, code)`.
- Si agregas nuevas tablas multi‑tenant, **siempre** incluye `tenant_id uuid not null`, índice, y deja que el script RLS las cubra.
