# Quick Start: Remediación de Duplicación

**Tiempo total estimado**: 29 horas en 4 semanas  
**Inicio recomendado**: Ahora mismo con #1

---

## 🚀 COMENZAR HOY: ISSUE #1 (3 horas)

### Paso 1: Crear archivo compartido (30 minutos)

```bash
# Ubicación
apps/packages/api-types/src/validators/countryValidators.ts

# Copiar contenido de CODIGOS_READY_TO_IMPLEMENT.md sección "#CRÍTICA #1"
# ~400 líneas incluyen:
# - validateEcuadorRUC() con check digit
# - validateSpainNIF() con check letter
# - validateArgentinaCUIT() completo
# - Tests
```

**Verificar que compila**:
```bash
cd apps/packages/api-types
npm run typecheck
```

### Paso 2: Remover duplicación en Frontend (30 minutos)

```bash
# Archivo: apps/tenant/src/modules/importador/utils/countryValidators.ts

# Remover toda la implementación local, reemplazar con:
export { 
    validateTaxID,
    validateEcuadorRUC,
    validateSpainNIF,
    validateArgentinaCUIT,
    ValidationResult
} from "@api-types/validators/countryValidators";
```

**Validar que los imports siguen funcionando**:
```bash
cd apps/tenant
npm run typecheck
```

### Paso 3: Validar Backend es idéntico (1 hora)

```bash
# Archivo: apps/backend/app/modules/imports/validators/country_validators.py

# Comparar función Python _calculate_ruc_check_digit() 
# Debe producir EXACTAMENTE los mismos resultados que TypeScript

# Agregar test de validación cruzada
# apps/backend/tests/test_validators_sync.py

def test_ruc_validation_sync():
    """Verifica que validadores TS y Python son idénticos"""
    valid_rucs = ["1790084103004", "0992123456001"]
    invalid_rucs = ["9999999999999", "1799999999999"]
    
    for ruc in valid_rucs:
        is_valid, _ = validate_ecuador_ruc(ruc)
        assert is_valid, f"RUC {ruc} debe ser válido"
    
    for ruc in invalid_rucs:
        is_valid, _ = validate_ecuador_ruc(ruc)
        assert not is_valid, f"RUC {ruc} debe ser inválido"
```

**Correr tests**:
```bash
cd apps/backend
pytest tests/test_validators_sync.py -v
```

### Paso 4: QA Manual (30 minutos)

**Entidad**: Abrir formulario de importación

```
# Test Case 1: RUC válido
Input: 1790084103004
Expected: ✓ Aceptado
Resultado: [ ] PASS [ ] FAIL

# Test Case 2: RUC con provincia inválida
Input: 1999999999999 (provincia 99)
Expected: ✗ Rechazado
Resultado: [ ] PASS [ ] FAIL

# Test Case 3: RUC con check digit inválido
Input: 1799999999999
Expected: ✗ Rechazado
Resultado: [ ] PASS [ ] FAIL

# Test Case 4: España NIF válido
Input: 12345678Z
Expected: ✓ Aceptado
Resultado: [ ] PASS [ ] FAIL
```

### Paso 5: Commit y PR (30 minutos)

```bash
git checkout -b feature/tax-validators-shared
git add apps/packages/api-types/src/validators/
git add apps/tenant/src/modules/importador/utils/countryValidators.ts
git add apps/backend/tests/test_validators_sync.py
git commit -m "refactor: Centralizar validadores de Tax ID en package compartido

- Crear @api-types/validators/countryValidators.ts con lógica completa
- Incluir validación de check digit para RUC Ecuador
- Incluir validación de check letter para NIF España
- Incluir algoritmo completo para CUIT Argentina
- Frontend importa desde package compartido
- Backend mantiene lógica Python idéntica
- Tests de sincronización backend/frontend

Fixes: Divergencia en validación de IDs fiscales
BREAKING: Frontend ahora rechaza RUCs inválidos (behavior change)"

git push origin feature/tax-validators-shared
```

**Crear PR con descripción**:
```markdown
# Tax ID Validators: Centralización en Package Compartido

## Problema
- Frontend validaba RUCs con regex simple
- Aceptaba RUCs inválidos (provincia 99, check digit incorrecto)
- Backend era más strict
- Divergencia causaba datos basura en importaciones

## Solución
- Crear `@api-types/validators/countryValidators.ts` como fuente única de verdad
- Implementar validación completa: check digits, provincias válidas, tipos válidos
- Frontend importa desde package compartido
- Backend mantiene lógica equivalente (tests de sincronización)

## Cambios
- ✨ Nueva: `apps/packages/api-types/src/validators/countryValidators.ts`
- 🔄 Refactored: `apps/tenant/src/modules/importador/utils/countryValidators.ts`
- ✅ Added: Tests de sincronización backend/frontend

## QA Checklist
- [ ] RUC válido es aceptado
- [ ] RUC con provincia inválida es rechazado
- [ ] RUC con check digit inválido es rechazado
- [ ] NIF España valida check letter
- [ ] CUIT Argentina valida algoritmo
- [ ] Tests pasan en CI/CD
```

---

## ⏭️ SIGUIENTE: ISSUE #2 (4 horas)

Una vez que #1 esté mergeado:

```bash
# Día siguiente (3-4 horas)

# 1. Crear app/packages/shared/src/calculations/totalsEngine.ts
#    Copiar de CODIGOS_READY_TO_IMPLEMENT.md

# 2. Remover calculateTotals() de apps/tenant/src/modules/pos/POSView.tsx
#    Importar desde @shared/calculations/totalsEngine

# 3. Validar backend usa la misma fórmula

# 4. Tests exhaustivos con casos edge (discounts, rounding)

# 5. PR
```

---

## 📅 TIMELINE RECOMENDADO

**AHORA (Hoy)**:
- [ ] Leer documentos:
  - `ANALISIS_DUPLICACION_CODIGO.md` (20 min)
  - `PLAN_REMEDIACION_DUPLICACION.md` (10 min)
  - Este archivo (10 min)

- [ ] Completar Issue #1 (3 horas)
  - [ ] Crear validator compartido
  - [ ] Frontend/Backend sincronizado
  - [ ] Tests pasando
  - [ ] PR creado

**Mañana**:
- [ ] Issue #2 (4 horas)

**Esta semana**:
- [ ] Issues #1-2 completados y mergeados

**Semana 2**:
- [ ] Issues #3-4 (UX: Payroll + Recipe preview)

**Semana 3**:
- [ ] Issues #5-7 (Consistency: Sector, User, Barcode)

**Semana 4**:
- [ ] Issues #8-10 (Docs: Normalización, Env, Company)

---

## 📊 COMANDOS ÚTILES

### Validar compilación
```bash
# Frontend
cd apps/tenant && npm run typecheck

# Admin
cd apps/admin && npm run typecheck

# Packages
cd apps/packages/api-types && npm run typecheck
cd apps/packages/shared && npm run typecheck

# Backend
cd apps/backend && python -m mypy app/
```

### Correr tests
```bash
# Frontend tests
npm run test

# Backend tests
pytest tests/ -v

# Specific test
pytest tests/test_validators_sync.py::test_ruc_validation_sync -v
```

### Ver cambios
```bash
# Mostrar qué archivos se modificaron
git diff --name-only

# Ver cambios específicos en un archivo
git diff apps/tenant/src/modules/importador/utils/countryValidators.ts
```

### Crear rama
```bash
git checkout -b feature/issue-1-tax-validators-shared
git checkout -b feature/issue-2-totals-engine
git checkout -b feature/issue-3-payroll-preview
# etc
```

---

## ⚠️ PUNTOS CLAVE

### No Olvidar
1. **Tests**: Siempre escribir tests junto con el código
2. **Sincronización**: Verificar que Backend = Frontend logic-wise
3. **Documentación**: Agregar comentarios explaining *por qué* las fórmulas son así
4. **Casos Edge**: Pensar en redondeo, descuentos complejos, valores negativos
5. **Backward Compatibility**: ¿Se rompe algo en producción?

### Evitar
- Mergear sin tests pasando
- Cambiar comportamiento sin communication (breaking changes)
- Dejar código duplicado "para después"
- Asumir que todos entienden la fórmula sin documentar

### Checklist Pre-PR
```
[ ] Código escrito y formateado
[ ] Tests agregados y pasando
[ ] typecheck/linting pasando
[ ] Código reusable documentado
[ ] PR description clara
[ ] Checklist de QA incluido
[ ] No hay console.log() o TODOs pendientes
```

---

## 💬 PREGUNTAS FRECUENTES

**P: ¿Por dónde empiezo?**  
A: Issue #1 - Tax ID validators. Es el más crítico y solo toma 3 horas.

**P: ¿Qué si un test falla?**  
A: No mergear. Debug la falla, entender si es un bug real o test incorrecto.

**P: ¿Qué si descubro otra duplicación?**  
A: Agrégala a este análisis, pero enfócate en completar los 10 issues.

**P: ¿Cuánto tiempo real toma?**  
A: Las estimaciones incluyen testing. En promedio: 3-6 horas/día de desarrollo focusado.

**P: ¿Debo hacer todas las issues?**  
A: Las 2 críticas (#1-2) SÍ. El resto depende de prioridad del negocio.

---

## 🎯 SUCCESS CRITERIA

Issue está DONE cuando:

1. ✅ Código escrito (TS o Python)
2. ✅ Tests pasan (unit + integration)
3. ✅ CI/CD pasa (lint, type check, build)
4. ✅ Code review aprobado
5. ✅ Mergeado a main
6. ✅ Documentación actualizada
7. ✅ TRACKING_REMEDIACION.md actualizado

---

## 📞 SOPORTE

Si te atascas:
1. Revisar `PLAN_REMEDIACION_DUPLICACION.md` sección del issue
2. Revisar `CODIGOS_READY_TO_IMPLEMENT.md` código ejemplo
3. Revisar comentarios en código que ya existe
4. Revisar tests para entender casos de uso
5. Si aún atascado: escalate

---

## 🏁 PRIMER PASO

Ahora:

```bash
# 1. Leer sección "PASO 1" arriba

# 2. Crear archivo
touch apps/packages/api-types/src/validators/countryValidators.ts

# 3. Copiar contenido de CODIGOS_READY_TO_IMPLEMENT.md sección "CRÍTICA #1"

# 4. Verificar compilación
cd apps/packages/api-types && npm run typecheck

# ¡HECHO! Continuamos mañana con paso 2
```

**Duración**: 15-20 minutos para setup inicial  
**Próximo checkpoint**: Mañana, paso 2 (remover duplicación frontend)

