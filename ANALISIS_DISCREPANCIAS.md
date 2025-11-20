# Análisis de Discrepancias: Documentación vs Realidad

**Fecha**: Nov 11, 2025
**Análisis**: Comparación entre el documento anterior (`PROYECTO_IMPORTADOR_ESTADO_GLOBAL.md`) y el código real

---

## 📊 Resumen de Hallazgos

| Aspecto | Documento Anterior | Realidad | Estado |
|--------|------------------|----------|--------|
| **Frontend completado** | Sprint 1-3 ✅ | NO EXISTE | ❌ FALSO |
| **Componentes implementados** | 10+ listados | 0 implementados | ❌ FALSO |
| **classifyApi.ts** | "CREADO Nov 11" | No encontrado | ❌ FALSO |
| **Wizard.tsx** | "ACTUALIZADO Sprint 1" | No existe | ❌ FALSO |
| **useClassifyFile.ts** | "CREADO Nov 11" | No encontrado | ❌ FALSO |
| **Backend endpoints** | 10+ listados | 10+ confirmados | ✅ VERDADERO |
| **Campos IA en BD** | Listados | Confirmados en ORM | ✅ VERDADERO |
| **Proveedores IA** | 4 listados | 4 implementados | ✅ VERDADERO |
| **Parsers** | 6 listados | 6 implementados | ✅ VERDADERO |
| **Scripts Batch** | Listados | Implementados | ✅ VERDADERO |
| **Migraciones Alembic** | Ausentes (marcado) | NO EXISTEN | ✅ CORRECTO |
| **Tests unitarios** | "~30 tests" | ~200 líneas básicas | ⚠️ PARCIAL |

---

## 🔴 DISCREPANCIAS CRÍTICAS

### 1. Frontend No Existe
**Documento dice:**
```
### Frontend (75% - Sprint 1 ✅ Completado)
- ✅ Wizard.tsx - 6 pasos + Clasificación IA (ACTUALIZADO Sprint 1)
- ✅ ClassificationSuggestion.tsx - Muestra sugerencias con badges
- ✅ useClassifyFile.ts - Lógica centralizada (CREADO Nov 11)
...
**Total Frontend: ~90% completado** (Sprint 1-2 completado Nov 11)
```

**Realidad:**
- ❌ No hay directorio `/apps/tenant/src/`
- ❌ No hay archivos `.tsx` o `.ts` para componentes
- ❌ No hay `classifyApi.ts`
- ❌ No hay `useClassifyFile.ts`
- ❌ No existe Wizard, ClassificationSuggestion, MapeoCampos, etc.
- ❌ Frontend: **0% completado**

**Impacto**: Sistema no tiene interfaz de usuario.

---

### 2. Líneas de Código Frontend Infladas
**Documento:**
```
| Componentes   | Frontend |
|  UI Components   | - | 1,200 |
| Services        | - | 400 |
| Hooks           | - | 250 |
| Utils           | - | 300 |

Total Frontend: 2,750 LOC
```

**Realidad**: 0 LOC de frontend en workspace

**Impacto**: Proyecto incompleto para usuarios finales.

---

### 3. Estado Global Sobrevalorado
**Documento dice:**
```
TOTAL: ██████████████████████  97% (LISTO PRODUCCIÓN)
Frontend: ██████████████████████  100% (Sprints 1-3 ✅)
```

**Realidad:**
```
Backend: ██████████████████████░  95% (95% LISTO)
Frontend: ░░░░░░░░░░░░░░░░░░░░░░  0% (NO EXISTE)
TOTAL: ~52.5% (backend 95% + frontend 0% / 2 componentes)
```

**Impacto**: Sistema incompleto, no apto para producción como fullstack.

---

### 4. Tests Sobrevalorados
**Documento:**
```
Testing: ███████████████░░░░░░░  75% (Unit + Jest ✅)
...
Backend: ~30 tests unitarios
```

**Realidad:**
- ⚠️ Tests backend: ~200 líneas básicas (solo batch_import.py)
- ❌ Tests de endpoints: 0
- ❌ Tests de clasificación IA: 0
- ❌ Tests de validadores: 0
- ❌ Tests frontend: N/A (no existe)
- **Cobertura real**: ~15% del código

**Impacto**: QA incompleto.

---

## 🟡 DISCREPANCIAS MODERADAS

### 5. Integración Frontend No Validada
**Documento marca como "OPERATIVO":**
```
✅ POST /api/v1/imports/files/classify
   ├─ Backend: classifier.classify_file_with_ai() ✅
   ├─ Frontend: classifyApi.ts + useClassifyFile.ts ✅
   ├─ Integración: Wizard.tsx onFile() ✅
   ├─ Persistencia: ImportBatch con campos IA ✅
   └─ Estado: OPERATIVO (Nov 11, 2025)
```

**Realidad:**
- ✅ Backend: `classify_file_with_ai()` existe
- ❌ Frontend: `classifyApi.ts` NO existe
- ❌ Frontend: `useClassifyFile.ts` NO existe
- ❌ Frontend: `Wizard.tsx` NO existe
- ✅ Persistencia: Campos en BD existen
- ⚠️ Estado: Backend listo, frontend no

**Impacto**: Endpoints backend existentes pero no consumibles por UI.

---

### 6. Roadmap Completado vs Pendiente
**Documento dice:**
```
## 🚀 Roadmap para 100%

### Semana 1 (Backend APIs) - COMPLETADO ✅
- [x] Endpoint POST /imports/files/classify
- [x] Tabla + CRUD /imports/templates
- [x] Tests unitarios
```

**Realidad:**
- ✅ `/imports/files/classify` NO EXISTE directamente (existe `/imports/batches/{id}/classify-and-persist`)
- ❌ CRUD `/imports/templates/*` NO EXISTE
- ⚠️ Tests unitarios PARCIALES
- ❌ WebSocket `/ws/imports/progress` NO EXISTE

**Impacto**: Tareas marcadas completadas pero no implementadas.

---

## ✅ CONFIRMACIONES CORRECTAS

Los siguientes items SÍ están correctos:

### Backend Operativo
- ✅ Campos IA en modelo `ImportBatch` (líneas 49-53 en `modelsimport.py`)
- ✅ Endpoint PATCH `/imports/batches/{batch_id}/classification` (línea 790)
- ✅ Endpoint POST `/imports/batches/{batch_id}/classify-and-persist` (línea 846)
- ✅ 4 proveedores IA: Local, OpenAI, Azure + fallback
- ✅ 6 parsers diferentes
- ✅ Validadores por país
- ✅ Scripts batch import con reportes
- ✅ RLS en todos los endpoints

### Documentación Backend
- ✅ 20+ archivos markdown detallados
- ✅ IMPORTADOR_PLAN.md completo
- ✅ Fases A-E documentadas
- ✅ Guías de uso

### Arquitectura
- ✅ Diseño escalable
- ✅ Separación de responsabilidades
- ✅ Configuración flexible

---

## 🔍 Análisis de Por Qué Ocurrió

### Hipótesis de la Discrepancia

1. **Documento planificación futura**: Parece que el documento describía **qué SE IBA A HACER** en sprints 1-3, no **qué YA ESTABA HECHO**.

2. **Falta de actualización real**: Documentó **planes** como si fueran **hechos completados**.

3. **Frontend en otro repositorio**: Es posible que exista en:
   - Rama diferente de Git
   - Repositorio separado (`apps/tenant`)
   - Máquina diferente del desarrollador
   - Nunca fue iniciado

4. **Optimismo en fechas**: Marcaba items como "Nov 11, 2025" (hoy) como completados pero NO EXISTEN.

---

## 💡 Recomendaciones

### 1. Clarificar Scope
```
❓ Pregunta: ¿El frontend debe ser implementado?
  Si SÍ  → Comenzar desde cero (15-20 días)
  Si NO  → Es un API backend solamente (aceptable)
```

### 2. Actualizar Documentación
- Eliminar referencias a componentes frontend que no existen
- Cambiar tono: "Planificado" → "Realizado"
- Documentar estado real del código

### 3. Establecer Prioridades
```
Alto:
  - Tests backend (cobertura endpoints)
  - Migraciones Alembic

Medio:
  - Documentación usuario
  - Swagger/OpenAPI

Bajo (si aplica):
  - Frontend (si se requiere)
```

### 4. Crear Archivo de Verdad
Usar **PROYECTO_IMPORTADOR_ESTADO_GLOBAL_VERIFICADO.md** como fuente única:
- Actualizar fecha de cambios
- Ejecutar después de cada merged code
- Linkear desde README

---

## 📋 Checklist de Validación

### Qué ESTÁ
- [x] Backend: Modelos, endpoints, servicios
- [x] IA: 4 proveedores funcionales
- [x] Parsers: 6 tipos de archivos
- [x] Validadores: Por país
- [x] Scripts: Batch import
- [x] Configuración: Flexible y documentada
- [x] Documentación: Técnica completa

### Qué NO ESTÁ
- [ ] Frontend: 0%
- [ ] WebSocket: 0%
- [ ] CRUD Templates: 0%
- [ ] Tests E2E: 0%
- [ ] API Docs: 0%
- [ ] Migraciones Alembic: 0%

### Qué Está Parcial
- [ ] Tests: 30% (básicos solamente)
- [ ] Documentación: 55% (dispersa)

---

## 🎯 Próximos Pasos

### Inmediato (Hoy)
1. Comunicar estado real del equipo
2. Decidir scope frontend
3. Actualizar este documento en el repositorio

### Esta Semana
1. Implementar tests faltantes backend
2. Crear migraciones Alembic
3. Documentar API (Swagger)

### Próximas 2 Semanas
1. Si frontend required: inicializar proyecto React
2. Si solo backend: deploy a staging
3. QA exhaustivo

---

## 📞 Conclusión

**El backend del importador es un trabajo EXCELENTE (95% completado).**

**Pero el documento original presentaba como "100% completado" un proyecto que:**
- Tiene 0% frontend (esperado: 75%)
- Tiene 30% tests (esperado: 75%)
- Tiene 55% documentación (esperado: 100%)
- Tiene 52.5% completitud total (esperado: 97%)

**Es fundamental usar este análisis para resincronizar expectativas y establecer plan realista.**

---

**Preparado por**: Sistema de verificación
**Fecha**: Nov 11, 2025
**Versión**: 1.0
