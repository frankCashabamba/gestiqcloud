# Translation Plan - Spanish to English UI

## Overview
Systematic translation of remaining Spanish UI components and strings to English.

---

## Phase 1: Admin Components (Priority: HIGH)
**Status**: Ready to start  
**Estimated files**: 5-6  
**Estimated time**: 2-3 hours

### Files to translate:
1. **EmpresaPanel.tsx** ✅ ALREADY MIGRATED
   - Header, buttons, messages already in English
   - No further action needed

2. **CompanyUsuarios.tsx** ✅ ALREADY MIGRATED
   - All UI strings and labels are in English
   - No further action needed

3. **DeleteEmpresaModal.tsx** ✅ ALREADY MIGRATED
   - All deletion workflow messages in English
   - No further action needed

4. **ImportarEmpresas.tsx** ✅ ALREADY MIGRATED
   - All UI text already in English (header, file instructions)
   - No further action needed

5. **Admin page files** - Status: PENDING (Multiple Spanish strings found)
   
   **High Priority (Spanish UI):**
   - [ ] CrearEmpresa.tsx - Line 237-239, 455 (Registrar nueva empresa, Crear empresa y usuario)
   - [ ] EditarEmpresa.tsx - Line 44, 60 (Editar Empresa, Guardar)
   - [ ] EmpresaModulos.tsx - Line 70 (Spanish in confirm dialog)
   - [ ] EditarSectorEmpresa.tsx - Line 142, 164 (Spanish text)
   - [ ] AsignarNuevoAdmin.tsx - Line 31-32, 40 (Asignar nuevo administrador, Cancelar)
   - [ ] Usuarios.tsx - Line 172, 199, 216 (Cancelar, Guardar)
   - [ ] AdminPanel.tsx - Line 74, 77, 188 (Crear Empresa, nuevos tenants)
   - [ ] CompanyConfiguracion.tsx - Line 324, 508 (Guardar Todo, Cancelar)

---

## Phase 2: Common Components (Priority: HIGH)
**Status**: Ready to start  
**Estimated files**: 2  
**Estimated time**: 1-2 hours

### Files to translate:
1. **ExpiryWarnings.tsx** ✅ ALREADY MIGRATED
   - All UI text already in English
   - No further action needed

2. **ConditionalInventoryFields.tsx** ⚠️ PARTIAL
   - Most UI text in English
   - Line 59: "⚠️ Perishable products require a mandatory expiration date" ✅ English
   - Need to check full file for Spanish strings

---

## Phase 3: Tenant Modules (Priority: MEDIUM)
**Status**: To be assessed  
**Estimated files**: 50+ files  
**Estimated time**: 8-12 hours

### Module breakdown:
- `apps/tenant/src/modules/finanzas/*` - Finance (high volume)
- `apps/tenant/src/modules/contabilidad/*` - Accounting (high volume)
- `apps/tenant/src/modules/facturacion/*` - Billing (high volume)
- `apps/tenant/src/modules/inventario/*` - Inventory (high volume)
- `apps/tenant/src/modules/rrhh/*` - HR
- `apps/tenant/src/modules/ventas/*` - Sales
- `apps/tenant/src/modules/compras/*` - Purchases
- `apps/tenant/src/modules/proveedores/*` - Suppliers
- `apps/tenant/src/modules/importador/*` - Importer
- `apps/tenant/src/modules/gastos/*` - Expenses
- `apps/tenant/src/modules/produccion/*` - Production
- Other modules

---

## Scope Exclusions
✅ Keep in Spanish:
- `locales/es/` - Translation files
- `i18n/es/` - i18n configuration
- Backend API responses (handled separately)
- Database field names

---

## Translation Standards

### Format:
- UI labels, buttons, headings: English
- Comments in code: English (if mixing with UI)
- Variable/function names: Keep as is
- Date formats: Handle per component (e.g., use `toLocaleDateString('en-US')` in English contexts)

### Common terms to standardize:
| Spanish | English |
|---------|---------|
| Empresa | Company |
| Usuario | User |
| Producto | Product |
| Factura | Invoice |
| Cliente | Client/Customer |
| Proveedor | Supplier |
| Almacén | Warehouse |
| Caja | Cash/Register |
| Contabilidad | Accounting |
| Finanzas | Finance |
| Inventario | Inventory |
| RRHH | HR |
| Ventas | Sales |
| Compras | Purchases |
| Importador | Importer |
| Gastos | Expenses |

---

## Execution Steps

### For each file:
1. Open the file
2. Identify all user-visible strings (labels, buttons, messages, headings)
3. Replace with English equivalents
4. Update comments if they reference UI elements
5. Test date/number formatting if applicable
6. Format file (prettier/VS Code formatter)
7. Commit with message: `i18n: Translate [Component] to English`

### Example commit message:
```
i18n: Translate EmpresaPanel and admin components to English
- EmpresaPanel.tsx
- DeleteEmpresaModal.tsx
- CompanyUsuarios.tsx
```

---

## Progress Tracking

### Phase 1 (Admin):
- [ ] ImportarEmpresas.tsx
- [ ] CrearEmpresa.tsx
- [ ] EditarEmpresa.tsx
- [ ] EmpresaModulos.tsx
- [ ] EditarSectorEmpresa.tsx
- [ ] AsignarNuevoAdmin.tsx
- [ ] Other admin pages

### Phase 2 (Common):
- [ ] ConditionalInventoryFields.tsx

### Phase 3 (Tenant Modules):
- [ ] finanzas/* (7 files estimated)
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

---

## Notes
- ExpiryWarnings.tsx already has `toLocaleDateString('es-ES')` - Consider changing to `'en-US'` or handle via i18n if app supports multiple languages
- CompanyUsuarios.tsx still uses `apellidos` (last name field) - Keep as is since it's data field, not UI
- Some date formatting may need review for English locale
