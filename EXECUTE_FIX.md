# EXECUTE FIX NOW | EJECUTAR FIX AHORA

## ⚠️ IMPORTANT | IMPORTANTE
**Read first:** `START_HERE_POLYMORPHIC_FIX.md`  
**Lee primero:** `START_HERE_POLYMORPHIC_FIX.md`

---

## 🎯 3 PASOS / 3 STEPS (5 minutos | 5 minutes)

### PASO 1 / STEP 1: Actualizar Código / Update Code

```bash
cd /path/to/gestiqcloud
git pull origin main
```

**Resultado esperado / Expected output:**
```
remote: Enumerating objects: 50, done.
...
Fast-forward
 apps/backend/app/models/core/invoiceLine.py | 15 +++++++++++++
 ...
```

---

### PASO 2 / STEP 2: Ejecutar Migración SQL / Run SQL Migration

```bash
# Opción A / Option A: Usar script
chmod +x ops/run_migration.sh
./ops/run_migration.sh up 2026-01-22_001_add_pos_invoice_lines

# O / OR Opción B / Option B: psql directo
psql -U gestiqcloud_user -d gestiqcloud \
  -f ops/migrations/2026-01-22_001_add_pos_invoice_lines/up.sql

# O / OR Opción C / Option C: Desde psql interactivo
psql -U gestiqcloud_user -d gestiqcloud
\i ops/migrations/2026-01-22_001_add_pos_invoice_lines/up.sql
\dt pos_invoice_lines
\q
```

**Resultado esperado / Expected output:**
```
✅ Migration applied successfully
```

---

### PASO 3 / STEP 3: Reiniciar Backend / Restart Backend

```bash
# Opción A / Option A: systemd
systemctl restart gestiqcloud-backend

# O / OR Opción B / Option B: Docker
docker-compose restart backend

# O / OR Opción C / Option C: Manual
pkill -f uvicorn
cd /path/to/gestiqcloud/apps/backend
python -m uvicorn app.main:app
```

---

## ✅ VERIFICACIÓN / VERIFICATION (1 minuto)

```bash
# 1. Verificar tabla / Verify table
psql -U gestiqcloud_user -d gestiqcloud -c "\dt pos_invoice_lines"

# 2. Test API - Obtener facturas / Get invoices
curl -s http://localhost:8000/api/v1/tenant/invoicing \
  -H "Authorization: Bearer $TOKEN" | jq .

# 3. Test API - POS Checkout
curl -s -X POST http://localhost:8000/api/v1/tenant/pos/receipts/{id}/checkout \
  -H "Authorization: Bearer $TOKEN" | jq .

# 4. Revisar logs / Check logs
tail -20 /var/log/gestiqcloud/backend.log | grep -i "polymorphic\|infailed"
# Should be EMPTY | Debe estar VACÍO
```

---

## ✨ ¡HECHO! / DONE!

Si todo arriba funcionó sin errores, ¡tu fix está aplicado!  
If everything above worked without errors, your fix is applied!

---

## 🆘 SI ALGO FALLA / IF SOMETHING FAILS

### Opción 1: Leer documentación / Read documentation
```
START_HERE_POLYMORPHIC_FIX.md → Sección "Si Algo Sale Mal"
```

### Opción 2: Deshacer / Rollback
```bash
# Deshacer migración / Undo migration
./ops/run_migration.sh down 2026-01-22_001_add_pos_invoice_lines

# Deshacer código / Undo code
git reset --hard HEAD~1

# Reiniciar / Restart
systemctl restart gestiqcloud-backend
```

### Opción 3: Ver logs detallados / View detailed logs
```bash
tail -200 /var/log/gestiqcloud/backend.log | grep -A 10 "Error\|Exception"
```

---

## 📚 DOCUMENTACIÓN / DOCUMENTATION

| Lee si... / Read if... | Archivo / File |
|---|---|
| Tienes 5 minutos | START_HERE_POLYMORPHIC_FIX.md |
| Necesitas entender todo | SOLUTION_POLYMORPHIC_IDENTITY_ERROR.md |
| Quieres ver el SQL | MIGRATION_SQL_FILES.md |
| Necesitas más detalles | IMPLEMENTATION_SUMMARY_BILINGUAL.md |
| Tienes problemas | APPLY_MIGRATION_NO_ALEMBIC.md |

---

## 🎉 FELICITACIONES! / CONGRATULATIONS!

Los errores deben haber desaparecido:  
The errors should have disappeared:

❌ **Antes / Before:**
```
AssertionError: No such polymorphic_identity 'pos'
InFailedSqlTransaction: transacción abortada
```

✅ **Después / After:**
```
GET /api/v1/tenant/invoicing → 200 OK
POST /api/v1/tenant/pos/receipts/{id}/checkout → 200 OK
```

---

**Tiempo total / Total time:** 5-10 minutos | minutes  
**Dificultad / Difficulty:** 🟢 Bajo | Low  
**Riesgo / Risk:** 🟢 Bajo | Low
