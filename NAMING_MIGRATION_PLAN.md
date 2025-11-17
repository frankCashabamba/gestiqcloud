# Plan de Migración: Español → Inglés

## Cambios de Tablas

| Español | Inglés | Ubicación |
|---------|--------|-----------|
| proveedores | suppliers | suppliers/proveedor.py |
| proveedor_contactos | supplier_contacts | suppliers/proveedor.py |
| proveedor_direcciones | supplier_addresses | suppliers/proveedor.py |
| ventas | sales | sales/venta.py |
| compras | purchases | purchases/compra.py |
| compra_lineas | purchase_lines | purchases/compra.py |
| nominas | payrolls | hr/nomina.py |
| nomina_conceptos | payroll_items | hr/nomina.py |
| nomina_plantillas | payroll_templates | hr/nomina.py |
| gastos | expenses | expenses/gasto.py |
| banco_movimientos | bank_movements | finance/banco.py |
| auditoria_importacion | import_audit | core/auditoria_importacion.py |
| lineas_panaderia | bakery_lines | core/invoiceLine.py |
| lineas_taller | workshop_lines | core/invoiceLine.py |
| facturas_temp | invoices_temp | core/facturacion.py |
| modulos_modulo | modules | core/modulo.py |
| modulos_empresamodulo | company_modules | core/modulo.py |
| modulos_moduloasignado | assigned_modules | core/modulo.py |
| usuarios_usuariorolempresa | user_company_roles | empresa/usuario_rolempresa.py |
| usuarios_usuarioempresa | user_companies | empresa/usuarioempresa.py |
| core_configuracionempresa | company_settings | empresa/settings.py |
| core_configuracioninventarioempresa | company_inventory_settings | empresa/settings.py |
| core_rolempresa | company_roles | empresa/rolempresas.py |
| core_tipoempresa | company_types | empresa/empresa.py |
| core_tiponegocio | business_types | empresa/empresa.py |
| core_moneda | currencies_legacy | empresa/empresa.py |

## Cambios de Columnas (Generales)

| Español | Inglés |
|---------|--------|
| codigo | code |
| nombre | name |
| nombre_comercial | trade_name |
| telefono | phone |
| email | email |
| web | website |
| activo | is_active |
| fecha | date |
| estado | status |
| numero | number |
| proveedor_id | supplier_id |
| cliente_id | customer_id |
| subtotal | subtotal |
| impuestos | taxes |
| total | total |
| rendimiento | yield |
| costo_total | total_cost |
| costo_por_unidad | unit_cost |
| tiempo_preparacion | preparation_time |
| instrucciones | instructions |

## Status de Ejecución

### ✅ Completado
1. Modelos Python en inglés (`/app/models/`)
2. Scripts SQL de renombre completados:
   - `2025-11-17_001_spanish_to_english_names/up.sql` ✅
   - `2025-11-17_800_rolempresas_to_english/up.sql` ✅
3. Tablas base creadas en `2025-11-01_000_baseline_modern/up.sql` ✅
4. Todas las migraciones de funcionalidad (28 scripts) ✅

### 🔄 Por Hacer

**Paso 1: Ejecutar Migraciones**
```bash
cd c:\Users\pc_cashabamba\Documents\GitHub\proyecto
python ops/scripts/migrate_all_migrations.py --database-url "postgresql://postgres:root@localhost:5432/gestiqclouddb_dev"
```

**Paso 2: Validar Esquema**
```bash
psql -h localhost -d gestiqclouddb_dev -c "\dt"
```

**Paso 3: Actualizar Código Python**
- [ ] `/app/schemas/` - Pydantic models (columnas renombradas)
- [ ] `/app/services/` - Queries SQL
- [ ] `/app/routers/` - Endpoints API

**Paso 4: Ejecutar Tests**
```bash
pytest tests/ -v
```

**Paso 5: Validar Integridad**
```bash
psql -h localhost -d gestiqclouddb_dev -c "\d suppliers"
psql -h localhost -d gestiqclouddb_dev -c "\d purchases"
psql -h localhost -d gestiqclouddb_dev -c "\d expenses"
```
