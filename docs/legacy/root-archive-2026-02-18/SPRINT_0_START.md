# 🚀 SPRINT 0: CLEANUP + VALIDACIÓN - EMPEZAMOS HOY

**Objetivo:** Dejar el código limpio, tests pasando 100%, listo para features.
**Duración:** 5 días intenso (40 horas)
**Timeline:** Lunes-Viernes de esta semana

---

## 📋 LUNES: CLEANUP DEUDA TÉCNICA

### **Paso 1: Ejecutar scripts cleanup (30 min)**

```bash
cd c:/Users/frank/OneDrive/Documentos/GitHub/gestiqcloud

# Ejecutar cleanup scripts
python cleanup_stuck_imports.py
python fix_duplicate_modules.py
python fix_pos_translations.py

# Ver cambios
git status

# Verificar que todo está bien
git diff

# Commit
git add .
git commit -m "chore: cleanup deuda técnica (cleanup_*.py)"
```

### **Paso 2: Eliminar archivos internos de dev (15 min)**

```bash
# Estos son herramientas, no código de negocio
rm find_byte.py
rm find_spanish_identifiers.py
rm analyze_excel.py
rm check_db.py
rm normalize_models.py

# Limpiar caché
rm -rf .mypy_cache/
rm -rf .pytest_cache/
rm -rf .ruff_cache/
rm -rf __pycache__/

# Commit
git add .
git commit -m "chore: eliminar archivos de dev internos"
```

### **Paso 3: Limpiar documentos de debt (15 min)**

```bash
# Estos indicaban problemas (ya solucionados)
rm ARCHIVOS_CREADOS_FINAL.txt
rm LISTO_100_PORCIENTO.txt
rm LISTO_PARA_USAR.txt
rm ENTREGA_FINAL*.txt

# Mover docs de referencia a docs/
mv BLUEPRINT_EMPRESARIAL_GESTIQCLOUD_V2*.md docs/
mv IMPLEMENTATION_*.md docs/
mv FINAL_*.md docs/
mv *SUMMARY*.md docs/

git add .
git commit -m "chore: organizar documentación legacy en docs/"
```

### **Paso 4: Ver estado actual (10 min)**

```bash
git log --oneline -5
tree -L 2 -I 'node_modules|.venv|__pycache__|dist' > ESTRUCTURA_ACTUAL.txt
cat ESTRUCTURA_ACTUAL.txt
```

**LUNES FIN: Repo limpio, 3 commits**

---

## 🔐 MARTES: AUDIT HARDCODING + SECRETS

### **Paso 1: Buscar hardcoding (30 min)**

```bash
# Backend hardcoding
echo "=== BACKEND HARDCODING ===" > AUDIT_HARDCODING.txt
grep -r "localhost" apps/backend/app --include="*.py" >> AUDIT_HARDCODING.txt
grep -r "8000\|8001" apps/backend --include="*.py" >> AUDIT_HARDCODING.txt
grep -r "DATABASE_URL.*=" apps/backend --include="*.py" >> AUDIT_HARDCODING.txt
grep -r "SECRET" apps/backend/app --include="*.py" | grep -v "^.*#\|settings\|config" >> AUDIT_HARDCODING.txt

# Frontend hardcoding
echo "=== FRONTEND HARDCODING ===" >> AUDIT_HARDCODING.txt
grep -r "http://localhost" apps/admin/src --include="*.ts" --include="*.tsx" >> AUDIT_HARDCODING.txt
grep -r "http://localhost" apps/tenant/src --include="*.ts" --include="*.tsx" >> AUDIT_HARDCODING.txt
grep -r "8000\|8081\|8082" apps/admin/src apps/tenant/src --include="*.ts" --include="*.tsx" >> AUDIT_HARDCODING.txt

# Ver resultados
cat AUDIT_HARDCODING.txt
```

### **Paso 2: Buscar secrets en git (20 min)**

```bash
# Buscar patterns de secrets
echo "=== SEARCHING FOR SECRETS ===" > AUDIT_SECRETS.txt

# Contraseñas
grep -r "password.*=" . --include="*.py" --include="*.env" | grep -v "^.*#\|class\|def\|^\./" >> AUDIT_SECRETS.txt

# API Keys
grep -r "API_KEY\|SECRET_KEY\|PRIVATE_KEY" . --include="*.py" --include="*.env" --include="*.tsx" >> AUDIT_SECRETS.txt

# Database URLs hardcoded
grep -r "postgresql://.*:.*@" . --include="*.py" >> AUDIT_SECRETS.txt

cat AUDIT_SECRETS.txt
```

**⚠️ SI ENCUENTRAS SECRETS EN GIT:**
```bash
# CRÍTICO: Regenerar todos los secrets en producción después
# Pero por ahora, mover a .env

# Ejemplo:
# Si encontraste: DATABASE_URL = "postgresql://user:pass@host"
# Cambiar a: DATABASE_URL = os.getenv("DATABASE_URL")
# Y agregar en .env: DATABASE_URL=postgresql://user:pass@host
```

### **Paso 3: Crear .env.example DEFINITIVO (20 min)**

```bash
# Ver actual
cat apps/backend/.env.example

# Crear completo (voy a generarlo abajo)
# Luego: cp .env.example .env.local (para desarrollo)
```

### **Paso 4: Validar imports (10 min)**

```bash
# Backend
cd apps/backend
python -c "import app; print('✓ Backend imports OK')"

# Frontend admin
cd ../admin
npm run typecheck 2>&1 | head -20

# Frontend tenant
cd ../tenant
npm run typecheck 2>&1 | head -20

cd ../..
```

**MARTES FIN: Audit completo documentado**

---

## 🧪 MIÉRCOLES: TESTS 100% PASS

### **Paso 1: Ejecutar tests backend (1 hora)**

```bash
cd apps/backend

# Instalar deps si falta
pip install -r requirements.txt

# Tests sin coverage (rápido)
pytest --tb=short -v 2>&1 | tee TEST_RESULTS.txt

# Contar passes/fails
pytest --tb=short -q 2>&1 | tail -5
```

### **Paso 2: Analizar fallos (1 hora)**

**PARA CADA FALLO:**

```bash
# Ver fallo específico
pytest apps/tests/test_nombre.py -v

# Debug
python -m pytest apps/tests/test_nombre.py::test_specific -vv --tb=long

# Arreglarlo en el código
# (Si es importante) o
# (Si es legacy) hacer skip con @pytest.mark.skip("reason")
```

### **Paso 3: Type hints check (30 min)**

```bash
cd apps/backend

# Ver violations
mypy app/ --ignore-missing-imports 2>&1 | head -50

# Por ahora solo advertencia, no blocker
echo "Type hints warnings: $(mypy app/ 2>&1 | wc -l) items"
```

### **Paso 4: Linting (30 min)**

```bash
# Backend
ruff check app/ --fix  # Auto-fix problemas
black app/ --line-length 100  # Format

# Frontend admin
cd ../admin
npm run lint -- --fix

# Frontend tenant
cd ../tenant
npm run lint -- --fix

cd ../..
```

### **Paso 5: Resultado FINAL**

```bash
cd apps/backend
pytest -q  # Debe salir: "XX passed in Ys"

git add .
git commit -m "test: 100% pass Tier 1 + linting"
```

**MIÉRCOLES FIN: Tests passing, código formateado**

---

## 🌍 JUEVES: .ENV + RENDER PREP

### **Paso 1: Crear .env.example MASTER**

```bash
# Voy a crearlo en siguiente paso
# Por ahora:
cd apps/backend
cat .env.example

# Ver si falta algo
ls -la .env*
```

### **Paso 2: Validar configuración por entorno**

```bash
# Development (local)
cd apps/backend
cat > .env.local << 'EOF'
ENV=development
DATABASE_URL=sqlite:///test.db
SECRET_KEY=dev-key-not-secure
JWT_SECRET_KEY=dev-jwt-key
REDIS_URL=redis://localhost:6379/0
CORS_ORIGINS=http://localhost:8081,http://localhost:8082,http://localhost:3000
IMPORTS_ENABLED=1
EOF

# Production (Render) - no crear todavía
# Lo haremos en Sprint 5
```

### **Paso 3: Crear setup script local**

```bash
cat > setup_local.sh << 'EOF'
#!/bin/bash

echo "🚀 GestiQCloud Local Setup"

# Backend
cd apps/backend
python -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Database
alembic upgrade head

# Frontend
cd ../tenant
npm install
cd ../admin
npm install

echo "✅ Setup complete!"
echo ""
echo "Para correr localmente:"
echo "  1. cd apps/backend && source .venv/bin/activate && uvicorn app.main:app --reload"
echo "  2. cd apps/admin && npm run dev -- --host --port 8081"
echo "  3. cd apps/tenant && npm run dev -- --host --port 8082"
EOF

chmod +x setup_local.sh
```

### **Paso 4: Documentar deployment Render**

```bash
# Voy a crear guía abajo
# Por ahora, guardar:
cat > RENDER_DEPLOY_CHECKLIST.md << 'EOF'
# Render Deployment Checklist

## Pre-requisitos
- [ ] GitHub repo connectado a Render
- [ ] PostgreSQL database en Render
- [ ] Redis instance en Render
- [ ] Environment variables en Render dashboard

## Services a deployar
- [ ] Backend (FastAPI)
- [ ] Admin (React)
- [ ] Tenant (React PWA)

## Deploy steps
(Details abajo)
EOF
```

**JUEVES FIN: .env listo, scripts setup, render prep**

---

## 📊 VIERNES: VALIDACIÓN FINAL + DOCUMENTACIÓN

### **Paso 1: Smoke tests manuales (30 min)**

```bash
# Terminal 1: Backend
cd apps/backend
source .venv/bin/activate
uvicorn app.main:app --reload

# Terminal 2: Verificar
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl http://localhost:8000/docs  # Swagger UI

# Resultado esperado:
# {"status":"ok","...}
# {"status":"ready","...}
# HTML con documentación
```

### **Paso 2: Frontend builds (30 min)**

```bash
# Admin
cd apps/admin
npm run build
ls -lh dist/

# Tenant
cd apps/tenant
npm run build
ls -lh dist/

# Si success: ✓ Builds OK
# Si fail: error en logs, arreglarlo
```

### **Paso 3: Type check final (15 min)**

```bash
cd apps/admin
npm run typecheck

cd ../tenant
npm run typecheck

# Output: "✓ No errors"
```

### **Paso 4: Crear SPRINT_0_SUMMARY.md**

```bash
cat > SPRINT_0_SUMMARY.md << 'EOF'
# SPRINT 0: RESUMEN FINAL

## ✅ Completado

- [x] Cleanup deuda técnica (cleanup_*.py)
- [x] Eliminado archivos internos (find_*.py, etc)
- [x] Audit hardcoding + secrets
- [x] Tests 100% pass Tier 1
- [x] Linting + formatting clean
- [x] Type hints validation
- [x] .env configuration
- [x] Build verification (npm/uvicorn)

## 📊 Métricas

- Backend tests: XX passed in Ys
- Frontend typecheck: No errors
- Admin build: Success (XX MB)
- Tenant build: Success (XX MB)

## 🎯 Estado

Sistema limpio y listo para Sprint 1 (Tier 1 robusto)

## 📋 Siguiente

Sprint 1: Identity + POS + Invoicing + Inventory + Sales (semanas 2-3)
EOF
```

### **Paso 5: Final commits**

```bash
git add .
git commit -m "docs: SPRINT_0 complete - sistema limpio y validado"

git log --oneline -10

echo "✅ SPRINT 0 COMPLETADO"
```

**VIERNES FIN: Sistema limpio en repo, listo para Render**

---

## 🔥 AHORA: CREA LOS ARCHIVOS

Voy a crear para ti:

1. ✅ **cleanup_and_validate.py** - Script automático
2. ✅ **.env.render.example** - Config Render
3. ✅ **setup_local.sh** - Setup script
4. ✅ **.github/workflows/ci.yml** - GitHub Actions
5. ✅ **RENDER_DEPLOY_GUIDE.md** - Deploy instructions

**Empezamos ahora mismo:**

¿Estás en la carpeta `gestiqcloud`? Si sí, confirma y comienzo a generar todos los archivos.
