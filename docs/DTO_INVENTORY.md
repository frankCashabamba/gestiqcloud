# Inventario de DTOs/Schemas del Backend

> **Fecha de generación:** 2026-01-17  
> **Estado:** Análisis completo

## Resumen Ejecutivo

| Métrica | Valor |
|---------|-------|
| Total de archivos schemas.py | 22 |
| Total de DTOs identificados | ~85 |
| DTOs potencialmente duplicados | 12 grupos |
| Prioridad de consolidación | Alta |

---

## 1. Inventario Completo por Módulo

### 1.1 Core/Schemas Base (`app/schemas/`)

| DTO | Campos Principales | Duplicado de |
|-----|-------------------|--------------|
| `UsuarioCreate` | nombre_encargado, apellido_encargado, email, username, password | ⚠️ Similar a `CompanyUserCreate` |
| `EmpresaCreate` | name, slug, tipo_empresa_id, tipo_negocio_id, tax_id, phone, address, city, state, cp, pais, logo, modulos | ⚠️ Similar a `CompanyInSchema` |
| `EmpresaConUsuarioCreate` | empresa, usuario | - |

### 1.2 Configuración (`app/schemas/configuracion.py`)

| DTO | Campos Principales | Duplicado de |
|-----|-------------------|--------------|
| `CompanyCategoryBase` | name | DEPRECATED |
| `CompanyCategoryCreate` | hereda de CompanyCategoryBase | DEPRECATED |
| `CompanyCategory` | id, name | DEPRECATED |
| `RolBaseBase` | name, description, permissions | - |
| `RolBaseCreate` | hereda de RolBaseBase | - |
| `RolBaseUpdate` | permissions | - |
| `RolBase` | id, name, description, permissions | - |
| `GlobalActionPermissionSchema` | id, key, module, description | - |
| `GlobalActionPermissionCreate` | key, module, description | - |
| `GlobalActionPermissionUpdate` | key, module, description | - |
| `AuthenticatedUser` | user_id, is_superadmin, user_type, tenant_id, empresa_slug, plantilla, is_company_admin, permisos, name | - |

### 1.3 Módulos (`app/modules/schemas.py`)

| DTO | Campos Principales | Duplicado de |
|-----|-------------------|--------------|
| `ModuloBase` | name, description, active, icon, url, initial_template, context_type, target_model, context_filters, category | ⚠️ Duplicado de `ModuloOutSchema` |
| `ModuloCreate` | hereda de ModuloBase | - |
| `ModuloOut` | id, + ModuloBase | ⚠️ Duplicado de `ModuloOutSchema` |
| `ModuloUpdate` | name, description, icon, url, initial_template, context_type, target_model, context_filters, category, active | - |
| `EmpresaModuloBase` | module_id, active, expiration_date, initial_template | - |
| `EmpresaModuloCreate` | hereda de EmpresaModuloBase | - |
| `EmpresaModuloOut` | id, tenant_id, company_slug, activation_date, module | - |
| `EmpresaModuloOutAdmin` | id, tenant_id, module_id, active, activation_date, expiration_date, initial_template, company_slug, module | - |
| `ModuloAsignadoBase` | modulo_id | - |
| `ModuloAsignadoCreate` | modulo_id, usuario_id | - |
| `ModuloAsignadoOut` | id, tenant_id, usuario_id, modulo_id, fecha_asignacion, modulo | - |

### 1.4 Módulos Interface (`app/modules/modulos/interface/http/schemas.py`)

| DTO | Campos Principales | Duplicado de |
|-----|-------------------|--------------|
| `ModuloOutSchema` | id, name, url, icon, category, description, initial_template, context_type, target_model, context_filters, active | ⚠️ **DUPLICADO de `ModuloOut`** |

### 1.5 Clientes - Dos Ubicaciones ⚠️

#### `app/modules/clients/schemas.py`

| DTO | Campos Principales | Duplicado de |
|-----|-------------------|--------------|
| `ClienteBase` | name, identificacion, email, phone, address, localidad, state, pais, codigo_postal, is_wholesale | ⚠️ Duplicado |
| `ClienteCreate` | hereda de ClienteBase | ⚠️ Duplicado |
| `ClienteUpdate` | hereda de ClienteBase | - |
| `ClienteOut` | id (int), + ClienteBase | ⚠️ Duplicado (con id: int) |

#### `app/modules/clients/interface/http/schemas.py`

| DTO | Campos Principales | Duplicado de |
|-----|-------------------|--------------|
| `ClienteInSchema` | name, identificacion, email, phone, address, localidad, state, pais, codigo_postal, is_wholesale | ⚠️ **DUPLICADO de `ClienteBase`** |
| `ClienteOutSchema` | id (UUID), name, identificacion, email, phone, address, localidad, state, pais, codigo_postal, is_wholesale | ⚠️ **DUPLICADO de `ClienteOut`** (diferente tipo de id) |

### 1.6 Invoicing (`app/modules/invoicing/schemas.py`)

| DTO | Campos Principales | Duplicado de |
|-----|-------------------|--------------|
| `LineaBase` | description, cantidad, precio_unitario, iva | - |
| `BakeryLine` | sector, bread_type, grams + LineaBase | - |
| `BakeryLineOut` | hereda de BakeryLine | - |
| `WorkshopLine` | sector, spare_part, labor_hours, rate + LineaBase | - |
| `WorkshopLineOut` | hereda de WorkshopLine | - |
| `ClienteSchema` | id, name, email, identificacion | ⚠️ **DUPLICADO parcial de `ClienteOut`** |
| `InvoiceCreate` | numero, supplier, fecha_emision, estado, subtotal, iva, total, cliente_id, lineas | - |
| `InvoiceOut` | id, numero, fecha_emision, estado, subtotal, iva, total, cliente, lineas | - |
| `InvoiceUpdate` | estado, supplier, fecha_emision, lineas | - |
| `FacturaTempCreate` | archivo_nombre, datos, usuario_id | - |
| `FacturaOut` | id, numero, supplier, fecha_emision, monto, estado | ⚠️ Similar a `InvoiceOut` |
| `InvoiceTempOut` | (vacío) | - |

### 1.7 Productos (`app/modules/products/interface/http/schemas.py`)

| DTO | Campos Principales | Duplicado de |
|-----|-------------------|--------------|
| `ProductoInSchema` | name, price, active | - |
| `ProductoOutSchema` | id, name, price, active | - |

### 1.8 Ventas (`app/modules/sales/interface/http/schemas.py`)

| DTO | Campos Principales | Duplicado de |
|-----|-------------------|--------------|
| `SaleBase` | date, total, customer_id, status | ⚠️ Similar a `PurchaseBase` |
| `SaleCreate` | hereda de SaleBase | - |
| `SaleUpdate` | hereda de SaleBase | - |
| `SaleOut` | id (UUID), + SaleBase | - |

### 1.9 Compras (`app/modules/purchases/interface/http/schemas.py`)

| DTO | Campos Principales | Duplicado de |
|-----|-------------------|--------------|
| `PurchaseBase` | date, total, supplier_id, status | ⚠️ Similar a `SaleBase` |
| `PurchaseCreate` | hereda de PurchaseBase | - |
| `PurchaseUpdate` | hereda de PurchaseBase | - |
| `PurchaseOut` | id (int), + PurchaseBase | - |

### 1.10 Proveedores (`app/modules/suppliers/interface/http/schemas.py`)

| DTO | Campos Principales | Duplicado de |
|-----|-------------------|--------------|
| `SupplierContactIn` | type, name, email, phone, notes | - |
| `SupplierAddressIn` | type, line1, line2, city, region, postal_code, country, notes | - |
| `SupplierBase` | name, trade_name, tax_id, country, language, tax_type, tax_withholding, tax_exempt, special_regime, payment_terms, payment_days, early_payment_discount, currency, payment_method, iban, contacts, addresses | - |
| `SupplierCreate` | hereda de SupplierBase | - |
| `SupplierUpdate` | hereda de SupplierBase | - |
| `SupplierContactOut` | id, + SupplierContactIn | - |
| `SupplierAddressOut` | id, + SupplierAddressIn | - |
| `SupplierOut` | id, tenant_id, iban_updated_by, iban_updated_at, contacts, addresses, + SupplierBase | - |
| `SupplierListOut` | id, name, trade_name, email, phone | - |

### 1.11 Usuarios (`app/modules/users/infrastructure/schemas.py`)

| DTO | Campos Principales | Duplicado de |
|-----|-------------------|--------------|
| `CompanyUserBase` | first_name, last_name, email, username | ⚠️ Similar a `UsuarioCreate` |
| `CompanyUserCreate` | password, active, is_company_admin, modules, roles + CompanyUserBase | ⚠️ Similar a `UsuarioCreate` |
| `CompanyUserUpdate` | first_name, last_name, email, username, password, is_company_admin, active, modules, roles | - |
| `CompanyUserOut` | id, tenant_id, is_company_admin, active, modules, roles, last_login_at + CompanyUserBase | - |
| `ModuleOption` | id, name, category, icon | - |
| `CompanyRoleOption` | id, name, description | - |

### 1.12 Empresa/Company (`app/modules/company/interface/http/schemas.py`)

| DTO | Campos Principales | Duplicado de |
|-----|-------------------|--------------|
| `CompanyInSchema` | name, slug, tax_id, phone, address, city, state, postal_code, country, logo, primary_color, active, deactivation_reason, initial_template, website, config_json | ⚠️ **DUPLICADO de `EmpresaCreate`** |
| `CompanyOutSchema` | id, name, slug, modules | - |

### 1.13 Gastos (`app/modules/expenses/interface/http/schemas.py`)

| DTO | Campos Principales | Duplicado de |
|-----|-------------------|--------------|
| `ExpenseBase` | date, amount, supplier_id, concept | - |
| `ExpenseCreate` | hereda de ExpenseBase | - |
| `ExpenseUpdate` | hereda de ExpenseBase | - |
| `ExpenseOut` | id (UUID), + ExpenseBase | - |

### 1.14 Finanzas (`app/modules/finanzas/interface/http/schemas.py`)

| DTO | Campos Principales | Duplicado de |
|-----|-------------------|--------------|
| `MovimientoOut` | id, fecha, concepto, monto | - |

### 1.15 HR (`app/modules/hr/interface/http/schemas.py`)

| DTO | Campos Principales | Duplicado de |
|-----|-------------------|--------------|
| `VacationOut` | id, user_id, start_date, end_date, status | - |

### 1.16 CRM (`app/modules/crm/application/schemas.py`)

| DTO | Campos Principales | Duplicado de |
|-----|-------------------|--------------|
| `LeadBase` | name, company, email, phone, status, source, assigned_to, score, notes, custom_fields | - |
| `LeadCreate` | hereda de LeadBase | - |
| `LeadUpdate` | name, company, email, phone, status, source, assigned_to, score, notes, custom_fields | - |
| `LeadOut` | id, tenant_id, converted_at, opportunity_id, created_at, updated_at + LeadBase | - |
| `OpportunityBase` | lead_id, customer_id, title, description, value, currency, probability, stage, expected_close_date, assigned_to, custom_fields | - |
| `OpportunityCreate` | hereda de OpportunityBase | - |
| `OpportunityUpdate` | lead_id, customer_id, title, description, value, currency, probability, stage, expected_close_date, actual_close_date, assigned_to, lost_reason, custom_fields | - |
| `OpportunityOut` | id, tenant_id, actual_close_date, lost_reason, created_at, updated_at + OpportunityBase | - |
| `ActivityBase` | lead_id, opportunity_id, customer_id, type, subject, description, status, due_date, assigned_to | - |
| `ActivityCreate` | hereda de ActivityBase | - |
| `ActivityUpdate` | type, subject, description, status, due_date, completed_at, assigned_to | - |
| `ActivityOut` | id, tenant_id, created_by, completed_at, created_at, updated_at + ActivityBase | - |
| `DashboardMetrics` | leads, opportunities, activities | - |
| `ConvertLeadRequest` | create_opportunity, opportunity_title, opportunity_value | - |

### 1.17 Imports (`app/modules/imports/schemas.py`)

| DTO | Campos Principales | Duplicado de |
|-----|-------------------|--------------|
| `DocumentoProcesado` | tipo, importe, cliente, invoice, fecha, cuenta, concepto, categoria, origen, documentoTipo | - |
| `DocumentoProcesadoResponse` | archivo, documentos | - |
| `OCRJobEnqueuedResponse` | job_id, status | - |
| `OCRJobStatusResponse` | job_id, status, result, error | - |
| `OkResponse` | ok | - |
| `HayPendientesOut` | hayPendientes | - |
| `BatchCreate` | source_type, origin, file_key, mapping_id, suggested_parser, classification_confidence, ai_enhanced, ai_provider | - |
| `BatchOut` | id, source_type, origin, status, file_key, mapping_id, created_at, suggested_parser, classification_confidence, ai_enhanced, ai_provider | - |
| `UpdateClassificationRequest` | suggested_parser, classification_confidence, ai_enhanced, ai_provider | - |
| `ItemOut` | id, idx, status, raw, normalized, errors, promoted_to, promoted_id, promoted_at, lineage, last_correction | - |
| `ItemPatch` | field, value | - |
| `PromoteResult` | created, skipped, failed | - |
| `IngestRows` | rows, mapping_id, transforms, defaults | - |
| `PromoteItems` | item_ids | - |
| `ImportMappingBase` | name, source_type, version, mappings, transforms, defaults, dedupe_keys | - |
| `ImportMappingCreate` | hereda de ImportMappingBase | - |
| `ImportMappingUpdate` | name, version, mappings, transforms, defaults, dedupe_keys | - |
| `ImportMappingOut` | id, tenant_id, created_at + ImportMappingBase | - |

### 1.18 Admin Config (`app/modules/admin_config/schemas.py`)

| DTO | Campos Principales | Duplicado de |
|-----|-------------------|--------------|
| `IdiomaCreate` | code, name, active | - |
| `IdiomaUpdate` | code, name, active | - |
| `IdiomaRead` | id, code, name, active | - |
| `MonedaCreate` | code, name, symbol, active | - |
| `MonedaUpdate` | code, name, symbol, active | - |
| `MonedaRead` | id, code, name, symbol, active | - |
| `PaisCreate` | code, name, active | - |
| `PaisUpdate` | code, name, active | - |
| `PaisRead` | id, code, name, active | - |
| `DiaSemanaCreate` | code, name, order | - |
| `DiaSemanaUpdate` | code, name, order | - |
| `DiaSemanaRead` | id, code, name, order | - |
| `HorarioAtencionCreate` | weekday_id, start_time, end_time | - |
| `HorarioAtencionUpdate` | weekday_id, start_time, end_time | - |
| `HorarioAtencionRead` | id, weekday_id, start_time, end_time | - |
| `SectorPlantillaCreate` | name, code, description, template_config, active | - |
| `SectorPlantillaUpdate` | name, code, description, template_config, active | - |
| `SectorPlantillaRead` | id, name, code, description, template_config, active, config_version | - |
| `TipoEmpresaCreate` | name, description, active | - |
| `TipoEmpresaUpdate` | name, description, active | - |
| `TipoEmpresaRead` | id, name, description, active | - |
| `TipoNegocioCreate` | name, description | - |
| `TipoNegocioUpdate` | name, description | - |
| `TipoNegocioRead` | id, name, description, active | - |

### 1.19 Canonical Schema (`app/modules/imports/domain/canonical_schema.py`)

| DTO | Campos Principales | Duplicado de |
|-----|-------------------|--------------|
| `TaxBreakdownItem` | rate, amount, code, base | TypedDict (no Pydantic) |
| `TotalsBlock` | subtotal, tax, total, tax_breakdown, discount, withholding | TypedDict |
| `PartyInfo` | name, tax_id, country, address, email, phone | TypedDict |
| `DocumentLine` | desc, qty, unit, unit_price, total, tax_code, tax_amount | TypedDict |
| `PaymentInfo` | method, iban, card_last4, reference | TypedDict |
| `BankTxInfo` | amount, direction, value_date, narrative, counterparty, external_ref | TypedDict |
| `RoutingProposal` | target, category_code, account, confidence, vendor_id | TypedDict |
| `AttachmentInfo` | file_key, mime, type, size, pages | TypedDict |
| `ProductInfo` | name, sku, category, description, price, stock, unit, currency, supplier, barcode | TypedDict |
| `ExpenseInfo` | description, amount, expense_date, category, subcategory, payment_method, vendor, receipt_number, notes | TypedDict |
| `CanonicalDocument` | doc_type, country, currency, issue_date, due_date, invoice_number, vendor, buyer, totals, lines, payment, bank_tx, product, expense, routing_proposal, attachments, metadata, source, confidence | TypedDict |

---

## 2. DTOs Potencialmente Duplicados

### 2.1 CRÍTICO: Clientes (3 ubicaciones)

| Ubicación | DTOs | Problema |
|-----------|------|----------|
| `modules/clients/schemas.py` | ClienteBase, ClienteCreate, ClienteUpdate, ClienteOut | id: **int** |
| `modules/clients/interface/http/schemas.py` | ClienteInSchema, ClienteOutSchema | id: **UUID** |
| `modules/invoicing/schemas.py` | ClienteSchema | Solo campos parciales |

**Impacto:** Inconsistencia de tipos (int vs UUID) causa errores en runtime.

### 2.2 CRÍTICO: Módulos (2 ubicaciones)

| Ubicación | DTOs | Problema |
|-----------|------|----------|
| `modules/schemas.py` | ModuloBase, ModuloCreate, ModuloOut, ModuloUpdate | Completo |
| `modules/modulos/interface/http/schemas.py` | ModuloOutSchema | Duplicado funcional |

**Impacto:** Mantenimiento doble, posible divergencia.

### 2.3 ALTO: Empresa/Company (2 ubicaciones)

| Ubicación | DTOs | Problema |
|-----------|------|----------|
| `schemas/schemas.py` | EmpresaCreate, EmpresaConUsuarioCreate | Campos en español (cp, pais) |
| `modules/company/interface/http/schemas.py` | CompanyInSchema, CompanyOutSchema | Campos en inglés con aliases |

**Impacto:** Inconsistencia de naming, confusión para desarrolladores.

### 2.4 ALTO: Usuarios (2 ubicaciones)

| Ubicación | DTOs | Problema |
|-----------|------|----------|
| `schemas/schemas.py` | UsuarioCreate | nombre_encargado, apellido_encargado |
| `modules/users/infrastructure/schemas.py` | CompanyUserCreate | first_name, last_name |

**Impacto:** Diferentes convenciones de naming para el mismo concepto.

### 2.5 MEDIO: Ventas vs Compras (similares)

| Módulo | DTOs | Campos |
|--------|------|--------|
| Sales | SaleBase, SaleCreate, SaleUpdate, SaleOut | date, total, customer_id, status |
| Purchases | PurchaseBase, PurchaseCreate, PurchaseUpdate, PurchaseOut | date, total, supplier_id, status |

**Oportunidad:** Crear `TransactionBase` compartido.

### 2.6 MEDIO: Invoicing duplicados internos

| DTO | Problema |
|-----|----------|
| InvoiceOut | Factura completa |
| FacturaOut | Similar pero con `monto` en vez de `total` |

---

## 3. Recomendaciones de Consolidación

### 3.1 Acciones Inmediatas (Sprint Actual)

| # | Acción | Archivos Afectados | Esfuerzo |
|---|--------|-------------------|----------|
| 1 | Unificar schemas de Cliente | `clients/schemas.py`, `clients/interface/http/schemas.py`, `invoicing/schemas.py` | 4h |
| 2 | Eliminar `ModuloOutSchema` duplicado | `modules/modulos/interface/http/schemas.py` | 1h |
| 3 | Consolidar EmpresaCreate/CompanyInSchema | `schemas/schemas.py`, `company/interface/http/schemas.py` | 3h |

### 3.2 Acciones Corto Plazo (1-2 Sprints)

| # | Acción | Beneficio |
|---|--------|-----------|
| 4 | Crear `shared/schemas/base.py` con schemas comunes | Reutilización |
| 5 | Unificar UsuarioCreate/CompanyUserCreate | Consistencia |
| 6 | Crear TransactionBase para Sales/Purchases | DRY |
| 7 | Estandarizar tipos de ID (preferir UUID) | Consistencia |

### 3.3 Acciones Largo Plazo

| # | Acción | Beneficio |
|---|--------|-----------|
| 8 | Migrar todos los schemas a convención inglesa | Consistencia |
| 9 | Eliminar schemas DEPRECATED (Q1 2026) | Limpieza |
| 10 | Documentar schemas con OpenAPI examples | DX |

---

## 4. Plan de Consolidación

### Fase 1: Clientes (Prioridad Crítica)

```
1. Definir ClienteBase canónico en shared/schemas/cliente.py
2. Usar UUID como tipo de ID estándar
3. Deprecar schemas duplicados con warnings
4. Migrar rutas HTTP a usar schemas unificados
5. Eliminar schemas legacy
```

### Fase 2: Módulos

```
1. Mantener ModuloOut en modules/schemas.py como fuente única
2. Eliminar ModuloOutSchema de modules/modulos/interface/http/
3. Actualizar imports en routers
```

### Fase 3: Empresa/Company

```
1. Definir CompanySchema canónico con campos en inglés
2. Mantener aliases para compatibilidad
3. Deprecar EmpresaCreate
4. Migrar onboarding a usar CompanySchema
```

### Fase 4: Usuarios

```
1. Unificar en CompanyUserCreate como estándar
2. Deprecar UsuarioCreate
3. Actualizar flujos de registro
```

---

## 5. Archivos de Schemas por Ubicación

```
apps/backend/app/
├── schemas/
│   ├── schemas.py              # UsuarioCreate, EmpresaCreate
│   └── configuracion.py        # Roles, Permisos, AuthenticatedUser
├── modules/
│   ├── schemas.py              # ModuloBase, EmpresaModulo*
│   ├── accounting/schemas.py   # (vacío)
│   ├── admin_config/schemas.py # Idioma, Moneda, Pais, etc.
│   ├── clients/
│   │   ├── schemas.py          # ClienteBase ⚠️ DUPLICADO
│   │   └── interface/http/schemas.py  # ClienteInSchema ⚠️ DUPLICADO
│   ├── company/interface/http/schemas.py  # CompanyInSchema ⚠️ DUPLICADO
│   ├── crm/application/schemas.py  # Lead, Opportunity, Activity
│   ├── expenses/interface/http/schemas.py  # ExpenseBase
│   ├── finanzas/interface/http/schemas.py  # MovimientoOut
│   ├── hr/interface/http/schemas.py  # VacationOut
│   ├── imports/
│   │   ├── schemas.py          # Batch, Item, ImportMapping
│   │   └── domain/canonical_schema.py  # TypedDicts canónicos
│   ├── invoicing/schemas.py    # Lineas, Facturas
│   ├── modulos/interface/http/schemas.py  # ModuloOutSchema ⚠️ DUPLICADO
│   ├── products/interface/http/schemas.py  # ProductoIn/OutSchema
│   ├── purchases/interface/http/schemas.py  # PurchaseBase
│   ├── sales/interface/http/schemas.py  # SaleBase
│   ├── suppliers/interface/http/schemas.py  # SupplierBase
│   └── users/infrastructure/schemas.py  # CompanyUserBase
└── admin/
    ├── tipo_negocio/schemas.py  # shim to legacy
    ├── tipo_empresa/schemas.py  # shim to legacy
    └── settings_admin/schemas.py  # shim to legacy
```

---

## 6. Inconsistencias de Naming Detectadas

| Patrón Español | Patrón Inglés | Recomendación |
|----------------|---------------|---------------|
| `ClienteBase` | `ClienteInSchema` | Usar sufijo `Schema` |
| `nombre_encargado` | `first_name` | Usar inglés |
| `cp` | `postal_code` | Usar inglés |
| `pais` | `country` | Usar inglés |
| `monto` | `amount` | Usar inglés |
| `fecha` | `date` | Usar inglés |
| `FacturaOut` | `InvoiceOut` | Usar inglés |

---

## 7. Métricas de Deuda Técnica

| Categoría | Cantidad | Impacto |
|-----------|----------|---------|
| DTOs completamente duplicados | 4 | Alto |
| DTOs parcialmente duplicados | 6 | Medio |
| Inconsistencias de tipos (int vs UUID) | 3 | Crítico |
| Schemas deprecados sin eliminar | 3 | Bajo |
| Mezcla español/inglés | 8+ | Medio |

---

## Próximos Pasos

1. [ ] Revisar este inventario con el equipo
2. [ ] Priorizar consolidación de Clientes (crítico)
3. [ ] Crear ticket para cada grupo de duplicados
4. [ ] Establecer guía de estilo para nuevos schemas
5. [ ] Configurar linter para detectar duplicados futuros
