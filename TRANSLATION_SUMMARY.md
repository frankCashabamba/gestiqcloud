# Translation Summary - Spanish to English UI

**Last Updated**: January 19, 2026  
**Scope**: Frontend UI components and strings (excluding i18n/locales)

---

## Status Overview

### ✅ Already Translated
- `EmpresaPanel.tsx` - Company management
- `CompanyUsuarios.tsx` - Company users
- `DeleteEmpresaModal.tsx` - Delete company modal
- `ImportarEmpresas.tsx` - Import companies
- `ExpiryWarnings.tsx` - Product expiry alerts
- Most tenant module labels (CajaForm uses English labels like "Date", "Type", "Concept", "Amount")

### ⚠️ Partially Translated
- `ConditionalInventoryFields.tsx` - Mixed English/Spanish (needs full review)

### ❌ Needs Translation (Admin - HIGH PRIORITY)
Priority 1 files with Spanish UI strings:

**File: CrearEmpresa.tsx**
- Line 237: "Registrar nueva empresa" → "Register new company"
- Line 239: "Completa los datos para crear una empresa..." → "Complete the data to create a company..."
- Line 455: "Crear empresa y usuario" → "Create company and user"

**File: EditarEmpresa.tsx**
- Line 44: "Editar Empresa" → "Edit Company"
- Line 60: "Guardar" → "Save"

**File: EmpresaModulos.tsx**
- Line 70: "¿Eliminar módulo de la empresa?" (Spanish confirm dialog)

**File: EditarSectorEmpresa.tsx**
- Line 142: "Se crearán nuevas categorías predefinidas" → "Predefined categories will be created"
- Line 164: "Cancelar" → "Cancel"

**File: AsignarNuevoAdmin.tsx**
- Line 31: "Asignar nuevo administrador" → "Assign new admin"
- Line 32: "Ingresa el email del usuario..." → "Enter the user email..."
- Line 40: "Cancelar" → "Cancel"

**File: Usuarios.tsx**
- Multiple Spanish strings: "Cancelar", "Nueva contraseña", "Guardar"

**File: AdminPanel.tsx**
- Line 74: "Crear Empresa" → "Create Company"
- Line 77: url with "empresas/crear"
- Line 188: "Nuevos tenants (30 días)" → "New tenants (30 days)"

**File: CompanyConfiguracion.tsx**
- Line 324: "Guardar Todo" → "Save All"
- Line 508: "Cancelar" → "Cancel"

---

## Module Analysis

### Finanzas (Finance) - Status: ✅ Mostly Compliant
Files analyzed:
- `CajaForm.tsx` - Uses English labels: "Date", "Type", "Concept", "Amount"
- `CajaList.tsx` - Component structure with Spanish field names (internal)
- `BancoList.tsx` - Similar structure
- `CierreCajaModal.tsx` - Modal component
- `SaldosView.tsx` - Dashboard view

**Finding**: UI labels already in English, field names (concepto, tipo, etc.) are internal/DB names

### Other High-Volume Modules (Inventory, HR, Sales, etc.)
**Status**: Requires detailed audit - not yet scanned

---

## Translation Checklist

### Phase 1: Admin Pages (Estimate: 2-3 hours)
- [ ] CrearEmpresa.tsx (3 strings)
- [ ] EditarEmpresa.tsx (2 strings)
- [ ] EmpresaModulos.tsx (1 string in confirm)
- [ ] EditarSectorEmpresa.tsx (2 strings)
- [ ] AsignarNuevoAdmin.tsx (3 strings)
- [ ] Usuarios.tsx (3+ strings)
- [ ] AdminPanel.tsx (3 strings)
- [ ] CompanyConfiguracion.tsx (2 strings)
- [ ] Other admin pages (TBD)

### Phase 2: Common Components (Estimate: 30 min - 1 hour)
- [ ] ConditionalInventoryFields.tsx (full review)
- [ ] Other shared tenant components (TBD)

### Phase 3: Tenant Modules (Estimate: 6-10 hours)
- [ ] finanzas/* (7 files)
- [ ] contabilidad/* (6 files estimated)
- [ ] facturacion/* (5 files estimated)
- [ ] inventario/* (8 files estimated)
- [ ] rrhh/* (5 files estimated)
- [ ] ventas/* (4 files estimated)
- [ ] compras/* (4 files estimated)
- [ ] proveedores/* (4 files estimated)
- [ ] importador/* (8 files estimated)
- [ ] gastos/* (5 files estimated)
- [ ] produccion/* (6 files estimated)
- [ ] Other modules (TBD)

---

## Key Observations

1. **Front-end layer is mostly done** - Main admin/common components are already in English
2. **Internal field names** - Keep Spanish database field names (concepto, tipo, monto) - these are NOT user-visible UI
3. **Labels vs data** - Form labels in English, field names in DB queries remain Spanish for backend compatibility
4. **Remaining work is primarily**:
   - Admin page titles and buttons
   - Tenant module screen titles and labels
   - Dialog/modal messages and confirmations
   - Error messages and validation strings

---

## Common Terms Reference

| Spanish | English |
|---------|---------|
| Crear | Create |
| Editar | Edit |
| Guardar | Save |
| Cancelar | Cancel |
| Eliminar | Delete |
| Borrar | Delete |
| Nuevo/Nueva | New |
| Empresa | Company |
| Usuario | User |
| Producto | Product |
| Factura | Invoice |
| Módulo | Module |
| Concepto | Concept/Description |
| Tipo | Type |
| Monto | Amount |
| Fecha | Date |
| Caja | Cash Register |
| Banco | Bank |
| Inventario | Inventory |
| Ingreso | Income/Inbound |
| Egreso | Expense/Outbound |

---

## Notes

- ExpiryWarnings.tsx: Uses `toLocaleDateString('es-ES')` - Consider changing to `'en-US'` if full English UI
- Date formatting needs review across all translated components
- Keep SQL queries, API responses, and database field names in original Spanish (handled separately)
- Some components mix internal field names (Spanish) with UI labels (English) - this is acceptable and correct
