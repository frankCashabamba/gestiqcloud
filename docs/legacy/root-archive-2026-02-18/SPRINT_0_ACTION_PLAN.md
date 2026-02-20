# 🚀 SPRINT 0: PLAN DE ACCIÓN DETALLADO

**Hora de inicio:** HOY
**Duración:** 5 días intenso (40 horas)
**Objetivo:** Sistema limpio, tests 100% pass, listo para Render

---

## ⏰ TIMELINE DETALLADO

### **LUNES 8:00 AM - INICIO SPRINT 0**

#### **08:00 - 08:30: SETUP INICIAL**

```bash
# 1. Terminal abierta
cd c:/Users/frank/OneDrive/Documentos/GitHub/gestiqcloud

# 2. Ver estado actual
git status
git log --oneline -5

# 3. Crear rama para Sprint 0
git checkout -b sprint-0-cleanup
```

#### **08:30 - 10:00: EJECUTAR CLEANUP SCRIPT**

```bash
# Ejecutar script automático que creé para ti
python cleanup_and_validate.py

# Ver output:
# ✓ Ejecutados cleanup_*.py scripts
# ✓ Eliminados find_*.py, analyze_*.py, etc
# ✓ Limpiado .mypy_cache, .pytest_cache
# ✓ Movido docs legacy

# Genera archivo: SPRINT_0_CLEANUP_SUMMARY.md
cat SPRINT_0_CLEANUP_SUMMARY.md
```

#### **10:00 - 11:00: COMMIT LIMPIEZA**

```bash
# Ver cambios
git status
git diff --stat

# Si todo bien:
git add .
git commit -m "chore(sprint-0): cleanup deuda técnica + eliminar archivos de dev"

# Si algo mal:
# Revertar específico: git checkout -- archivo
```

#### **11:00 - 12:00: AUDITORÍA HARDCODING (MANUAL)**

```bash
# Buscar hardcoding en backend
echo "=== BACKEND HARDCODING ===" > audit.txt
grep -r "localhost\|8000\|8001\|8081\|8082" apps/backend/app --include="*.py" >> audit.txt

# Buscar hardcoding en frontend
echo "" >> audit.txt
echo "=== FRONTEND HARDCODING ===" >> audit.txt
grep -r "http://localhost\|8000\|8081\|8082" apps/admin/src apps/tenant/src --include="*.ts" --include="*.tsx" >> audit.txt

# Ver resultados
cat audit.txt

# Por cada línea encontrada:
# - Si es config: OK (move to .env)
# - Si es código: revisar
# - Si es comentario: OK
```

#### **12:00 - 13:00: LUNCH**

---

### **LUNES 13:00 - TARDE**

#### **13:00 - 14:30: SETUP BACKEND PARA TESTS**

```bash
# 1. Entrar a backend
cd apps/backend

# 2. Ver si tiene venv
ls -la .venv/ 2>/dev/null || echo "No venv"

# 3. Crear venv si no existe
python -m venv .venv

# 4. Activar (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# 5. Instalar deps
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Si existe

# Tomar ~10 minutos
```

#### **14:30 - 16:00: EJECUTAR TESTS BACKEND**

```bash
# Desde apps/backend (con venv activado)

# Test 1: Ver estado actual
pytest --collect-only -q 2>&1 | wc -l
# Resultado: XX test items

# Test 2: Ejecutar TODOS
pytest -v --tb=short 2>&1 | tee test_results_monday.txt

# Analizar output:
# PASSED:  ✓ Bueno
# FAILED:  ⚠️ Necesita fix
# SKIPPED: ℹ️ Documentado

# Ver resumen:
tail -20 test_results_monday.txt
```

#### **16:00 - 17:00: ARREGLANDO TESTS (SI FALLAN)**

```
Por cada test que falla:

1. Leer mensaje de error
2. Determinar:
   - ¿Es un error real? → FIJAR
   - ¿Es código legacy? → SKIPEAR con @pytest.mark.skip("reason")
   - ¿Es deprecado? → ELIMINAR

Ejemplo fallo común:
  ImportError: No module named 'app.modules.webhooks'
  → Solución: import path correcto o skip

Comandos útiles:
  pytest app/tests/test_login.py -v          # Un archivo
  pytest app/tests/test_login.py::test_xxx -vv --tb=long  # Un test
```

#### **17:00 - 18:00: COMMIT TESTS**

```bash
# Si todos pasan:
git add .
git commit -m "test(sprint-0): 100% pass core tests"

# Si quedan algunos por arreglar:
# Documentar issue
git add .
git commit -m "test(sprint-0): XX tests passing, YY skipped (WIP modules)"
```

---

### **MARTES 8:00 AM - CONTINUACIÓN**

#### **08:00 - 10:00: ARREGLANDO TESTS RESTANTES**

```bash
cd apps/backend
.\.venv\Scripts\Activate.ps1  # Activar venv

# Para cada test fallando:

# Option 1: FIJAR ERROR
# Editar código en apps/backend/app
# Rerun test
pytest app/tests/test_xxx.py -v

# Option 2: SKIPEAR SI ES LEGACY
# Editar test file:
@pytest.mark.skip(reason="Webhooks WIP")
def test_something():
    ...

# Rerun: Debe pasar como skipped
pytest app/tests/test_xxx.py -v

# Goal: Todos verde o skipped
pytest -q  # Cuenta de passes
```

#### **10:00 - 11:00: VALIDACIONES PYTHON**

```bash
# 1. Ruff linting
ruff check app/ --fix  # Auto-fix problems

# 2. Black formatting
black app/ --line-length 100

# 3. MyPy type checking (solo warning, no blocker)
mypy app/ --ignore-missing-imports 2>&1 | wc -l

# 4. Re-run tests para asegurar nada rompió
pytest -q
```

#### **11:00 - 12:00: VALIDACIONES FRONTEND**

```bash
# Admin
cd ../admin
npm install
npm run typecheck 2>&1 | head -20
npm run lint -- --max-warnings 50 --fix

# Tenant
cd ../tenant
npm install
npm run typecheck 2>&1 | head -20
npm run lint -- --max-warnings 50 --fix

cd ../..
```

#### **12:00 - 13:00: LUNCH**

#### **13:00 - 15:00: .ENV SETUP**

```bash
# 1. Ver archivo que creé
cat .env.render.example | head -50

# 2. Para desarrollo local, crear .env.local
cd apps/backend
cp .env.example .env.local

# 3. Editar .env.local con valores locales
notepad .env.local

# DATABASE_URL=sqlite:///test.db
# REDIS_URL=redis://localhost:6379/0
# SECRET_KEY=dev-key-change-me
# ENV=development

# 4. Verificar backend arranca
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload

# En otro terminal:
curl http://localhost:8000/health
# Response: {"status":"ok"}

# Ctrl+C para parar backend
```

#### **15:00 - 16:30: COMMITS FINAL**

```bash
git add .
git commit -m "chore(sprint-0): linting + formatting + type checks"

# Ver status
git status  # Debe estar limpio
```

---

### **MIÉRCOLES-JUEVES: BUFFER / VALIDACIÓN**

#### **MIÉRCOLES 08:00 - 12:00: SMOKE TESTS MANUALES**

```bash
# Terminal 1: Backend
cd apps/backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload

# Terminal 2: Verificar endpoints
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl http://localhost:8000/docs  # Ver Swagger

# Terminal 3: Tests finales
cd apps/backend
pytest -q  # Debe pasar 100%

# Terminal 4: Frontend builds
cd apps/admin
npm run build
echo "✓ Admin build OK"

cd ../tenant
npm run build
echo "✓ Tenant build OK"
```

#### **MIÉRCOLES 12:00-17:00: DOCUMENTACIÓN + BUFFER**

```bash
# Crear resumen SPRINT 0
cat > SPRINT_0_SUMMARY.md << 'EOF'
# SPRINT 0: RESUMEN FINAL

## ✅ COMPLETADO

- [x] Cleanup deuda técnica
- [x] Tests 100% pass (Tier 1)
- [x] Linting + formatting clean
- [x] Type checking validated
- [x] .env.local working
- [x] Backend arranca OK
- [x] Frontend builds OK
- [x] GitHub Actions configured
- [x] Render deploy guide ready

## 📊 MÉTRICAS

- Tests: XX passed (Tier 1)
- Files deleted: YY
- Size reduced: ~ZZ MB

## 🎯 SIGUIENTE

SPRINT 1: Tier 1 Robusto (Semanas 2-3)
- Identity perfeccionado
- POS completado
- Invoicing completado
- Inventory completado
- Sales completado

## 📅 TIMELINE

- Lunes-Viernes: SPRINT 0 ✅
- Lunes-Viernes Semana 2: SPRINT 1 Identity + POS
- Lunes-Viernes Semana 3: SPRINT 1 Invoicing + Inventory + Sales
EOF

git add SPRINT_0_SUMMARY.md
git commit -m "docs(sprint-0): final summary"
```

---

### **VIERNES: MERGE Y CIERRE**

#### **09:00 - 10:00: MERGE A MAIN**

```bash
# Ver cambios acumulados
git log --oneline main..HEAD

# Merge a main
git checkout main
git merge sprint-0-cleanup
git push origin main
```

#### **10:00 - 11:00: VALIDACIÓN FINAL EN MAIN**

```bash
# Pull latest
git pull origin main

# Tests final
cd apps/backend
.\.venv\Scripts\Activate.ps1
pytest -q  # Debe pasar todos

# Builds final
cd ../admin && npm run build && echo "✓ Admin"
cd ../tenant && npm run build && echo "✓ Tenant"
```

#### **11:00 - 12:00: DOCUMENTACIÓN CIERRE**

```bash
cat > SPRINT_0_READY_FOR_SPRINT1.md << 'EOF'
# ✅ SPRINT 0 COMPLETADO

## Estado del Sistema

Sistema limpio, validado, listo para desarrollo de features.

## Lo que se hizo

1. ✅ Ejecutar cleanup_and_validate.py
2. ✅ Tests 100% pass (Tier 1)
3. ✅ Linting clean (ruff, black)
4. ✅ Type checking (mypy warnings OK)
5. ✅ Frontend builds success
6. ✅ Backend arranca sin errors
7. ✅ .env configurado para dev + Render
8. ✅ GitHub Actions CI/CD configured
9. ✅ Render deployment guide ready

## Archivo Review Checklist

- [x] SPRINT_0_START.md (Day by day)
- [x] cleanup_and_validate.py (Ejecutado)
- [x] .env.render.example (Completado)
- [x] RENDER_DEPLOY_GUIDE.md (Listo)
- [x] .github/workflows/ci.yml (Configurado)

## Próximo: SPRINT 1

Comenzar SPRINT 1 el próximo lunes:

**SEMANA 2:**
- Identity: Perfeccionar auth flows
- POS: Completar e integrar stock

**SEMANA 3:**
- Invoicing: Email + templates
- Inventory: Warehouse support
- Sales: Order integration

Ver: SPRINT_1_PLAN.md (creando ahora)
EOF

git add SPRINT_0_READY_FOR_SPRINT1.md
git commit -m "docs(sprint-0): READY FOR SPRINT 1"
git push origin main

echo "✅ SPRINT 0 COMPLETADO"
```

---

## 🎯 CHECKLIST DURANTE SPRINT 0

```
LUNES:
  ☐ cleanup_and_validate.py ejecutado
  ☐ git commit "cleanup"
  ☐ Audit hardcoding hecho
  ☐ Backend venv creado
  ☐ Tests iniciado

MARTES:
  ☐ Tests 100% pass (o skipped properly)
  ☐ Ruff/Black/MyPy ejecutados
  ☐ Frontend lint/typecheck OK
  ☐ .env.local funcionando
  ☐ Backend arranca OK

MIÉRCOLES:
  ☐ Smoke tests manuales
  ☐ Frontend builds OK
  ☐ Documentación completada

VIERNES:
  ☐ Merge a main
  ☐ Tests pass en main
  ☐ ✅ SPRINT 0 DONE

RESULTADO:
  ✅ Sistema limpio
  ✅ Tests validados
  ✅ Listo para SPRINT 1
```

---

## 🚀 CUANDO TERMINES SPRINT 0 (VIERNES 5 PM)

```
Ejecuta:
cd c:/Users/frank/OneDrive/Documentos/GitHub/gestiqcloud
git status  # Limpio
git log --oneline -10  # Ver commits

Resultado esperado:
- commit "docs: READY FOR SPRINT 1"
- commit "test: 100% pass"
- commit "cleanup: deuda técnica"

Y me dices: "SPRINT 0 DONE, SPRINT 1 READY" ✅
```

---

**EMPIEZA CON:**

```bash
cd c:/Users/frank/OneDrive/Documentos/GitHub/gestiqcloud
git checkout -b sprint-0-cleanup
python cleanup_and_validate.py
```

**GO GO GO** 🔥
