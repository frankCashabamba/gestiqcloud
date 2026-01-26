# Tracking: Remediación de Duplicación Frontend/Backend

**Inicio**: 17 de Enero 2026  
**Target**: 4 semanas (29 horas)

---

## 📋 STATUS SUMMARY

| Issue | Status | PR | Ramas | % Completo |
|-------|--------|----|----|-----------|
| #1 Tax ID | ⏳ Pending | - | - | 0% |
| #2 Totals | ⏳ Pending | - | - | 0% |
| #3 Payroll | ⏳ Pending | - | - | 0% |
| #4 Recipes | ⏳ Pending | - | - | 0% |
| #5 Sector | ⏳ Pending | - | - | 0% |
| #6 User | ⏳ Pending | - | - | 0% |
| #7 Barcode | ⏳ Pending | - | - | 0% |
| #8 Data | ⏳ Pending | - | - | 0% |
| #9 Env | ⏳ Pending | - | - | 0% |
| #10 Company | ⏳ Pending | - | - | 0% |

**Global**: 0% (0/29 horas)

---

## 🔴 CRÍTICA #1: TAX ID VALIDATION

**Descripción**: Frontend acepta RUCs inválidos  
**Riesgo**: Importaciones con datos basura  
**Estimado**: 3 horas

### Checklist

- [ ] Crear `apps/packages/api-types/src/validators/countryValidators.ts`
  - [ ] `validateEcuadorRUC()` con check digit
  - [ ] `validateSpainNIF()` con check letter
  - [ ] `validateArgentinaCUIT()` con algoritmo
  - [ ] Tests en `__tests__/countryValidators.test.ts`
  
- [ ] Frontend: Usar validador compartido
  - [ ] Remover duplicación en `apps/tenant/src/modules/importador/utils/countryValidators.ts`
  - [ ] Re-exportar desde `@api-types`
  - [ ] Validar en hooks y formularios
  
- [ ] Backend: Validar código Python idéntico
  - [ ] Comparar lógica con TypeScript
  - [ ] Agregar test de sincronización
  - [ ] Documentar en README
  
- [ ] QA: Validación cross-layer
  - [ ] RUC válido en TS → válido en Python ✓
  - [ ] RUC inválido en TS → inválido en Python ✓
  - [ ] Casos edge (provincia 99, tipo 9, check digit) ✓

### Archivos a Modificar
```
✏️ NEW  apps/packages/api-types/src/validators/countryValidators.ts
✏️ MOD  apps/tenant/src/modules/importador/utils/countryValidators.ts
✏️ MOD  apps/backend/app/modules/imports/validators/country_validators.py
✏️ NEW  apps/packages/api-types/src/validators/__tests__/countryValidators.test.ts
📝 DOC  README.md (agregar nota sobre validators compartidos)
```

### Notas
- Código ready-to-implement en `CODIGOS_READY_TO_IMPLEMENT.md`
- Tests incluyen casos de RUCs válidos/inválidos

---

## 🔴 CRÍTICA #2: CÁLCULOS TOTALES

**Descripción**: Divergencia en orden de operaciones  
**Riesgo**: Discrepancias en moneda (1-3%)  
**Estimado**: 4 horas

### Checklist

- [ ] Crear engine centralizado
  - [ ] `apps/packages/shared/src/calculations/totalsEngine.ts`
  - [ ] Clase `TotalsCalculator` con fórmula documentada
  - [ ] Tests exhaustivos (4+ casos)
  - [ ] Soporte para redondeo (round/ceil/floor)
  
- [ ] Frontend: Usar engine
  - [ ] Remover `calculateTotals()` local de `POSView.tsx` (L866-906)
  - [ ] Importar desde `@shared/calculations/totalsEngine`
  - [ ] Usar en cart, preview, receipt
  - [ ] Tests: verificar totals exactos
  
- [ ] Backend: Validar al guardar
  - [ ] Endpoint de validación: `POST /pos/validate-totals`
  - [ ] Comparar cálculo frontend vs backend
  - [ ] Rechazar si divergencia > 0.01
  
- [ ] QA: Casos de uso
  - [ ] Sin descuentos (100 → 115 con 15% tax)
  - [ ] Line discount (180 × 0.15 = 27 tax)
  - [ ] Global discount (80 × 0.15 = 12 tax, NOT 15)
  - [ ] Mixed descuentos
  - [ ] Múltiples items

### Archivos a Modificar
```
✏️ NEW  apps/packages/shared/src/calculations/totalsEngine.ts
✏️ MOD  apps/tenant/src/modules/pos/POSView.tsx (L866-906)
✏️ MOD  apps/tenant/src/modules/pos/services.ts
✏️ NEW  apps/backend/app/modules/pos/application/calculate.py
✏️ NEW  apps/packages/shared/src/calculations/__tests__/totals.test.ts
```

### Notas
- Código ready-to-implement en `CODIGOS_READY_TO_IMPLEMENT.md`
- Orden de operaciones está documentada en engine

---

## 🟡 MEDIA #3: PAYROLL PREVIEW

**Descripción**: Sin cálculo local, usuario debe guardar para ver resultado  
**Riesgo**: Mala UX  
**Estimado**: 6 horas

### Checklist

- [ ] Crear engine de nómina
  - [ ] `apps/packages/shared/src/calculations/payrollEngine.ts`
  - [ ] Funciones por país (ES, EC, AR, PE)
  - [ ] Tramos progresivos IRPF
  - [ ] Tests por país
  
- [ ] Frontend: Hook para preview
  - [ ] `apps/tenant/src/modules/rrhh/hooks/usePayrollCalculator.ts`
  - [ ] Usa `calculatePayroll()` en tiempo real
  - [ ] Componente `PayrollPreview` muestra resultado
  - [ ] Integrar en formulario de nómina
  
- [ ] QA: Validación por país
  - [ ] ES: 6.35% social + IRPF tramos
  - [ ] EC: 9.45% aporte
  - [ ] Deducciones (spouse, dependents)

### Archivos a Modificar
```
✏️ NEW  apps/packages/shared/src/calculations/payrollEngine.ts
✏️ NEW  apps/tenant/src/modules/rrhh/hooks/usePayrollCalculator.ts
✏️ NEW  apps/tenant/src/modules/rrhh/components/PayrollPreview.tsx
✏️ MOD  apps/tenant/src/modules/rrhh/pages/NominaForm.tsx
```

---

## 🟡 MEDIA #4: RECIPE COSTS PREVIEW

**Descripción**: Sin preview, usuario no ve costo hasta guardar  
**Riesgo**: Mala UX  
**Estimado**: 5 horas

### Checklist

- [ ] Crear engine de costos
  - [ ] `apps/packages/shared/src/calculations/recipeEngine.ts`
  - [ ] `calculateRecipeCost()` con ingredientes
  - [ ] Desglose: ingredientes + labor + overhead
  
- [ ] Frontend: Hook para preview
  - [ ] `apps/tenant/src/modules/productos/hooks/useRecipeCostCalculator.ts`
  - [ ] Componente `RecipeCostPreview`
  - [ ] Mostrar margen/rentabilidad
  
- [ ] Integración en formularios

### Archivos a Modificar
```
✏️ NEW  apps/packages/shared/src/calculations/recipeEngine.ts
✏️ NEW  apps/tenant/src/modules/productos/hooks/useRecipeCostCalculator.ts
✏️ NEW  apps/tenant/src/modules/productos/components/RecipeCostPreview.tsx
✏️ MOD  apps/tenant/src/modules/productos/Form.tsx
```

---

## 🟡 MEDIA #5: SECTOR VALIDATION SYNC

**Descripción**: Reglas DB pueden desincronizarse  
**Riesgo**: Validación inconsistente  
**Estimado**: 2 horas

### Checklist

- [ ] Agregar versionado en BD
  - [ ] Columna `rules_version` en tabla de reglas
  - [ ] Timestamp de última actualización
  
- [ ] Frontend: Cache con invalidación
  - [ ] Guardar version en localStorage
  - [ ] Comparar con server en cada load
  - [ ] Invalidar si versión server > local
  
- [ ] Tests: Sincronización

### Archivos a Modificar
```
✏️ NEW  ops/migrations/xxx_add_rules_version.sql
✏️ MOD  apps/tenant/src/hooks/useSectorValidation.ts
✏️ MOD  apps/tenant/src/services/sectorValidationRules.ts
```

---

## 🟡 MEDIA #6: USER UNIQUENESS VALIDATION

**Descripción**: Sin validación local, usuario espera respuesta del server  
**Riesgo**: Mala UX  
**Estimado**: 3 horas

### Checklist

- [ ] Backend: Crear endpoints de validación
  - [ ] `POST /users/check-email` → `{exists: boolean}`
  - [ ] `POST /users/check-username` → `{exists: boolean}`
  
- [ ] Frontend: Hooks con debounce
  - [ ] `useEmailExists(email)` - debounce 500ms
  - [ ] `useUsernameExists(username)` - debounce 500ms
  - [ ] Mostrar error mientras usuario escribe
  
- [ ] UI: Feedback instantáneo
  - [ ] Campo con icono ✓ cuando no existe
  - [ ] Campo con icono ✗ cuando existe

### Archivos a Modificar
```
✏️ NEW  apps/backend/app/modules/users/interface/http/validators.py
✏️ NEW  apps/tenant/src/hooks/useEmailExists.ts
✏️ NEW  apps/tenant/src/hooks/useUsernameExists.ts
✏️ MOD  apps/tenant/src/modules/usuarios/Form.tsx
```

---

## 🟡 MEDIA #7: BARCODE VALIDATION (Backend)

**Descripción**: Backend no valida checksums  
**Riesgo**: Barcodes inválidos se guardan  
**Estimado**: 2 horas

### Checklist

- [ ] Backend: Validación de barcode
  - [ ] Importar lógica de `barcodeGenerator.ts`
  - [ ] Validar en endpoint de importación
  - [ ] Rechazar barcodes inválidos
  
- [ ] Endpoint: `POST /products/validate-barcode`
  - [ ] Input: `barcode, format`
  - [ ] Output: `{valid: bool, error?: string}`

### Archivos a Modificar
```
✏️ NEW  apps/backend/app/modules/products/application/barcode_validator.py
✏️ NEW  apps/backend/app/modules/products/interface/http/validators.py
✏️ MOD  apps/backend/app/modules/imports/validators_impl.py
```

---

## 🟢 BAJA #8: DATA NORMALIZATION

**Descripción**: Documentar flujo  
**Riesgo**: Bajo  
**Estimado**: 1 hora

### Checklist

- [ ] Documentar en README
  - [ ] Flujo: Frontend normaliza → Backend valida
  - [ ] Sin duplicación, separación clara
  - [ ] Archivos involucrados

### Archivos a Modificar
```
📝 MOD  docs/NORMALIZATION_FLOW.md (nuevo)
```

---

## 🟢 BAJA #9: ENV VALIDATION

**Descripción**: Sin sincronización expectations  
**Riesgo**: Bajo  
**Estimado**: 1 hora

### Checklist

- [ ] Sincronizar schemas
  - [ ] `tsconfig.base.json` vs `settings.py`
  - [ ] Documentar vars compartidas

### Archivos a Modificar
```
📝 MOD  docs/ENV_VARS.md (nuevo)
```

---

## 🟢 BAJA #10: COMPANY VALIDATION

**Descripción**: Diferentes niveles de validación  
**Riesgo**: Bajo  
**Estimado**: 2 horas

### Checklist

- [ ] Sincronizar validación
  - [ ] Frontend debe ser al menos igual a backend
  - [ ] Usar validadores compartidos (Tax ID)

### Archivos a Modificar
```
✏️ MOD  apps/admin/src/pages/CrearEmpresa.tsx
✏️ MOD  apps/backend/app/modules/tenants/validators.py
```

---

## 📊 WEEKLY BREAKDOWN

### Semana 1: Críticos
```
Lunes:    #1 Tax ID - 3h
Martes:   #2 Totals - 4h
Miércoles: Testing + Docs
Total:    7h
```

### Semana 2: UX Improvements
```
Lunes:    #3 Payroll - 6h
Martes:   #4 Recipes - 5h
Total:    11h
```

### Semana 3: Consistency
```
Lunes:    #5 Sector - 2h
Martes:   #6 User - 3h
Miércoles: #7 Barcode - 2h
Total:    7h
```

### Semana 4: Documentation
```
Lunes:    #8 Data - 1h
Martes:   #9 Env - 1h
Miércoles: #10 Company - 2h
Total:    4h
```

---

## 🔗 REFERENCIAS

- **Análisis completo**: `ANALISIS_DUPLICACION_CODIGO.md`
- **Plan detallado**: `PLAN_REMEDIACION_DUPLICACION.md`
- **Código ready**: `CODIGOS_READY_TO_IMPLEMENT.md`
- **Este tracking**: `TRACKING_REMEDIACION.md`

---

## ✅ DEFINICIÓN DE DONE

Para cada issue:
1. Código escrito y testeado localmente
2. PR creado con descripción clara
3. Tests pasan en CI/CD
4. Code review aprobado
5. Merged a main
6. Documentación actualizada
7. Ticket marcado como completo

