# 🚀 DEPLOY AHORA - Solución Polymorphic Identity 'pos'

## Estado: LISTO PARA APLICAR

Todo está preparado. Solo necesitas ejecutar los comandos.

---

## PASO 1: Actualizar Código

```bash
git pull origin main
```

**Qué se actualiza:**
- ✅ `apps/backend/app/models/core/invoiceLine.py` (nueva clase POSLine)
- ✅ `apps/backend/app/modules/pos/application/invoice_integration.py` (mejor error handling)
- ✅ `ops/migrations/2026-01-22_001_add_pos_invoice_lines/` (3 archivos SQL)
- ✅ `ops/run_migration.sh` (script ejecutable)

---

## PASO 2: Ejecutar Migración SQL

### Opción A: Usar el script (RECOMENDADO)

```bash
chmod +x ops/run_migration.sh
./ops/run_migration.sh up 2026-01-22_001_add_pos_invoice_lines
```

### Opción B: Comando psql directo

```bash
psql -U gestiqcloud_user -d gestiqcloud \
  -f ops/migrations/2026-01-22_001_add_pos_invoice_lines/up.sql
```

### Opción C: Desde psql interactivo

```bash
psql -U gestiqcloud_user -d gestiqcloud
```

Luego en el prompt:
```sql
\i ops/migrations/2026-01-22_001_add_pos_invoice_lines/up.sql
\dt pos_invoice_lines
\q
```

---

## PASO 3: Verificar la Migración

```bash
# Verificar tabla
psql -U gestiqcloud_user -d gestiqcloud -c "\dt pos_invoice_lines"

# Debería mostrar:
#                List of relations
#  Schema |         Name          | Type  | Owner
# --------+-----------------------+-------+-------
#  public | pos_invoice_lines     | table | postgres
```

---

## PASO 4: Reiniciar Backend

```bash
systemctl restart gestiqcloud-backend
```

O si usas otro método:
```bash
# Docker
docker-compose restart backend

# Manual
pkill -f uvicorn
python -m uvicorn app.main:app
```

---

## PASO 5: Verificar APIs Funcionan

```bash
# Test 1: Obtener facturas (antes daba error polymorphic)
curl -X GET http://localhost:8000/api/v1/tenant/invoicing \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" | jq .

# Debería devolver: 200 OK con lista de facturas

# Test 2: POS Checkout (antes daba InFailedSqlTransaction)
curl -X POST http://localhost:8000/api/v1/tenant/pos/receipts/{receipt_id}/checkout \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"

# Debería devolver: 200 OK con documentos creados
```

---

## PASO 6: Verificar Logs

```bash
# No debería haber errores polymorphic
tail -50 /var/log/gestiqcloud/backend.log | grep -i "polymorphic\|infailed"

# Si ve errores, ejecutar:
tail -200 /var/log/gestiqcloud/backend.log
```

---

## ✅ CHECKLIST DE VERIFICACIÓN

- [ ] `git pull origin main` completado
- [ ] Migración SQL ejecutada sin errores
- [ ] `\dt pos_invoice_lines` muestra tabla
- [ ] Backend reiniciado
- [ ] `GET /api/v1/tenant/invoicing` retorna 200
- [ ] `POST /api/v1/tenant/pos/.../checkout` retorna 200
- [ ] Logs: 0 errores polymorphic
- [ ] Logs: 0 errores InFailedSqlTransaction

---

## ⏱️ TIEMPO TOTAL

- Paso 1 (git pull): 1 minuto
- Paso 2 (migración): 30 segundos
- Paso 3 (verificar): 30 segundos
- Paso 4 (reinicio): 2 minutos
- Paso 5 (test): 1 minuto
- Paso 6 (logs): 1 minuto

**TOTAL: ~6 minutos**

---

## 🔙 SI ALGO SALE MAL

### Revertir Migración

```bash
# Opción 1: Script
./ops/run_migration.sh down 2026-01-22_001_add_pos_invoice_lines

# Opción 2: psql directo
psql -U gestiqcloud_user -d gestiqcloud \
  -f ops/migrations/2026-01-22_001_add_pos_invoice_lines/down.sql
```

### Revertir Código

```bash
git reset --hard HEAD~1
systemctl restart gestiqcloud-backend
```

---

## 📚 DOCUMENTACIÓN DE REFERENCIA

Si tienes dudas:

| Pregunta | Lee |
|----------|-----|
| ¿Qué se cambia? | `SUMMARY_CHANGES_MADE.md` |
| ¿Por qué este error? | `SOLUTION_POLYMORPHIC_IDENTITY_ERROR.md` |
| ¿Cómo funcionan las migraciones? | `MIGRATION_SQL_FILES.md` |
| ¿Qué es i18n? | Ver abajo |
| Troubleshooting | `APPLY_MIGRATION_NO_ALEMBIC.md` |

---

## 🌐 SOBRE I18N

### Estado Actual

El proyecto ya tiene i18n configurado. Los textos no necesitan traducciones en el código porque:

1. **Modelos Python**: Solo tienen docstrings (no mostrados a usuarios)
2. **Mensajes de Error**: Se manejan via middleware de logging
3. **Respuestas API**: Usan archivos de traducción centralizados

### POSLine Model

El nuevo modelo `POSLine` está en inglés:
```python
class POSLine(InvoiceLine):
    """POS-generated line item model."""  # Docstring en inglés
    __tablename__ = "pos_invoice_lines"
    __mapper_args__ = {"polymorphic_identity": "pos"}
```

### Archivos de Traducción

No hay cambios necesarios en archivos i18n porque:
- El `sector='pos'` es un valor técnico, no un label de usuario
- Los errores se loguean, no se muestran a usuarios
- Las APIs retornan datos, no strings de UI

### Si Necesitas Agregar Traducciones

Busca en:
```
apps/backend/app/i18n/
apps/backend/locales/
apps/frontend/i18n/
```

Y agrega claves si es necesario.

---

## 🎯 COMANDO QUICK START

Si ejecutas esto, todo se hace automáticamente:

```bash
# Copiar y ejecutar
git pull origin main && \
chmod +x ops/run_migration.sh && \
./ops/run_migration.sh up 2026-01-22_001_add_pos_invoice_lines && \
systemctl restart gestiqcloud-backend && \
echo "✅ Deployment completed" && \
sleep 3 && \
curl -s http://localhost:8000/api/v1/tenant/invoicing \
  -H "Authorization: Bearer $TOKEN" | head -20
```

---

## 📞 SOPORTE

Si algo falla:

```bash
# Mostrar errores detallados
journalctl -u gestiqcloud-backend -n 50 -f

# O desde archivo
tail -100 /var/log/gestiqcloud/backend.log | grep -A 5 "Error"

# Chequear BD
psql -U gestiqcloud_user -d gestiqcloud -c "SELECT COUNT(*) FROM pos_invoice_lines;"
```

---

## ✨ DESPUÉS DEL DEPLOY

Todo debería funcionar normalmente. Si algo no funciona:

1. ✅ Revisar logs: `tail -50 /var/log/gestiqcloud/backend.log`
2. ✅ Verificar tabla: `\dt pos_invoice_lines`
3. ✅ Revisar índices: `\di *pos_invoice*`
4. ✅ Reconectar: `systemctl restart gestiqcloud-backend`

---

**¡Listo! Ahora puedes ejecutar los comandos arriba.** 🚀
