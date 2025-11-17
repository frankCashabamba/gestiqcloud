# Migraciones Faltantes / Incompletas

## Resumen Ejecutivo

De **65 tablas** requeridas por los modelos ORM:
- ✅ **~50 tablas** ya están creadas en las migraciones existentes
- ⚠️ **~15 tablas** faltan o están incompletas

---

## Tablas Que Faltan Crear (Críticas)

### 1. ❌ `clients`
- **Estado:** Falta CREATE TABLE completo
- **Modelo:** `app/models/core/clients.py` (Cliente)
- **Dependencias:** tenants
- **Prioridad:** ALTA (base para ventas)

### 2. ❌ `invoices`
- **Estado:** Falta CREATE TABLE
- **Modelo:** `app/models/core/facturacion.py` (Invoice)
- **Campos:** id, tenant_id, number, date, status, total, customer_id
- **Dependencias:** tenants, clients
- **Prioridad:** ALTA

### 3. ❌ `invoice_lines`
- **Estado:** Falta CREATE TABLE
- **Modelo:** `app/models/core/invoiceLine.py` (LineaFactura)
- **Dependencias:** invoices, products
- **Prioridad:** ALTA

### 4. ❌ `store_credits`
- **Estado:** Falta CREATE TABLE
- **Modelo:** `app/models/pos/store_credit.py` (StoreCredit)
- **Campos:** id, tenant_id, customer_id, amount, balance, status
- **Dependencias:** tenants, clients
- **Prioridad:** MEDIA

### 5. ❌ `store_credit_events`
- **Estado:** Falta CREATE TABLE
- **Modelo:** `app/models/pos/store_credit.py` (StoreCreditEvent)
- **Dependencias:** store_credits
- **Prioridad:** MEDIA

### 6. ❌ `incidents`
- **Estado:** Falta CREATE TABLE
- **Modelo:** `app/models/ai/incident.py` (Incident)
- **Campos:** id, tenant_id, incident_type, status, description, priority
- **Dependencias:** tenants
- **Prioridad:** BAJA

### 7. ❌ `notification_channels`
- **Estado:** Falta CREATE TABLE
- **Modelo:** `app/models/ai/incident.py` (NotificationChannel)
- **Dependencias:** tenants
- **Prioridad:** BAJA

### 8. ❌ `notification_log`
- **Estado:** Falta CREATE TABLE
- **Modelo:** `app/models/ai/incident.py` (NotificationLog)
- **Dependencias:** notification_channels
- **Prioridad:** BAJA

### 9. ❌ `einv_credentials`
- **Estado:** Falta CREATE TABLE
- **Modelo:** `app/models/core/einvoicing.py` (EinvoicingCredentials)
- **Campos:** id, tenant_id, provider, credentials_json
- **Dependencias:** tenants
- **Prioridad:** BAJA

### 10. ❌ `sri_submissions`
- **Estado:** Falta CREATE TABLE
- **Modelo:** `app/models/core/einvoicing.py` (SRISubmission)
- **Dependencias:** tenants
- **Prioridad:** BAJA

### 11. ❌ `sii_batches`
- **Estado:** Falta CREATE TABLE
- **Modelo:** `app/models/core/einvoicing.py` (SIIBatch)
- **Dependencias:** tenants
- **Prioridad:** BAJA

### 12. ❌ `sii_batch_items`
- **Estado:** Falta CREATE TABLE
- **Modelo:** `app/models/core/einvoicing.py` (SIIBatchItem)
- **Dependencias:** sii_batches
- **Prioridad:** BAJA

### 13. ❌ `doc_series`
- **Estado:** Falta CREATE TABLE
- **Modelo:** `app/models/pos/doc_series.py` (DocSeries)
- **Campos:** id, tenant_id, code, name, next_number, prefix
- **Dependencias:** tenants
- **Prioridad:** MEDIA (para numeración de docs)

### 14. ❌ `unit_conversions`
- **Estado:** Puede estar incompleto
- **Modelo:** Conversión de unidades de producto
- **Prioridad:** BAJA

### 15. ❌ `base_roles`
- **Estado:** Falta CREATE TABLE
- **Modelo:** `app/models/empresa/empresa.py` (RolBase)
- **Campos:** id, code, name, permissions_json
- **Dependencias:** (ninguna)
- **Prioridad:** MEDIA (roles globales)

---

## Migraciones Incompletas (Parcialmente Completadas)

### ⚠️ `2025-11-17_001_spanish_to_english_names`
- **Estado:** COMPLETO - incluye todos los renombres de columnas
- **Verificar:** Que se ejecute DESPUÉS de 000_baseline

### ⚠️ `000_baseline_modern`
- **Estado:** Parcial - No crea auth_user
- **Solución:** Crear `2025-11-01_100_auth_tables` ✅ HECHO

---

## Plan de Acción

### Fase 1: Críticas (Hacer Primero)

```sql
-- Necesario para ventas/facturas
CREATE TABLE clients (...)
CREATE TABLE invoices (...)
CREATE TABLE invoice_lines (...)
```

**Migración a crear:** `2025-11-01_110_core_business_tables`

### Fase 2: Soporte (Hacer Segundo)

```sql
-- Configuración y control
CREATE TABLE doc_series (...)
CREATE TABLE base_roles (...)
```

**Migración a crear:** `2025-11-01_120_config_tables`

### Fase 3: Complementarias (Hacer Tercero)

```sql
-- POS y créditos
CREATE TABLE store_credits (...)
CREATE TABLE store_credit_events (...)
```

**Migración a crear:** `2025-11-01_130_pos_extensions`

### Fase 4: Electrónico (Hacer Cuarto)

```sql
-- E-invoicing
CREATE TABLE einv_credentials (...)
CREATE TABLE sri_submissions (...)
CREATE TABLE sii_batches (...)
CREATE TABLE sii_batch_items (...)
```

**Migración a crear:** `2025-11-01_140_einvoicing_tables`

### Fase 5: AI/Alertas (Hacer Último)

```sql
-- Incidentes y notificaciones
CREATE TABLE incidents (...)
CREATE TABLE notification_channels (...)
CREATE TABLE notification_log (...)
```

**Migración a crear:** `2025-11-01_150_ai_incident_tables`

---

## Scripts a Crear

### ✅ Creado:
1. `2025-11-01_100_auth_tables` (auth_user, auth_audit, auth_refresh_*)

### ⏳ Por Crear:
1. `2025-11-01_110_core_business_tables` (clients, invoices, invoice_lines)
2. `2025-11-01_120_config_tables` (doc_series, base_roles)
3. `2025-11-01_130_pos_extensions` (store_credits, store_credit_events)
4. `2025-11-01_140_einvoicing_tables` (einv_*, sri_*, sii_*)
5. `2025-11-01_150_ai_incident_tables` (incidents, notifications)

---

## Orden de Ejecución Recomendado

```bash
1. 2025-11-01_000_baseline_modern         ← Existente
2. 2025-11-01_100_auth_tables             ← Nuevo ✅
3. 2025-11-01_110_core_business_tables    ← POR CREAR
4. 2025-11-01_120_config_tables           ← POR CREAR
5. 2025-11-01_130_pos_extensions          ← POR CREAR
6. 2025-11-01_140_einvoicing_tables       ← POR CREAR
7. 2025-11-01_150_ai_incident_tables      ← POR CREAR
8. 2025-11-01_150_modulos_to_english      ← Existente
9. 2025-11-01_160_create_usuarios_usuarioempresa ← Existente
10. ... resto de migraciones ...
11. 2025-11-17_001_spanish_to_english_names   ← Renombres
12. 2025-11-17_800_rolempresas_to_english      ← Renombres
```

---

## Resumen de Tablas por Migración

### 000_baseline_modern: ~40 tablas
- tenants, product_categories, products, warehouses, stock_items, stock_moves
- pos_registers, pos_shifts, pos_receipts, pos_receipt_lines, pos_payments
- auth_refresh_family, auth_refresh_token
- ... y más

### 100_auth_tables (NUEVA): 2 tablas
- auth_user
- auth_audit

### 110_core_business_tables (POR CREAR): 3 tablas
- clients
- invoices
- invoice_lines

### 120_config_tables (POR CREAR): 2 tablas
- doc_series
- base_roles

### 130_pos_extensions (POR CREAR): 2 tablas
- store_credits
- store_credit_events

### 140_einvoicing_tables (POR CREAR): 4 tablas
- einv_credentials
- sri_submissions
- sii_batches
- sii_batch_items

### 150_ai_incident_tables (POR CREAR): 3 tablas
- incidents
- notification_channels
- notification_log

### Resto de migraciones: ~8 tablas
- recipes, recipe_ingredients
- production_orders, production_order_lines
- employees, vacations
- import_batches y familia
- ... etc

---

## Total de Tablas Cubiertas

```
Baseline:           ~40 tablas
Auth (100):         2 tablas
Business (110):     3 tablas
Config (120):       2 tablas
POS (130):          2 tablas
EInvoicing (140):   4 tablas
AI/Incidents (150): 3 tablas
Resto:             ~8 tablas
─────────────────
TOTAL:            ~64 tablas ✅
```

Solo falta `unit_conversions` que puede estar en otra migración.

---

## Próximas Acciones

### Inmediato:
- [ ] Crear `2025-11-01_110_core_business_tables` (CRÍTICO)
- [ ] Validar que clients/invoices sean creadas
- [ ] Ejecutar prueba: `python ops/scripts/migrate_all_migrations.py --dry-run`

### Luego:
- [ ] Crear `2025-11-01_120_config_tables`
- [ ] Crear `2025-11-01_130_pos_extensions`
- [ ] Crear `2025-11-01_140_einvoicing_tables`
- [ ] Crear `2025-11-01_150_ai_incident_tables`

### Final:
- [ ] Ejecutar todas las migraciones en orden
- [ ] Validar esquema con `psql \dt`
- [ ] Ejecutar tests

---

**Nota:** Los nombres de columnas que aparecen con guiones en el checklist se refieren a columnas en español que serán renombradas por la migración `2025-11-17_001_spanish_to_english_names`.
