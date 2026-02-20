# ✅ SPRINT 0: CHECKLIST DIARIO

**Use esto cada día para saber dónde estás**

---

## 📅 LUNES: LIMPIEZA

```
MAÑANA:
  [ ] Abierto terminal PowerShell
  [ ] En carpeta: c:/Users/frank/.../gestiqcloud
  [ ] Ejecuté: git checkout -b sprint-0-cleanup
  [ ] Ver: git branch (debe decir sprint-0-cleanup)

TARDE:
  [ ] Ejecuté: Remove-Item para limpiar cache
  [ ] Sin errores de "Acceso denegado"
  [ ] Ejecuté: git add . && git commit "chore(sprint-0): limpiar cache"
  [ ] Ejecuté: cd apps/backend
  [ ] Ejecuté: python -m venv .venv
  [ ] Ejecuté: .\.venv\Scripts\Activate.ps1
  [ ] Ejecuté: pip install -r requirements.txt
  [ ] Verificación: python -c "import app; print('✓')" (sin error)
  [ ] Ejecuté: pytest --collect-only -q (veo número de tests)

FIN DE LUNES:
  [ ] 1 commit en rama sprint-0-cleanup
  [ ] Backend venv listo
  [ ] Tests contados
  [ ] git status = limpio
```

**LUNES DONE? Contéstame: ✅**

---

## 🧪 MARTES: TESTS

```
MAÑANA:
  [ ] Terminal abierta en apps/backend
  [ ] .venv activado
  [ ] Ejecuté: pytest -q --tb=short
  [ ] Veo resultado (XX passed o XX failed)
  [ ] Guardé resultado en test_results_martes.txt

SI HAY FAILED:
  [ ] Para cada fallo:
      [ ] Leí el error
      [ ] Ejecuté: pytest app/tests/test_xxx.py -vv --tb=long
      [ ] Decidí: arreglar o skipear
      [ ] Editei el archivo test
      [ ] Agregué: @pytest.mark.skip(reason="...")
      [ ] Rerun test: pasó como skipped

  [ ] Después de arreglar: pytest -q pasó

LINTING:
  [ ] Ejecuté: ruff check app/ --fix
  [ ] Sin errores
  [ ] Ejecuté: black app/ --line-length 100
  [ ] Rerun tests: pytest -q pasó

FRONTEND:
  [ ] cd ../admin && npm install
  [ ] npm run typecheck (< 20 warnings)
  [ ] npm run lint --fix (0 errors)
  [ ] cd ../tenant && npm install
  [ ] npm run typecheck (< 20 warnings)
  [ ] npm run lint --fix (0 errors)

COMMIT:
  [ ] git add .
  [ ] git commit -m "test(sprint-0): XX passed + linting clean"
```

**MARTES DONE? Contéstame: Tests: XX passed, Commits: Y**

---

## 🔧 MIÉRCOLES: VALIDACIONES

```
TYPE HINTS:
  [ ] Ejecuté: mypy app/ --ignore-missing-imports
  [ ] Conté líneas: wc -l (< 100 warnings es OK)

.ENV SETUP:
  [ ] Ejecuté: cp .env.example .env.local
  [ ] Abierto notepad .env.local
  [ ] Cambié: DATABASE_URL=sqlite:///test.db
  [ ] Cambié: REDIS_URL=redis://localhost:6379/0
  [ ] Cambié: ENV=development
  [ ] Cambié: SECRET_KEY=dev-key
  [ ] Guardé (Ctrl+S)

SMOKE TESTS BACKEND:
  [ ] Ejecuté: uvicorn app.main:app --reload
  [ ] Veo: "Application startup complete"
  [ ] En OTRA terminal: curl http://localhost:8000/health
  [ ] Respuesta: {"status":"ok"}
  [ ] curl http://localhost:8000/ready
  [ ] Respuesta: {"status":"ready"}
  [ ] Abrí browser: http://localhost:8000/docs (Swagger UI cargó)
  [ ] Ctrl+C para parar backend

BUILDS:
  [ ] cd ../admin
  [ ] npm run build
  [ ] Veo: "dist built successfully" (o similar)
  [ ] ls dist/ tiene archivos
  [ ] cd ../tenant
  [ ] npm run build
  [ ] Veo: "dist built successfully"
  [ ] ls dist/ tiene archivos

COMMITS:
  [ ] git add .
  [ ] git commit -m "chore(sprint-0): .env setup + validations OK"
```

**MIÉRCOLES DONE? Contéstame: Validations OK**

---

## 📊 JUEVES: DOCUMENTACIÓN

```
CREAR RESUMEN:
  [ ] Abierto editor
  [ ] Creé: SPRINT_0_STATUS.md (desde template arriba)
  [ ] Rellené: Tests XX passed
  [ ] Rellené: Commits Y
  [ ] Rellené: Todos los checkboxes que hice

AGREGAR A GIT:
  [ ] git add SPRINT_0_STATUS.md
  [ ] git commit -m "docs(sprint-0): status report"

REVIEW:
  [ ] git log --oneline -10 (veo 5-8 commits)
  [ ] git status (limpio)
  [ ] Rama: git branch (sprint-0-cleanup)
```

**JUEVES DONE? Contéstame: Status doc creado**

---

## 🎯 VIERNES: MERGE A MAIN

```
FINAL CHECKS:
  [ ] cd apps/backend
  [ ] .\.venv\Scripts\Activate.ps1
  [ ] pytest -q (100% pass)
  [ ] cd ../admin && npm run build (OK)
  [ ] cd ../tenant && npm run build (OK)

MERGE:
  [ ] git checkout main
  [ ] git merge sprint-0-cleanup
  [ ] Sin conflictos
  [ ] git push origin main

FINAL COMMIT:
  [ ] Creé: SPRINT_0_FINAL.md
  [ ] git add SPRINT_0_FINAL.md
  [ ] git commit -m "docs(sprint-0): FINAL - ready for SPRINT 1"
  [ ] git push origin main

VERIFICACIÓN:
  [ ] git log --oneline -5 (veo merge commit)
  [ ] git branch (estoy en main)
  [ ] Rama sprint-0-cleanup puede ser eliminada (opcional)
```

**VIERNES DONE? Contéstame: ✅ SPRINT 0 COMPLETADO**

---

## 🎉 CUANDO TERMINES

```
Mensaje para mí:
"SPRINT 0 COMPLETADO ✅
- Tests: XX passed
- Commits: Y
- Linting: clean
- Builds: OK
- Ready para SPRINT 1"
```

Entonces:
- Creamos SPRINT_1_PLAN.md
- Empezamos SPRINT 1 lunes
- Tier 1 (Identity, POS, Invoicing, Inventory, Sales)

---

## 🚨 SI ATASCAS

| Problema | Solución |
|----------|----------|
| pytest falla | `pytest app/tests/test_xxx.py -vv --tb=long` |
| npm build falla | `npm run build -- --debug` |
| venv error | `Remove-Item -Recurse .venv` y crear nuevo |
| git conflict | `git status` y resolver manual |
| .env error | Verificar DATABASE_URL y REDIS_URL |
| Backend no arranca | Ver log del `uvicorn` para error |

---

**START NOW:**

```bash
cd c:/Users/frank/OneDrive/Documentos/GitHub/gestiqcloud
git checkout -b sprint-0-cleanup
```

**CHECKLIST: LUNES ✅**
