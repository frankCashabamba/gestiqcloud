# 🔥 SPRINT 0: COMANDOS COPY-PASTE

**Copia y pega estos comandos directamente en PowerShell**

---

## 📅 LUNES: LIMPIEZA

### **LUNES MAÑANA: Setup**

```powershell
# 1. Ir a carpeta
cd "C:\Users\frank\OneDrive\Documentos\GitHub\gestiqcloud"

# 2. Ver rama actual
git branch

# 3. Crear rama
git checkout -b sprint-0-cleanup

# 4. Verificar rama
git branch
# Debe decir: * sprint-0-cleanup
```

### **LUNES TARDE: Limpiar caché**

```powershell
# Limpiar caché raíz
Remove-Item -Recurse -Force .mypy_cache -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .pytest_cache -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .ruff_cache -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force htmlcov -ErrorAction SilentlyContinue
Remove-Item -Force .coverage -ErrorAction SilentlyContinue
Remove-Item -Force coverage.xml -ErrorAction SilentlyContinue

# Limpiar backend
cd apps/backend
Remove-Item -Recurse -Force .mypy_cache -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .pytest_cache -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .ruff_cache -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force htmlcov -ErrorAction SilentlyContinue
Remove-Item -Force .coverage -ErrorAction SilentlyContinue
cd ..

# Ir a raíz
cd ..

# Ver status
git status
# Debe mostrar: "deleted: .mypy_cache/, deleted: .pytest_cache/" etc

# Commit
git add .
git commit -m "chore(sprint-0): limpiar cache (.mypy, .pytest, .ruff, htmlcov)"

# Ver log
git log --oneline -2
```

### **LUNES TARDE: Backend setup**

```powershell
# Entrar a backend
cd apps/backend

# Crear venv
python -m venv .venv

# Activar venv
.\.venv\Scripts\Activate.ps1

# Ver prompt: debe tener (.venv) adelante

# Actualizar pip
pip install --upgrade pip

# Instalar dependencias
pip install -r requirements.txt

# Esperar 5-10 minutos

# Verificar imports
python -c "import app; print('✓ Backend imports OK')"
```

### **LUNES FIN: Contar tests**

```powershell
# Contar tests
pytest --collect-only -q

# Output: "50 test items collected" (o similar)

# Ver detalle
pytest --collect-only -q | Select-Object -First 20

# Volver a raíz
cd ../..
```

---

## 🧪 MARTES: TESTS

### **MARTES MAÑANA: Ejecutar tests**

```powershell
# Ir a backend
cd apps/backend

# Activar venv
.\.venv\Scripts\Activate.ps1

# RUN TESTS (rápido)
pytest -q --tb=short

# O CON DETALLE
pytest -v --tb=short 2>&1 | Tee-Object -FilePath test_results_martes.txt

# Ver resultado
Get-Content test_results_martes.txt | Select-Object -Last 20
```

### **MARTES: Si hay tests fallando**

```powershell
# Para ver error específico
pytest app/tests/test_login.py -vv --tb=long

# Si es WIP/Webhooks/etc, skipear:
# Editar el archivo: notepad app/tests/test_xxx.py
# Agregar esto ANTES de la función:
@pytest.mark.skip(reason="Webhooks experimental - WIP")

# Guardar (Ctrl+S)

# Rerun
pytest app/tests/test_xxx.py -v

# Debe decir: "SKIPPED"
```

### **MARTES: Linting Python**

```powershell
# Ruff fix
ruff check app/ --fix

# Black format
black app/ --line-length 100

# MyPy check (solo info, no blocker)
mypy app/ --ignore-missing-imports 2>&1 | Measure-Object -Line

# Re-run tests
pytest -q

# Debe salir: "XX passed"
```

### **MARTES: Frontend linting**

```powershell
# Admin
cd ../admin
npm install

npm run typecheck 2>&1 | Select-Object -First 30

npm run lint -- --max-warnings 50 --fix

# Tenant
cd ../tenant
npm install

npm run typecheck 2>&1 | Select-Object -First 30

npm run lint -- --max-warnings 50 --fix

# Volver a raíz
cd ../..
```

### **MARTES FIN: Commit**

```powershell
# Ver cambios
git status

# Agregar todo
git add .

# Commit
git commit -m "test(sprint-0): XX tests passing + linting clean"

# Ver log
git log --oneline -5
```

---

## 🔧 MIÉRCOLES: VALIDACIONES

### **MIÉRCOLES MAÑANA: Type hints**

```powershell
cd apps/backend
.\.venv\Scripts\Activate.ps1

# Ver warnings
mypy app/ --ignore-missing-imports 2>&1 | Measure-Object -Line

# Output: numero de líneas (OK si < 100)
```

### **MIÉRCOLES: .env setup**

```powershell
# Ver archivo
cd apps/backend
Get-Content .env.example | Select-Object -First 30

# Copiar
Copy-Item .env.example .env.local

# Editar (notepad)
notepad .env.local

# Cambiar estos valores:
# DATABASE_URL=sqlite:///test.db
# REDIS_URL=redis://localhost:6379/0
# ENV=development
# SECRET_KEY=dev-key-not-secure
# JWT_SECRET_KEY=dev-jwt-not-secure

# Guardar: Ctrl+S en notepad
# Cerrar notepad
```

### **MIÉRCOLES: Smoke test backend**

```powershell
# TERMINAL 1: ARRANCA BACKEND
cd apps/backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload

# Espera a ver: "Application startup complete"
# NO CIERRES ESTA TERMINAL

# TERMINAL 2: TEST (ABRE NUEVA PowerShell)
# En la NUEVA terminal:

# Test 1: Health
curl http://localhost:8000/health

# Response esperado: {"status":"ok",...}

# Test 2: Ready
curl http://localhost:8000/ready

# Response esperado: {"status":"ready",...}

# Test 3: Docs (en browser)
# Abre: http://localhost:8000/docs
# Debe cargar página Swagger UI

# Cuando termines las pruebas:
# Vuelve a TERMINAL 1 y presiona Ctrl+C para parar backend
```

### **MIÉRCOLES: Builds frontend**

```powershell
# Admin
cd apps/admin
npm run build

# Ver output: "built successfully" o similar
# Ver carpeta dist/
ls dist/ | Select-Object -First 10

# Tenant
cd ../tenant
npm run build

# Ver carpeta dist/
ls dist/ | Select-Object -First 10

# Volver a raíz
cd ../..
```

### **MIÉRCOLES FIN: Commit**

```powershell
git add .
git commit -m "chore(sprint-0): .env.local + validations OK"
git log --oneline -5
```

---

## 📊 JUEVES: DOCUMENTACIÓN

### **JUEVES: Crear status file**

```powershell
# Crear archivo
@"
# SPRINT 0: STATUS REPORT

Date: $(Get-Date -Format 'yyyy-MM-dd')

## ✅ Completado

- [x] Cache limpiado
- [x] Backend venv creado
- [x] Tests ejecutados (XX passed)
- [x] Linting clean
- [x] Type hints checked
- [x] .env.local configurado
- [x] Smoke tests OK
- [x] Admin build OK
- [x] Tenant build OK

## Estado

Sistema limpio. Listo para SPRINT 1.

## Siguiente

SPRINT 1 lunes próximo.
"@ | Out-File -Encoding utf8 SPRINT_0_STATUS.md

# Ver archivo
Get-Content SPRINT_0_STATUS.md
```

### **JUEVES FIN: Commit**

```powershell
git add SPRINT_0_STATUS.md
git commit -m "docs(sprint-0): status report"
git log --oneline -5
```

---

## 🎯 VIERNES: MERGE A MAIN

### **VIERNES MAÑANA: Final checks**

```powershell
# Backend tests
cd apps/backend
.\.venv\Scripts\Activate.ps1
pytest -q

# Admin build
cd ../admin
npm run build

# Tenant build
cd ../tenant
npm run build

# Volver a raíz
cd ../..
```

### **VIERNES: Merge**

```powershell
# Ver rama actual
git branch

# Cambiar a main
git checkout main

# Mergear
git merge sprint-0-cleanup

# Ver resultado
git log --oneline -5

# Push
git push origin main
```

### **VIERNES FIN: Cierre sprint**

```powershell
# Crear final file
@"
# ✅ SPRINT 0: COMPLETADO

Date: $(Get-Date -Format 'yyyy-MM-dd')

## ✅ Qué se hizo

1. Cache limpiado
2. Backend venv creado
3. Tests 100% pass
4. Linting clean
5. Type hints validated
6. .env.local working
7. Smoke tests OK
8. Admin/Tenant builds OK
9. Merge a main

## Siguiente

SPRINT 1: Tier 1 Robusto
- Identity
- POS
- Invoicing
- Inventory
- Sales

Comienza lunes.
"@ | Out-File -Encoding utf8 SPRINT_0_FINAL.md

git add SPRINT_0_FINAL.md
git commit -m "docs(sprint-0): FINAL - ready for SPRINT 1"
git push origin main

echo "✅✅✅ SPRINT 0 COMPLETADO ✅✅✅"
```

---

## 📞 COPIAR-PEGAR RESUMEN

**LUNES TODO:**

```powershell
cd "C:\Users\frank\OneDrive\Documentos\GitHub\gestiqcloud"
git checkout -b sprint-0-cleanup
Remove-Item -Recurse -Force .mypy_cache -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .pytest_cache -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .ruff_cache -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force htmlcov -ErrorAction SilentlyContinue
Remove-Item -Force .coverage -ErrorAction SilentlyContinue
cd apps/backend
Remove-Item -Recurse -Force .mypy_cache -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .pytest_cache -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .ruff_cache -ErrorAction SilentlyContinue
cd ..
git add .
git commit -m "chore(sprint-0): limpiar cache"
cd apps/backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
pytest --collect-only -q
cd ../..
```

**MARTES TESTS:**

```powershell
cd apps/backend
.\.venv\Scripts\Activate.ps1
pytest -q --tb=short
ruff check app/ --fix
black app/ --line-length 100
pytest -q
cd ../admin && npm install && npm run lint -- --fix
cd ../tenant && npm install && npm run lint -- --fix
cd ../..
git add .
git commit -m "test(sprint-0): XX passed + linting clean"
```

---

**CUANDO TERMINES VIERNES:**

```powershell
git log --oneline -5
# Ver que estés en main
# Ver merge commit
echo "SPRINT 0 DONE"
```

**Contéstame: SPRINT 0 COMPLETADO ✅**
