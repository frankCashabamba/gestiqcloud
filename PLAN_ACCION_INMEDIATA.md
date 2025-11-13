# Plan de Acción Inmediata - Post Verificación

**Fecha**: Nov 11, 2025
**Basado en**: Análisis de código real vs documentación anterior

---

## 🚨 DECISIÓN CRÍTICA #1: Frontend ¿SÍ o NO?

### Escenario A: SÍ, SE NECESITA FRONTEND
```
Timeline Total:     20-25 días
Composición:
  - Frontend dev:   12 días (React + integración)
  - Backend tests:  3 días
  - E2E tests:      2 días
  - QA/Deploy:      3 días

Costo:  2-3 personas, 1 mes sprint
Inicio: Esta semana idealmente

Items Sprint Frontend:
  1. Setup React/TypeScript (1 día)
  2. Wizard 6 pasos (5 días)
  3. Integración 4 endpoints API (3 días)
  4. Componentes reutilizables (2 días)
  5. UI/UX responsivo (1 día)
```

### Escenario B: NO, SOLO BACKEND/API
```
Timeline Total:     5-7 días
Composición:
  - Backend tests:  3 días
  - API docs:       1 día
  - Migraciones:    0.5 días
  - QA/Deploy:      2 días

Costo:  1 persona, 1 semana
Inicio: Hoy

Items:
  1. Tests de endpoints (1 día)
  2. Tests de clasificación IA (1 día)
  3. Swagger/OpenAPI (1 día)
  4. Migraciones Alembic (0.5 días)
  5. Deploy staging + UAT (2 días)
```

**⚠️ RECOMENDACIÓN**: Clarificar requirement con cliente HOY.

---

## 📋 PLAN ESCENARIO A (Con Frontend)

### Semana 1: Frontend Inicial

**Lunes**
```
🔧 Task: Setup React project
├─ Crear proyecto TypeScript
├─ Instalar dependencias (React, axios, hooks, etc)
├─ Estructura carpetas
├─ ESLint + Prettier
└─ Git setup

Time: 4 horas
Status: Should start TODAY
```

**Martes-Miércoles**
```
🛠️ Task: Wizard Component (Pasos 1-3)
├─ Paso 1: Upload file + clasificación IA
│  └─ Integrar POST /imports/batches/{id}/classify-and-persist
├─ Paso 2: Preview + mapping
│  └─ Integrar POST /imports/mappings/suggest
├─ Paso 3: Template selection
│  └─ Buscar endpoint o localizar plantillas
├─ Estilos Tailwind
└─ Tests básicos

Time: 8 horas (2 días)
Status: Core functionality
```

**Jueves-Viernes**
```
🎨 Task: Wizard Pasos 4-6 + UI Polish
├─ Paso 4: Validación visual
│  └─ POST /imports/batches/{id}/validate?country=EC
├─ Paso 5: Resumen
│  └─ Mostrar errores y stats
├─ Paso 6: Progreso importación
│  └─ Polling GET /imports/batches/{id} (sin WebSocket)
├─ Componentes reutilizables
├─ Responsive design
└─ Tests componentes

Time: 8 horas (2 días)
Status: Complete Wizard
```

### Semana 2: Integración + Tests

**Lunes-Martes**
```
🔗 Task: API Integration Completa
├─ classifyApi.ts - POST /imports/files/classify
├─ batchApi.ts - POST /imports/batches + PATCH classification
├─ mappingApi.ts - POST /imports/mappings/suggest
├─ validationApi.ts - POST /imports/validate
├─ Error handling + retry logic
├─ Loading states + spinners
└─ Toast notifications

Time: 8 horas (2 días)
Status: All endpoints integrated
```

**Miércoles-Jueves**
```
🧪 Task: Tests + QA
├─ Unit tests componentes (Jest)
├─ Integration tests API calls
├─ E2E tests (Cypress/Playwright)
├─ Responsive testing (mobile/tablet/desktop)
├─ Cross-browser testing
├─ Performance optimization
└─ Accessibility check (a11y)

Time: 6 horas (1.5 días)
Status: Full test coverage
```

**Viernes**
```
🚀 Task: Deployment + Documentation
├─ Build production
├─ Setup CI/CD pipeline
├─ Deploy a staging
├─ User documentation
├─ Training material
└─ Handoff documentation

Time: 4 horas
Status: Ready for UAT
```

**Total Semana 2**: 18 horas = 2.25 días

---

## 📋 PLAN ESCENARIO B (Solo Backend/API)

### Días 1-2: Tests Endpoints

**Día 1: Tests de Endpoints**
```
📝 Task: Crear test_imports_api.py
├─ Test POST /imports/batches
├─ Test PATCH /imports/batches/{id}/classification
├─ Test POST /imports/batches/{id}/classify-and-persist
├─ Test POST /imports/batches/{id}/ingest
├─ Test POST /imports/batches/{id}/validate
├─ Error handling (404, 422, 500)
├─ RLS validation (tenant_id)
└─ Run: pytest tests/modules/imports/test_imports_api.py

Time: 6 horas
Status: 50 tests, coverage ~70%
```

**Día 2: Tests Clasificación IA**
```
📝 Task: test_classifier_integration.py
├─ Test classify_file() heurísticas
├─ Test classify_file_with_ai() con IA
├─ Test fallback si IA falla
├─ Test con diferentes tipos archivo
├─ Test providers (local, openai, azure)
├─ Test caché (hit/miss)
├─ Test telemetría
└─ Run: pytest tests/modules/imports/test_classifier_integration.py

Time: 6 horas
Status: 30 tests, coverage ~60%
```

### Día 3: API Documentation

```
📚 Task: Swagger/OpenAPI
├─ Generar openapi.json desde FastAPI
├─ Documenten todos endpoint
├─ Ejemplos request/response
├─ Autenticación (RLS)
├─ Rate limiting info
├─ Error codes
├─ Publicar en /docs (FastAPI automático)
└─ Crear README para consumidores

Time: 3 horas
Status: API fully documented
```

### Días 4-5: Migraciones + Deploy

**Día 4: Alembic Migrations**
```
🗄️ Task: Crear migraciones
├─ alembic revision --autogenerate "Add IA classification fields"
├─ Verificar generated migration
├─ Test up/down
├─ Documentar cambios BD
├─ Create rollback guide

Time: 2 horas
Status: Migration ready
```

**Día 5: QA + Staging**
```
✅ Task: Testing + Deployment
├─ Run full test suite
├─ Deploy a staging environment
├─ Smoke tests en staging
├─ Test IA providers (local at least)
├─ Test RLS multi-tenant
├─ Performance testing
├─ Security scanning
└─ UAT handoff

Time: 6 horas
Status: Production ready
```

**Total**: 5 días de trabajo enfocado

---

## 🎯 ACCIONES PARA HOY (Nov 11, 2025)

### Morning (Antes de almuerzo)

```
1. ✅ Leer RESUMEN_VERIFICACION_RAPIDA.md (3 min)
2. ✅ Comunicar hallazgos a stakeholders (15 min)
3. ✅ DECISIÓN: Frontend sí/no (5 min)
4. ✅ Establecer prioridades (10 min)
```

### Afternoon (Después almuerzo)

**Si Frontend = SÍ**
```
1. ✅ Crear plan sprint frontend (1 hora)
2. ✅ Setup repositorio React (si new) (1 hora)
3. ✅ Primer commit: Setup base (30 min)
4. ✅ Plan backlog primeros 5 días (30 min)
```

**Si Frontend = NO**
```
1. ✅ Crear plan tests backend (1 hora)
2. ✅ Escribir primer test endpoint (1 hora)
3. ✅ Comenzar test_imports_api.py (1 hora)
4. ✅ Plan backlog primeros 5 días (30 min)
```

---

## 📊 Checklist Diario

### Semana 1 (Días 1-5)

```
[] Día 1
  [] Decisión frontend comunicada
  [] Tareas semana asignadas
  [] Desarrollo iniciado
  [] Daily standup completado

[] Día 2
  [] 30% del trabajo completado
  [] Tests escritos para 50% código
  [] Commits a main

[] Día 3
  [] 50% del trabajo completado
  [] Tests para 75% código
  [] PR reviews completados

[] Día 4
  [] 70% del trabajo completado
  [] Coverage ~70%
  [] Integración testada

[] Día 5
  [] 90%+ completado
  [] Coverage >80%
  [] Ready para Viernes
```

---

## 📞 Reunión de Status: VIERNES

**Hora**: 5pm
**Asistentes**: Tech lead, QA, PM
**Agenda**:
```
1. Estado actual (10 min)
2. Blockers identificados (5 min)
3. Ajustes plan si aplica (5 min)
4. Próximos pasos (5 min)
```

**Métricas**:
- ✅ Tests escritos: Esperado 50+ (A) / 10+ (B)
- ✅ Coverage: Esperado >60% (A) / >70% (B)
- ✅ Componentes: Esperado 3-4 (A) / N/A (B)
- ✅ Commits: Esperado 10+ (A/B)

---

## 🚀 Go-Live Criteria

### Opción A: Frontend
```
Requisitos para producción:
□ Wizard 6 pasos funcionando
□ Integración 4+ endpoints
□ 80%+ test coverage
□ Responsive mobile/tablet/desktop
□ Error handling completo
□ Documentación usuario
□ Performance <2s load time
□ Security review completada
□ UAT pasada
```

### Opción B: API Only
```
Requisitos para producción:
□ 80%+ test coverage endpoints
□ Migraciones Alembic aplicadas
□ API docs públicos (Swagger)
□ RLS validado multi-tenant
□ IA providers testeados
□ Rate limiting configured
□ Monitoring setup (logs)
□ Security review completada
□ Performance <100ms endpoints
```

---

## 💰 Estimado de Recursos

### Escenario A: Con Frontend
```
Team size:        2-3 personas
Duration:         3-4 semanas
Effort total:     150-180 hours
Cost:             $15K-25K (depends salary)

Breakdown:
  Frontend dev:   100h ($80/h = $8K)
  Backend tests:  30h  ($80/h = $2.4K)
  QA/Testing:     20h  ($70/h = $1.4K)
  PM/Docs:        10h  ($100/h = $1K)
```

### Escenario B: Solo Backend
```
Team size:        1 persona
Duration:         1 semana
Effort total:     35-40 hours
Cost:             $2.8K-3.2K

Breakdown:
  Backend tests:  20h ($80/h = $1.6K)
  API docs:       5h  ($80/h = $400)
  Migraciones:    3h  ($80/h = $240)
  QA/Deploy:      7h  ($80/h = $560)
```

**Recomendación**: Escenario B costo/beneficio.

---

## ⚡ Quick Start Commands

### Escenario A: Frontend
```bash
# Day 1
npm create vite@latest importador-ui -- --template react-ts
cd importador-ui
npm install axios react-hook-form tailwindcss @headlessui/react
git init && git add . && git commit -m "init: react setup"

# Day 2-3
touch src/pages/Wizard.tsx
touch src/services/classifyApi.ts
touch src/hooks/useClassifyFile.ts
# ... implement
```

### Escenario B: Backend
```bash
# Day 1
cd apps/backend/tests/modules/imports
touch test_imports_api.py
# ... write tests
pytest test_imports_api.py -v

# Day 3
cd apps/backend
alembic revision --autogenerate "Add IA fields"
alembic upgrade head
```

---

## 📈 Success Metrics

### Week 1 End
```
A: 50% frontend done, 40%+ test coverage
B: 100% backend tested, API docs 70% done
```

### Week 2 End
```
A: 90% frontend done, 70%+ test coverage
B: 100% backend complete, ready for production
```

### Week 3 End (A only)
```
A: 100% done, 80%+ test coverage, in staging
```

---

## 🔗 Documentos Referencia

Mantener abiertos durante desarrollo:
- **PROYECTO_IMPORTADOR_ESTADO_GLOBAL_VERIFICADO.md** - Estado real
- **COMPARATIVA_DOCUMENTO_VS_CODIGO.md** - Qué verificar
- **RESUMEN_VERIFICACION_RAPIDA.md** - Checklist rápido
- **DOCUMENTOS_VERIFICACION_README.md** - Guía documentación

---

## 💡 Tips para Éxito

1. **Comunicación**: Daily standup a las 9am
2. **Documentación**: Commit message claro + README actualizado
3. **Testing**: Escribe test ANTES de código (TDD)
4. **Git**: Small commits, frequent pushes
5. **Review**: PR review máximo 2 horas
6. **Meetings**: Reunión status solo viernes
7. **Focus**: No cambiar scope mid-sprint

---

**Plan preparado**: Nov 11, 2025
**Válido hasta**: Cambio de scope o 1 mes

Para preguntas o ajustes, contactar tech lead.
