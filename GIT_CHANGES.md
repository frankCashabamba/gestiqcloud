# Git Changes - Archivos a Sincronizar

## 📝 Archivos Modificados / Modified Files (para git add)

### 1. Model Definition
```
apps/backend/app/models/core/invoiceLine.py
```
**Cambio / Change:** Agregada clase POSLine (líneas 68-80)

### 2. Error Handling
```
apps/backend/app/modules/pos/application/invoice_integration.py
```
**Cambio / Change:** Mejorado manejo de excepciones en rollback

### 3. i18n English
```
apps/backend/app/i18n/locales/en.json
```
**Cambio / Change:** Agregadas claves de traducción para invoice y invoicing

### 4. i18n Spanish
```
apps/backend/app/i18n/locales/es.json
```
**Cambio / Change:** Agregadas claves de traducción para invoice e invoicing

## 📁 Archivos Nuevos / New Files (para git add)

### 5. Database Migration - Up
```
ops/migrations/2026-01-22_001_add_pos_invoice_lines/up.sql
```
**Contenido / Content:** Script SQL para crear tabla pos_invoice_lines

### 6. Database Migration - Down
```
ops/migrations/2026-01-22_001_add_pos_invoice_lines/down.sql
```
**Contenido / Content:** Script SQL para revertir migración

### 7. Migration Documentation
```
ops/migrations/2026-01-22_001_add_pos_invoice_lines/README.md
```
**Contenido / Content:** Documentación de la migración

### 8. Migration Script
```
ops/run_migration.sh
```
**Contenido / Content:** Script ejecutable para correr migraciones

---

## 🔄 Comandos Git / Git Commands

```bash
# 1. Ver estado / Check status
git status

# Debería mostrar / Should show:
# Modified:
#   - apps/backend/app/models/core/invoiceLine.py
#   - apps/backend/app/modules/pos/application/invoice_integration.py
#   - apps/backend/app/i18n/locales/en.json
#   - apps/backend/app/i18n/locales/es.json
# Untracked:
#   - ops/migrations/2026-01-22_001_add_pos_invoice_lines/
#   - ops/run_migration.sh

# 2. Agregar cambios / Add changes
git add apps/backend/app/models/core/invoiceLine.py
git add apps/backend/app/modules/pos/application/invoice_integration.py
git add apps/backend/app/i18n/locales/en.json
git add apps/backend/app/i18n/locales/es.json
git add ops/migrations/2026-01-22_001_add_pos_invoice_lines/
git add ops/run_migration.sh

# O agregar todo / Or add all:
git add -A

# 3. Verificar staged files / Verify staged files
git status

# Debería mostrar "ready to commit"

# 4. Commit (opcional si lo haces después)
git commit -m "feat: Add POSLine polymorphic model support

- Add POSLine class for sector='pos' invoice lines
- Create pos_invoice_lines table with proper foreign keys
- Improve error handling in invoice_integration.py
- Add i18n translations for invoice types
- Add database migration scripts (up/down)

Fixes:
- AssertionError: No such polymorphic_identity 'pos'
- InFailedSqlTransaction errors in POS checkout

BREAKING CHANGE: None
Backward compatible: Yes"

# 5. Push (si ya tienes que hacerlo)
git push origin main
```

---

## 📊 Resumen de Cambios / Summary of Changes

### Líneas de Código / Lines of Code:
- **Modificadas / Modified:** ~60 líneas (en 4 archivos)
- **Nuevas / New:** ~75 líneas (en 4 archivos)
- **Total / Total:** ~135 líneas

### Archivos / Files:
- **Modificados / Modified:** 4
- **Nuevos / New:** 4
- **Total / Total:** 8 archivos

### Peso / Size:
- **Código / Code:** ~5 KB
- **Migraciones / Migrations:** ~2 KB
- **Scripts / Scripts:** ~3 KB
- **Total / Total:** ~10 KB

---

## ✅ Checklist Pre-Commit

- [ ] Verifiqué que los 4 archivos están modificados / Verified 4 files are modified
- [ ] Verifiqué que los 4 archivos nuevos están presentes / Verified 4 new files present
- [ ] Los archivos Python no tienen errores de sintaxis / Python files have no syntax errors
- [ ] El JSON es válido / JSON is valid
- [ ] El SQL es válido / SQL is valid
- [ ] El script shell es ejecutable / Shell script is executable

---

## 🔍 Verificar Archivos / Verify Files

```bash
# 1. Verificar Python syntax
python -m py_compile apps/backend/app/models/core/invoiceLine.py
python -m py_compile apps/backend/app/modules/pos/application/invoice_integration.py

# 2. Verificar JSON syntax
python -m json.tool apps/backend/app/i18n/locales/en.json > /dev/null
python -m json.tool apps/backend/app/i18n/locales/es.json > /dev/null

# 3. Verificar SQL syntax (si tienes psql)
psql -f ops/migrations/2026-01-22_001_add_pos_invoice_lines/up.sql --dry-run

# 4. Verificar script es ejecutable
file ops/run_migration.sh
# Debería decir: "bash script"
```

---

## 📋 Contenido Mínimo / Minimal Content

Si solo quieres los cambios esenciales sin documentación:

```bash
# Agregar solo lo esencial / Add only essential:
git add apps/backend/app/models/core/invoiceLine.py
git add apps/backend/app/modules/pos/application/invoice_integration.py
git add apps/backend/app/i18n/locales/en.json
git add apps/backend/app/i18n/locales/es.json
git add ops/migrations/2026-01-22_001_add_pos_invoice_lines/up.sql
git add ops/migrations/2026-01-22_001_add_pos_invoice_lines/down.sql
git add ops/run_migration.sh

# (Opcional / Optional) No incluir documentación de pruebas
# Do NOT add documentation files
```

---

## 🚀 Para Push a Main / For Push to Main

```bash
# 1. Crear rama / Create branch
git checkout -b feat/polymorphic-pos-support

# 2. Hacer cambios (ya hecho / already done above)

# 3. Commit
git commit -m "feat: Add POSLine polymorphic model support

- Add POSLine class for sector='pos'
- Create pos_invoice_lines table
- Improve error handling
- Add i18n translations
- Add migration scripts

Fixes: AssertionError and InFailedSqlTransaction"

# 4. Push a rama / Push to branch
git push origin feat/polymorphic-pos-support

# 5. Crear Pull Request / Create PR
# - Title: Add POSLine polymorphic model support
# - Description: Ver commit message
# - Reviewers: [tu team]
# - Labels: bug-fix, database, i18n

# 6. Merge cuando esté aprobado / Merge when approved
git checkout main
git pull origin main
git merge feat/polymorphic-pos-support
git push origin main
```

---

## 📦 Differencial / Diff Preview

```bash
# Ver cambios antes de commit / See changes before commit
git diff apps/backend/app/models/core/invoiceLine.py
git diff apps/backend/app/modules/pos/application/invoice_integration.py
git diff apps/backend/app/i18n/locales/en.json
git diff apps/backend/app/i18n/locales/es.json

# Ver archivos nuevos / See new files
git status --short ops/migrations/
git status --short ops/run_migration.sh
```

---

## 🔐 Seguridad / Security

- ✅ Sin credenciales hardcodeadas / No hardcoded credentials
- ✅ Sin contraseñas / No passwords
- ✅ Sin tokens / No tokens
- ✅ Sin datos sensibles / No sensitive data
- ✅ Scripts con permisos apropiados / Scripts with proper permissions

---

## 📋 Commit Message Template

```
feat: Add POSLine polymorphic model support

## Changes
- Add POSLine class to invoiceLine.py
- Create pos_invoice_lines table
- Improve error handling in invoice_integration.py
- Add i18n translations (EN/ES)
- Add database migration scripts

## Why
The database had invoice_lines records with sector='pos' but the Python models
only supported 'bakery' and 'workshop'. This caused polymorphic_identity errors
when fetching invoices and InFailedSqlTransaction errors during POS checkout.

## How
- Added POSLine model class with polymorphic_identity='pos'
- Created pos_invoice_lines table using joined table inheritance
- Improved error handling to prevent transaction cascade failures
- Added i18n keys for invoice types and error messages

## Testing
- Verify model loads: from app.models.core.invoiceLine import POSLine
- Verify table: \dt pos_invoice_lines in psql
- Test API: GET /api/v1/tenant/invoicing (should return 200)
- Test POS: POST /api/v1/tenant/pos/receipts/{id}/checkout (should return 200)

## Fixes
- Fixes: AssertionError: No such polymorphic_identity 'pos'
- Fixes: InFailedSqlTransaction errors
- Closes: #[issue-number] (if applicable)

## Breaking Changes
None - fully backward compatible

## Migration
Run: ./ops/run_migration.sh up 2026-01-22_001_add_pos_invoice_lines
Or: psql -U gestiqcloud_user -d gestiqcloud -f ops/migrations/2026-01-22_001_add_pos_invoice_lines/up.sql
```

---

**¡Listo para git add y commit!**  
**Ready for git add and commit!**
