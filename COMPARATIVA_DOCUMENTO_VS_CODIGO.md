# Comparativa: Documento Anterior vs Código Real

**Análisis**: Línea por línea de lo que dice el documento vs lo que hay en el código

---

## 📊 Tabla Comparativa Global

```
┌─────────────────────┬──────────────────────┬──────────────────────┬──────────┐
│ Componente          │ Documento Decía      │ Código Real          │ Resultado│
├─────────────────────┼──────────────────────┼──────────────────────┼──────────┤
│ Frontend            │ 100% (Sprints 1-3)   │ 0% (NO EXISTE)       │ ❌ FALSO │
│ Frontend LOC        │ 2,750                │ 0                    │ ❌ FALSO │
│ Componentes         │ 10+ implementados    │ 0 implementados      │ ❌ FALSO │
│ classifyApi.ts      │ CREADO Nov 11        │ NO ENCONTRADO        │ ❌ FALSO │
│ useClassifyFile.ts  │ CREADO Nov 11        │ NO ENCONTRADO        │ ❌ FALSO │
│ Wizard.tsx          │ ACTUALIZADO Sprint 1 │ NO EXISTE            │ ❌ FALSO │
│ Backend             │ 97% (5 Fases ✅)     │ 95% (5 Fases ✅)     │ ✅ VERDAD│
│ Endpoints           │ 10+ operativos       │ 10+ confirmados      │ ✅ VERDAD│
│ Campos IA           │ Persistidos          │ En BD líneas 49-53   │ ✅ VERDAD│
│ Proveedores IA      │ 4 implementados      │ 4 implementados      │ ✅ VERDAD│
│ Parsers             │ 6 tipos              │ 6 tipos confirmados  │ ✅ VERDAD│
│ Scripts Batch       │ 650 LOC              │ 650 LOC confirmado   │ ✅ VERDAD│
│ Tests               │ 75% (Unit + Jest)    │ 30% (básico)         │ ❌ FALSO │
│ Total estado        │ 97% (listo prod)     │ 52% (incompleto)     │ ❌ FALSO │
└─────────────────────┴──────────────────────┴──────────────────────┴──────────┘
```

---

## 🔴 SECCIONES COMPLETAMENTE FALSAS

### Sección: Frontend (75% - Sprint 1 ✅ Completado)

**Documento dice:**
```
### 🎨 FRONTEND (75% - Sprint 1 ✅ Completado)

#### Componentes (✅ 100%)
- ✅ Wizard.tsx - 6 pasos + Clasificación IA (ACTUALIZADO Sprint 1)
- ✅ ClassificationSuggestion.tsx - Muestra sugerencias con badges
- ✅ MapeoCampos.tsx - Auto-mapeo + Drag&Drop
- ✅ ProgressIndicator.tsx - Barra animada
- ✅ TemplateManager.tsx - Gestión plantillas
- ✅ PreviewPage.tsx - Vista previa lotes
- ✅ 10 componentes más

#### Features de IA (Sprint 1 ✅ NUEVO)
- ✅ Clasificación automática con IA al subir archivo
- ✅ Servicio classifyApi.ts - Consume endpoints backend
- ✅ Hook useClassifyFile.ts - Lógica centralizada
- ✅ Fallback automático a heurística si IA falla
- ✅ Badge visual "🤖 IA: Local/OpenAI/Azure"
- ✅ Persistencia en batch CON campos de clasificación
- ✅ Soporte múltiples proveedores (local/OpenAI/Azure)
```

**Realidad (verificado):**
```
❌ NO EXISTE
- ❌ Wizard.tsx - NO ENCONTRADO
- ❌ ClassificationSuggestion.tsx - NO ENCONTRADO
- ❌ MapeoCampos.tsx - NO ENCONTRADO
- ❌ ProgressIndicator.tsx - NO ENCONTRADO
- ❌ TemplateManager.tsx - NO ENCONTRADO
- ❌ PreviewPage.tsx - NO ENCONTRADO
- ❌ 0 componentes implementados

Features de IA frontend (NO EXISTEN):
- ❌ classifyApi.ts - NO ENCONTRADO
- ❌ useClassifyFile.ts - NO ENCONTRADO
- ❌ Integración Wizard - NO EXISTE
- ❌ 0% frontend IA

Búsqueda realizada:
- ❌ No hay directorio /apps/tenant/
- ❌ No hay archivos .tsx
- ❌ No hay archivos .ts de frontend
- ❌ No hay carpeta importador/
```

**Conclusión**: 100% de esta sección es **INVENTADA/PLANIFICADA, NO REAL**

---

### Sección: Estado Global 97% Listo Producción

**Documento dice:**
```
║  TOTAL:      ██████████████████████  97% (LISTO PRODUCCIÓN)   ║

**Total Frontend: ~90% completado** (Sprint 1-2 completado Nov 11)

| Frontend   | - | 1,200 |
| Services   | - | 400   |
| Hooks      | - | 250   |
| Utils      | - | 300   |
| TOTAL      | **18** | **18,400** |
```

**Realidad:**
```
Frontend LOC:     0 (vs 2,750 documentado)
Services:         400 confirmado (backend)
Hooks:            0 (vs 250 documentado)
Utils:            0 incluido en backend 700 LOC
TOTAL:            7,350 (vs 18,400 documentado)
Porcentaje real:  52% (vs 97% documentado)

Componentes reales:
- Backend: 7,350 LOC        (95%)
- Frontend: 0 LOC            (0%)
- Promedio: 3,675 LOC        (52.5%)
```

**Conclusión**: Estado global **INFLADO EN 45 PUNTOS PORCENTUALES**

---

### Sección: Sprints 1-3 Completados

**Documento dice:**
```
**Última actualización**: Nov 11, 2025 - Sprints 1-3 Completados
- ✅ Sprint 1: Clasificación IA (classifyApi.ts, useClassifyFile.ts)
- ✅ Sprint 2: Override manual, Settings UI
- ✅ Sprint 3: Telemetría, Tests, WebSocket
- ✅ Flujo completo: Upload → IA → Preview → Validación → BD
```

**Realidad:**
```
❌ Sprint 1 - Clasificación IA:
  - Backend: ✅ HECHO (clasificador + endpoints)
  - Frontend: ❌ NO (classifyApi.ts, useClassifyFile.ts NO EXISTEN)
  - Resultado: 50% completado

❌ Sprint 2 - Override manual:
  - Backend: ✅ HECHO (PATCH /batches/{id}/classification)
  - Frontend: ❌ NO (Settings UI NO EXISTE)
  - Resultado: 50% completado

❌ Sprint 3 - Telemetría + Tests + WebSocket:
  - Backend: ⚠️ PARCIAL (telemetría existe, tests NO, WebSocket NO)
  - Frontend: ❌ NO (tests frontend NO EXISTEN)
  - Resultado: 20% completado

❌ Flujo completo:
  - Backend: ✅ FUNCIONA TÉCNICAMENTE
  - Frontend: ❌ NO EXISTE (usuarios no pueden acceder)
  - Resultado: Sistema API solamente
```

**Conclusión**: Sprints **INCOMPLETOS, NO "COMPLETADOS"**

---

## 🟡 SECCIONES PARCIALMENTE CORRECTAS

### Testing: 75% vs Realidad 30%

**Documento:**
```
Testing: ███████████████░░░░░░░  75% (Unit + Jest ✅)
...
Backend: ~30 tests unitarios
Frontend: Setup listo (vitest), no hay tests aún
```

**Realidad:**
```
Backend tests:     ~200 líneas (solo batch_import.py)
Frontend tests:    0 (no existe frontend)
Endpoints tests:   0 (no encontrados)
IA tests:          0 (no encontrados)
Cobertura real:    ~15% del código

Diferencia: 75% documentado vs 30% real = -45%
```

**Por qué ocurrió**: Solo hay tests básicos de batch import, nada de endpoints ni IA.

---

### Docs: 100% vs Realidad 55%

**Documento:**
```
Docs: ██████████████████████  100% (13 secciones ✅)
...
TOTAL: 13 secciones ✅
```

**Realidad:**
```
Backend técnica:     90% completa (dispersa en 20 archivos .md)
Frontend documentación: 0% (no existe frontend)
API pública (Swagger): 0% (no existe)
Usuario:             0% (no existe)
Total docs útil:     ~55% (solo backend)

Archivos encontrados:
✅ IMPORTADOR_PLAN.md                 (maestro)
✅ FASE_D_IA_CONFIGURABLE.md          (IA)
✅ FASE_E_BATCH_IMPORT.md             (batch)
✅ FASE_C_VALIDADORES_PAISES.md       (validadores)
✅ + 16 más (mayormente fase completada)

❌ Falta: API docs, docs usuario, setup guía
```

**Por qué ocurrió**: Documentación técnica es buena pero dispersa y sin guía de usuario.

---

## ✅ SECCIONES CORRECTAS

### Backend: 97% vs 95% (Diferencia mínima)

**Documento:**
```
Backend: █████████████████████░  97% (5 Fases ✅)
```

**Realidad:**
```
Backend: ██████████████████████░  95% (5 Fases ✅)

Qué está: 7,350 LOC implementado
Qué falta:
  - Tests (cobertura endpoints)      -2%
  - Migraciones Alembic              -1%
  - API docs                         -1%
  - Algunas validaciones edge cases  -1%

Total backend: 95% operativo
```

**Conclusión**: Backend assessment es **PRECISO**

---

### Endpoints: 10+ Implementados

**Documento lista:**
```
✅ POST   /imports/batches
✅ PATCH  /imports/batches/{id}/classification
✅ POST   /imports/batches/{id}/classify-and-persist
✅ POST   /imports/files/classify
... (10+ total)
```

**Realidad (verificado en línea 790, 846, etc):**
```
✅ POST   /imports/batches                              (línea 773)
✅ PATCH  /imports/batches/{id}/classification        (línea 790)
✅ POST   /imports/batches/{id}/classify-and-persist   (línea 846)
✅ POST   /imports/batches/{id}/ingest                (línea 932)
✅ POST   /uploads/chunk/init                          (línea 136)
✅ POST   /uploads/chunk/{id}/complete                (línea 238)
✅ + 4 más (mappings/suggest, analyze-file, etc)

Total: 10+ confirmados
```

**Conclusión**: Endpoints assessment es **100% PRECISO**

---

### IA Providers: 4 Implementados

**Documento:**
```
Providers implementados:
- ✅ app/modules/imports/ai/local_provider.py
- ✅ app/modules/imports/ai/openai_provider.py
- ✅ app/modules/imports/ai/azure_provider.py
```

**Realidad:**
```
✅ base.py              (AIProvider interface)
✅ local_provider.py    (LocalAIProvider)
✅ openai_provider.py   (OpenAIProvider)
✅ azure_provider.py    (AzureProvider)
✅ cache.py             (ClassificationCache)
✅ telemetry.py         (AITelemetry)

Total: 4 proveedores + cache + telemetría
```

**Conclusión**: IA assessment es **100% PRECISO**

---

### Parsers: 6 Tipos

**Documento:**
```
Parsers registrados:
- generic_excel
- products_excel
- csv_invoices
- csv_bank
- xml_invoice
- xml_camt053_bank
```

**Realidad (líneas 19-50 classifier.py):**
```
"generic_excel": {...},
"products_excel": {...},
"csv_invoices": {...},
"csv_bank": {...},
"xml_invoice": {...},
"xml_camt053_bank": {...},

Total: 6 parsers confirmados
```

**Conclusión**: Parsers assessment es **100% PRECISO**

---

## 📈 Tabla de Precisión de Documento

| Sección | Precisión | Notas |
|---------|-----------|-------|
| Frontend | 0% | COMPLETAMENTE FALSO |
| Frontend LOC | 0% | 2,750 vs 0 |
| Tests | 40% | 75% vs 30% documentado |
| Docs | 55% | 100% vs 55% documentado |
| Total estado | 0% | 97% vs 52% real |
| Backend | 98% | 97% vs 95% muy cercano |
| Endpoints | 100% | 10+ confirmados |
| IA Providers | 100% | 4 confirmados |
| Parsers | 100% | 6 confirmados |
| **Promedio** | **37%** | **Muy impreciso** |

---

## 🎯 Por Qué Ocurrió Esta Discrepancia

### Hipótesis 1: Documento vs Planificación
El documento describe lo que **SE PLANEABA HACER** en 3 sprints, no lo que **YA ESTABA HECHO**.

**Evidencia**:
- Dice "Sprint 1: ...✅ Completado"
- Pero usa fecha "Nov 11" para items sin implementar
- Describe flujos que solo existen en backend

### Hipótesis 2: Frontend Abandonado o No Sincronizado
- Backend se completó (95%)
- Frontend nunca fue iniciado
- Documentación nunca fue actualizada

**Evidencia**:
- 0 archivos .tsx
- 0 archivos .ts frontend
- 0 directorio /apps/tenant/

### Hipótesis 3: Mezcla de Aspiración y Realidad
- Mezcló "lo que hicimos" (backend ✅)
- Con "lo que íbamos a hacer" (frontend ❌)
- Sin diferenciar claramente

**Evidencia**:
- Marca como "COMPLETADO ✅" items que no existen
- Pone porcentajes muy altos (100%, 97%)
- No menciona bloqueadores

---

## 💡 Lecciones Aprendidas

### Para Futuros Documentos
1. **Diferenciar**: Planificación vs Realizado
2. **Verificar**: Contra código, no contra planes
3. **Actualizar**: Post-merge, no un día antes de cierre
4. **Documentar**: Con ubicaciones de archivo y líneas
5. **Ser conservador**: Mejor 60% real que 100% aspiracional

### Para Este Proyecto
1. **Decidir**: ¿Se implementa frontend?
2. **Priorizar**: Tests backend si no hay frontend
3. **Comunicar**: Estado real al equipo/clientes
4. **Rebasar**: Expectativas vs realidad

---

## 📞 Recomendación Final

**Use PROYECTO_IMPORTADOR_ESTADO_GLOBAL_VERIFICADO.md como fuente de verdad.**

**No confíe en PROYECTO_IMPORTADOR_ESTADO_GLOBAL.md sin verificar contra código.**

---

**Análisis realizado**: Nov 11, 2025  
**Método**: Lectura de código + comparativa documento  
**Confianza**: Alta (verificado línea por línea)
