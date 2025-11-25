# Execution Checklist - Refactoring Spanish → English

Versión: 1.0
Fecha: 2025-11-25
Estimado: 75 minutos

---

## 📋 PRE-EXECUTION (5 minutos)

### Read Documentation
- [ ] COMENZAR_AQUI.md (5 min) - understand what you're doing
- [ ] Chose execution path: Rápida / Completa / Técnica

### Git Setup
```bash
cd c:\Users\pc_cashabamba\Documents\GitHub\proyecto
```

- [ ] Verify clean status: `git status` shows "working tree clean"
- [ ] Create backup branch: `git branch backup/pre-refactor`
- [ ] Commit current state: `git commit -m "Pre-refactor checkpoint"`
- [ ] Create working branch: `git checkout -b refactor/spanish-to-english`

### Environment Check
- [ ] Python 3.8+ available: `python --version`
- [ ] PowerShell open for manual commands
- [ ] Terminal/bash open for git commands
- [ ] VS Code or editor ready (for docstring cleanup)
- [ ] ~75 minutes available without interruptions

### Tests Verification
```bash
cd apps/backend
pytest tests/ -v
```
- [ ] All tests PASS before changes

### Script Verification
```bash
cd c:\Users\pc_cashabamba\Documents\GitHub\proyecto
python refactor_script.py --help
```
- [ ] Script runs without errors
- [ ] Script is readable (not corrupted)

---

## 🔍 PHASE 1: ANALYSIS (5 minutos)

### Run Analysis
```bash
python refactor_script.py --analyze
```

- [ ] Script completes without errors
- [ ] Output shows number of files needing changes
- [ ] Output shows imports, aliases, and labels to change

### Review Output
- [ ] Understand number of files affected (~60-80)
- [ ] Understand types of changes (imports, aliases, labels)
- [ ] No unexpected categories

### Save Output (Optional)
```bash
python refactor_script.py --analyze > refactor_analysis_output.txt
```
- [ ] Saved for reference if needed

---

## ⚙️ PHASE 2: AUTOMATIC CHANGES (5 minutos)

### Verify You're Ready
- [ ] All previous steps completed ✓
- [ ] You understand this is the point of no return ✓
- [ ] git status is clean ✓
- [ ] You can revert with: git reset --hard HEAD~1 ✓

### Execute Changes
```bash
python refactor_script.py --execute
```

When prompted "⚠️  This will modify files. Continue? (y/N):"
- [ ] Type: `y`
- [ ] Press: Enter

### Execution Progress
- [ ] Script starts updating files...
- [ ] Sees messages like "✅ app/schemas/purchases.py"
- [ ] Script completes without errors
- [ ] Final message shows number of files changed (~20-30)

### Verify Automatic Changes
```bash
python refactor_script.py --verify
```

- [ ] Script completes
- [ ] If "No remaining old patterns found!" → ✅ SUCCESS
- [ ] If "Found X files with remaining old patterns" → Continue to manual fixes

### Commit Automatic Changes
```bash
git add -A
git commit -m "refactor: automatic imports/aliases update"
```

- [ ] Commit succeeds
- [ ] Shows files changed (~20-30)

---

## 🔧 PHASE 3: MANUAL DIRECTORY RENAMES (15 minutos)

### Prepare PowerShell
```powershell
cd c:\Users\pc_cashabamba\Documents\GitHub\proyecto\apps\backend\app\modules
ls
```

- [ ] Verify current directory is `...app/modules`
- [ ] Verify you can see directories: proveedores, gastos, empresa, usuarios, etc.

### Rename Modules
```powershell
# One by one or all at once
Rename-Item "proveedores" "suppliers"
Rename-Item "gastos" "expenses"
Rename-Item "empresa" "company"
Rename-Item "usuarios" "users"

# Verify
ls | grep -E "suppliers|expenses|company|users|hr"
```

- [ ] "proveedores" → "suppliers" ✓
- [ ] "gastos" → "expenses" ✓
- [ ] "empresa" → "company" ✓
- [ ] "usuarios" → "users" ✓
- [ ] "rrhh" → Verify if consolidation needed with "hr" in models

### Check if hr/rrhh needs consolidation
```bash
# If both exist, check what's different
ls -la modules/hr/
ls -la modules/rrhh/ (if exists)
```

- [ ] Understand HR/RRHH structure
- [ ] If both exist, decide consolidation plan
- [ ] Otherwise, may need manual merge

### Commit Module Renames
```bash
git add -A
git commit -m "refactor: rename modules Spanish to English"
```

- [ ] Commit succeeds
- [ ] Shows directory renames

---

## 📁 PHASE 4: SCHEMA FILE RENAMES (8 minutos)

### Prepare PowerShell
```powershell
cd c:\Users\pc_cashabamba\Documents\GitHub\proyecto\apps\backend\app\schemas
ls *.py | head -20
```

- [ ] Verify current directory is `...app/schemas`
- [ ] Can see: empresa.py, rol_empresa.py, hr_nomina.py, etc.

### Rename Schema Files
```powershell
Rename-Item "empresa.py" "company.py"
Rename-Item "rol_empresa.py" "company_role.py"
Rename-Item "hr_nomina.py" "payroll.py"
Rename-Item "configuracionempresasinicial.py" "company_initial_config.py"

# Verify
ls *.py | grep -E "company|payroll|settings"
```

- [ ] "empresa.py" → "company.py" ✓
- [ ] "rol_empresa.py" → "company_role.py" ✓
- [ ] "hr_nomina.py" → "payroll.py" ✓
- [ ] "configuracionempresasinicial.py" → "company_initial_config.py" ✓

### Check consolidation options
```powershell
# Check what's in these files
ls -l configuracion.py (if exists)
```

- [ ] Review if "configuracion.py" can be deleted/consolidated
- [ ] Document decision (keep, delete, or merge)

### Commit Schema Renames
```bash
git add -A
git commit -m "refactor: rename schema files Spanish to English"
```

- [ ] Commit succeeds
- [ ] Shows file renames

---

## 🗑️ PHASE 5: DELETE LEGACY COMPAT FILES (3 minutos)

### Verify Compat Files Status
```bash
cd apps/backend/app/models/company
ls -la empresa.py usuarioempresa.py 2>/dev/null
```

- [ ] Files exist: empresa.py, usuarioempresa.py
- [ ] These should be compat wrappers ONLY

### Verify No References (Important!)
```bash
grep -r "from app\.models\.company\.empresa\|from app\.models\.company\.usuarioempresa" ../../
```

- [ ] Result is EMPTY (no references found)
- [ ] If references found: DON'T DELETE YET, fix imports first

### Delete If Safe
```powershell
cd c:\Users\pc_cashabamba\Documents\GitHub\proyecto\apps\backend\app\models\company
Remove-Item "empresa.py"
Remove-Item "usuarioempresa.py"

# Verify deletion
ls *.py | head
```

- [ ] "empresa.py" DELETED ✓
- [ ] "usuarioempresa.py" DELETED ✓
- [ ] Other files still exist

### Commit Deletions
```bash
git add -A
git commit -m "refactor: remove legacy compat files"
```

- [ ] Commit succeeds
- [ ] Shows file deletions

---

## 🔍 PHASE 6: REVIEW CRITICAL FILES (10 minutos)

Open these files in VS Code and review:

### app/main.py
```bash
grep -n "proveedores\|gastos\|empresa\|usuarios" app/main.py
```

- [ ] Open file: `app/main.py`
- [ ] Search for old module names (proveedores, gastos, empresa, usuarios)
- [ ] If found: update to new names (suppliers, expenses, company, users)
- [ ] Save file

### app/platform/http/router.py
```bash
grep -n "proveedores\|gastos\|empresa\|usuarios" app/platform/http/router.py
```

- [ ] Open file: `app/platform/http/router.py`
- [ ] Search for route registrations with old module names
- [ ] If found: update import paths
- [ ] Save file

### app/db/base.py
```bash
grep -n "from app\.models\.company\.empresa\|from app\.modules" app/db/base.py
```

- [ ] Open file: `app/db/base.py`
- [ ] Check model imports
- [ ] Verify no imports from deleted compat files
- [ ] Save file

### app/setup.py (if exists)
```bash
ls app/setup.py 2>/dev/null && grep -n "proveedores\|gastos" app/setup.py
```

- [ ] If file exists: check for old module references
- [ ] Update if found

### Commit Critical File Updates
```bash
git add -A
git commit -m "refactor: update critical file imports"
```

- [ ] Commit succeeds
- [ ] Files updated

---

## 🧹 PHASE 7: DOCSTRING CLEANUP (15 minutos)

### Files to Clean (Docstrings/Comments in Spanish → English)

Open each file and clean Spanish docstrings/comments:

```
Files:
  - app/modules/suppliers/interface/http/tenant.py (if exists)
  - app/modules/expenses/interface/http/tenant.py (if exists)
  - app/modules/company/interface/http/tenant.py (if exists)
  - app/modules/hr/interface/http/tenant.py
  - app/schemas/company.py (recently renamed)
  - app/schemas/payroll.py (recently renamed)
  - app/models/expenses/expense.py
  - app/models/suppliers/supplier.py
  - app/models/company/company.py
  - app/models/company/company_user.py
```

### For Each File:
1. [ ] Open in VS Code
2. [ ] Find Spanish docstrings: `"""[Spanish text]"""`
3. [ ] Translate to English or replace
4. [ ] Find Spanish comments: `# [Spanish text]`
5. [ ] Translate to English
6. [ ] Save file

Example transformations:
```python
# BEFORE:
"""Módelo de Proveedor"""
# Sistema de proveedores

# AFTER:
"""Supplier Model"""
# Supplier management system
```

### Commit Docstring Changes
```bash
git add -A
git commit -m "refactor: docstrings Spanish to English"
```

- [ ] Commit succeeds
- [ ] Shows modified files (~8-10)

---

## 🧪 PHASE 8: UPDATE TESTS (10 minutos)

### Update Test Imports
```bash
grep -r "from app\.modules\.proveedores\|from app\.schemas\.empresa\|from app\.models\.company\.empresa" apps/backend/tests/
```

- [ ] Open files that contain old imports
- [ ] Update imports to new module/schema/model names
- [ ] Save files

### Update Test Docstrings
Files:
- `apps/backend/tests/test_hr_nominas.py`
- `apps/backend/tests/test_sector_config.py`
- Any other tests with Spanish docstrings

For each:
1. [ ] Open in VS Code
2. [ ] Update Spanish docstrings → English
3. [ ] Update Spanish comments → English
4. [ ] Save file

Example:
```python
# BEFORE:
def test_nomina_create_schema(self):
    """Schema de creación de nómina"""

# AFTER:
def test_payroll_create_schema(self):
    """Payroll creation schema"""
```

### Commit Test Updates
```bash
git add -A
git commit -m "refactor: update test imports and docstrings"
```

- [ ] Commit succeeds
- [ ] Shows modified test files

---

## ✅ PHASE 9: VERIFICATION (15 minutos)

### Run Verification Script
```bash
python refactor_script.py --verify
```

- [ ] Script completes
- [ ] Output shows: "No remaining old patterns found!" ✅

If NOT clean:
- [ ] Fix any remaining patterns manually
- [ ] Re-run verify script
- [ ] Repeat until clean

### Search for Residual Old Names

```bash
# Module names
grep -r "from app\.modules\.proveedores\|from app\.modules\.gastos\|from app\.modules\.empresa" apps/backend/app/
grep -r "from app\.modules\.usuarios\|from app\.modules\.rrhh" apps/backend/app/
```

- [ ] Both searches return EMPTY ✓

```bash
# Model compat files
grep -r "from app\.models\.company\.empresa\|from app\.models\.company\.usuarioempresa" apps/backend/app/
```

- [ ] Result is EMPTY ✓

```bash
# Pydantic aliases
grep -r 'alias="proveedor_id"\|alias="categoria_gasto_id"' apps/backend/app/
```

- [ ] Result is EMPTY ✓

```bash
# Spanish docstrings in code (not docs/)
grep -r '"""[^"]*[áéíóú]' apps/backend/app/ --include="*.py" | head -5
```

- [ ] Few or no results (some Spanish is OK in comments)
- [ ] No critical docstrings in Spanish

### Run Tests
```bash
cd apps/backend
pytest tests/ -v
```

- [ ] All tests PASS ✅
- [ ] No failures or errors
- [ ] No skip messages (unless expected)

### Database Check (if applicable)
```bash
# Check if migrations are needed
alembic revision --autogenerate -m "refactor: rename columns to English"
```

- [ ] Migration generated (if needed)
- [ ] Review generated migration file
- [ ] Verify column renames are correct
- [ ] If OK: `alembic upgrade head`

### Final Manual Review
- [ ] Open 3-5 random files that were changed
- [ ] Verify imports look correct
- [ ] Verify docstrings are English
- [ ] Verify no broken syntax

---

## 🎉 PHASE 10: FINAL COMMIT (3 minutos)

### Check Status
```bash
git status
```

- [ ] Shows "working tree clean" or only expected changes

### Final Commit (if needed)
```bash
git add -A
git commit -m "refactor: cleanup remaining issues"
```

- [ ] Commit succeeds (if there were remaining changes)

### Create Pull Request
```bash
git push origin refactor/spanish-to-english
```

- [ ] Push succeeds
- [ ] Branch is now on remote

### Create PR
On GitHub/GitLab:
- [ ] Go to repository
- [ ] Create PR from `refactor/spanish-to-english` to `main`
- [ ] Add description (link to this documentation)
- [ ] Request review from team lead
- [ ] Monitor CI/CD pipeline (should pass all checks)

---

## 📊 COMPLETION SUMMARY

### Before vs After

**BEFORE:**
```
- Imports: from app.modules.proveedores import ...
- Fields: alias="proveedor_id"
- Labels: "Proveedor"
- Files: empresa.py, usuarioempresa.py exist
- Docstrings: Mixed Spanish/English
```

**AFTER:**
```
- Imports: from app.modules.suppliers import ...
- Fields: supplier_id (no alias)
- Labels: "Supplier"
- Files: empresa.py, usuarioempresa.py DELETED
- Docstrings: 100% English
```

### Validation Checklist

- [ ] ✅ No Spanish module imports anywhere
- [ ] ✅ No Pydantic aliases for supplier/expense
- [ ] ✅ All docstrings in code are English
- [ ] ✅ All tests pass
- [ ] ✅ Legacy compat files deleted
- [ ] ✅ Critical files reviewed and updated
- [ ] ✅ Tests updated with correct imports
- [ ] ✅ Git history clean with logical commits

---

## 🎓 POST-EXECUTION

### Cleanup (Optional)
After PR is merged and in production:

```bash
# Delete working branch
git branch -d refactor/spanish-to-english
git push origin --delete refactor/spanish-to-english

# Delete backup branch
git branch -d backup/pre-refactor
git push origin --delete backup/pre-refactor

# Delete documentation files (if desired)
Remove-Item REFACTOR_*.md, refactor_script.py, etc.
```

- [ ] Branches cleaned up (optional)
- [ ] Documentation removed (optional - can keep for reference)

### Team Communication
- [ ] Notify team of migration
- [ ] Update any API documentation
- [ ] Update onboarding docs if they reference old names
- [ ] Update architecture diagrams if needed

### Monitoring
- [ ] Monitor logs for any issues
- [ ] Check performance (should be identical)
- [ ] Verify no broken API clients
- [ ] Follow up with frontend team if they use API

---

## ⏱️ TIME TRACKING

| Phase | Planned | Actual | Notes |
|-------|---------|--------|-------|
| Pre-Execution | 5 min | ___ min | |
| Phase 1 (Analysis) | 5 min | ___ min | |
| Phase 2 (Auto) | 5 min | ___ min | |
| Phase 3 (Renames) | 15 min | ___ min | |
| Phase 4 (Schema) | 8 min | ___ min | |
| Phase 5 (Delete) | 3 min | ___ min | |
| Phase 6 (Critical) | 10 min | ___ min | |
| Phase 7 (Docstrings) | 15 min | ___ min | |
| Phase 8 (Tests) | 10 min | ___ min | |
| Phase 9 (Verify) | 15 min | ___ min | |
| Phase 10 (Commit) | 3 min | ___ min | |
| **TOTAL** | **~75 min** | **___ min** | |

---

## 🚀 YOU'RE DONE!

Congratulations! You've successfully refactored the backend from Spanish to English.

Next steps:
1. PR review by team lead
2. Merge to main
3. Deploy to production
4. Monitor for issues
5. Celebrate! 🎉

---

**Document Version**: 1.0
**Last Updated**: 2025-11-25
**Status**: Ready to Execute
**Estimated Time**: 75 minutes
**Difficulty**: Medium
**Reversible**: Yes (git reset)
