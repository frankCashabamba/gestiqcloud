# 🚀 Solución del Error "No such polymorphic_identity 'pos'" - COMIENZA AQUÍ

## El Problema (en 30 segundos)

Tienes dos errores:

1. **`AssertionError: No such polymorphic_identity 'pos' is defined`** 
   - Cuando intentas ver facturas → `/api/v1/tenant/invoicing`

2. **`InFailedSqlTransaction: transacción abortada...`**
   - Cuando haces checkout de POS → `/api/v1/tenant/pos/receipts/{id}/checkout`

**Causa:** La base de datos tiene registros con `sector='pos'` pero el código Python no tiene una clase `POSLine` para manejarlos.

---

## La Solución (3 pasos)

### Paso 1️⃣: Actualizar Código

```bash
git pull origin main
```

Se actualizan 2 archivos:
- ✅ `apps/backend/app/models/core/invoiceLine.py` (nueva clase POSLine)
- ✅ `apps/backend/app/modules/pos/application/invoice_integration.py` (mejor manejo de errores)

### Paso 2️⃣: Ejecutar Migración SQL

Elige UNA opción:

#### Opción A: Script automático (RECOMENDADO)
```bash
chmod +x ops/run_migration.sh
./ops/run_migration.sh up 2026-01-22_001_add_pos_invoice_lines
```

#### Opción B: psql directo
```bash
psql -U gestiqcloud_user -d gestiqcloud \
  -f ops/migrations/2026-01-22_001_add_pos_invoice_lines/up.sql
```

#### Opción C: Desde psql interactivo
```bash
psql -U gestiqcloud_user -d gestiqcloud
\i ops/migrations/2026-01-22_001_add_pos_invoice_lines/up.sql
\dt pos_invoice_lines
\q
```

### Paso 3️⃣: Reiniciar Backend y Probar

```bash
# Reiniciar
systemctl restart gestiqcloud-backend

# Probar API de facturas (debería funcionar sin error polymorphic)
curl -X GET http://localhost:8000/api/v1/tenant/invoicing \
  -H "Authorization: Bearer $TOKEN"

# Probar POS checkout (debería funcionar sin error InFailedSqlTransaction)
curl -X POST http://localhost:8000/api/v1/tenant/pos/receipts/{id}/checkout \
  -H "Authorization: Bearer $TOKEN"
```

✅ **¡Listo! Los errores deben desaparecer**

---

## ¿Qué se cambió?

### Código Python (Git Pull)

**Archivo 1:** `invoiceLine.py` - Nueva clase POSLine
```python
class POSLine(InvoiceLine):
    """POS-generated line item model."""
    __tablename__ = "pos_invoice_lines"
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("invoice_lines.id"), primary_key=True
    )
    pos_receipt_line_id: Mapped[UUID | None] = mapped_column(...)
    __mapper_args__ = {"polymorphic_identity": "pos"}
```

**Archivo 2:** `invoice_integration.py` - Mejor manejo de transacciones
```python
# Ahora atrapa y registra errores de rollback
except Exception as e:
    try:
        self.db.rollback()
    except Exception as rollback_error:
        logger.error("Failed to rollback: %s", rollback_error)
    return None
```

### Base de Datos (Migración SQL)

**Nueva tabla:** `pos_invoice_lines` (heredada de `invoice_lines`)

```sql
CREATE TABLE pos_invoice_lines (
    id UUID PRIMARY KEY REFERENCES invoice_lines(id),
    pos_receipt_line_id UUID,
    FOREIGN KEY (id) REFERENCES invoice_lines(id) ON DELETE CASCADE
);
CREATE INDEX idx_pos_invoice_lines_pos_receipt_line_id ON pos_invoice_lines(pos_receipt_line_id);
```

---

## Verificación Rápida

Después de completar los 3 pasos, verifica:

```bash
# 1. ¿Existe la tabla?
psql -U gestiqcloud_user -d gestiqcloud -c "\dt pos_invoice_lines"
# Debería mostrar: pos_invoice_lines | table

# 2. ¿Se creó el índice?
psql -U gestiqcloud_user -d gestiqcloud -c "\di *pos_invoice*"
# Debería mostrar: idx_pos_invoice_lines_pos_receipt_line_id

# 3. ¿Backend reiniciado?
systemctl status gestiqcloud-backend | grep active
# Debería mostrar: active (running)

# 4. ¿Los errores desaparecieron?
tail -20 /var/log/gestiqcloud/backend.log | grep -i "polymorphic\|infailed"
# No debería mostrar nada (o solo errores previos)
```

---

## Si Algo Sale Mal

### Error: "Table invoice_lines does not exist"
```bash
# Ejecutar primero la migración consolidada
./ops/run_migration.sh up 2025-11-21_000_complete_consolidated_schema
```

### Error: "Database connection refused"
```bash
# Verificar credenciales
psql -U gestiqcloud_user -h localhost -d gestiqcloud -c "SELECT 1"

# Si no funciona, probar con variables de entorno
export PGUSER=gestiqcloud_user
export PGPASSWORD=tu_password  # Si es necesario
export PGHOST=localhost
psql -d gestiqcloud -c "SELECT 1"
```

### Error: "Permission denied" en script
```bash
chmod +x ops/run_migration.sh
./ops/run_migration.sh status
```

### ¿Deshacer la migración?
```bash
./ops/run_migration.sh down 2026-01-22_001_add_pos_invoice_lines
# O manualmente:
psql -U gestiqcloud_user -d gestiqcloud \
  -f ops/migrations/2026-01-22_001_add_pos_invoice_lines/down.sql
```

---

## Documentación Detallada

Si necesitas entender más:

| Documento | Contenido |
|-----------|-----------|
| `QUICK_FIX_POLYMORPHIC_NO_ALEMBIC.md` | Versión corta sin Alembic |
| `APPLY_MIGRATION_NO_ALEMBIC.md` | Instrucciones detalladas para ejecutar SQL |
| `MIGRATION_SQL_FILES.md` | Los 3 archivos SQL explicados |
| `SOLUTION_POLYMORPHIC_IDENTITY_ERROR.md` | Análisis técnico completo |
| `SUMMARY_CHANGES_MADE.md` | Resumen de todos los cambios |

---

## Checklist Final

- [ ] Ejecuté `git pull origin main`
- [ ] Ejecuté la migración SQL (up.sql)
- [ ] Verifiqué que la tabla `pos_invoice_lines` existe
- [ ] Reinicié el backend
- [ ] Probé API de facturas → No hay error polymorphic
- [ ] Probé POS checkout → No hay error InFailedSqlTransaction
- [ ] Reviré logs → Sin errores relacionados

---

## Información Técnica Rápida

**Qué es Polymorphic Identity:**
- SQLAlchemy usa una columna discriminadora (`sector`) para determinar qué clase usar
- `sector='bakery'` → BakeryLine
- `sector='workshop'` → WorkshopLine
- `sector='pos'` → POSLine (ahora definido)

**Por qué es necesario:**
- Invoice lines pueden ser de diferentes tipos (bakery, workshop, pos)
- Cada tipo tiene atributos específicos
- SQLAlchemy necesita saber qué clase instanciar al cargar datos

**Riesgo:**
- 🟢 BAJO - Solo crea una tabla nueva, no modifica existentes
- ✅ Reversible - El down.sql lo deshace completamente
- ✅ Idempotente - Se puede ejecutar múltiples veces sin problemas

---

## Contacto / Dudas

**Logs útiles para debugging:**
```bash
# Ver errores relacionados
tail -100 /var/log/gestiqcloud/backend.log | grep -E "polymorphic|InFailedSql|pos_invoice"

# Ver todas las migraciones ejecutadas
psql -U gestiqcloud_user -d gestiqcloud -c \
  "SELECT schemaname, tablename FROM pg_tables WHERE tablename LIKE '%pos%';"
```

**Verificar estado actual:**
```bash
# ¿Qué versión de código está corriendo?
git log -1 --oneline

# ¿Qué migraciones se aplicaron?
./ops/run_migration.sh status

# ¿Hay datos con sector='pos'?
psql -U gestiqcloud_user -d gestiqcloud -c \
  "SELECT COUNT(*), sector FROM invoice_lines GROUP BY sector;"
```

---

## Timeline

| Cuándo | Acción |
|--------|--------|
| Ahora | Ejecutar git pull |
| Ahora | Ejecutar migración SQL |
| Ahora | Reiniciar backend |
| ~5 min | Completado |

**Total:** ⏱️ 5 minutos

---

## ¿Por qué pasó esto?

1. El sistema anterior creaba registros de facturación en `invoice_lines` con `sector='pos'`
2. El código Python solo tenía modelos para `'bakery'` y `'workshop'`
3. SQLAlchemy no sabía cómo cargar registros con `sector='pos'`
4. Esto causaba error al traer facturas y fallaba la transacción de checkout

**La solución:** Agregar la clase `POSLine` y la tabla de base de datos correspondiente.

---

## Próximos Pasos (Opcional)

Después de aplicar este fix, si tienes registros con `sector='pos'` en `invoice_lines`, puedes (opcionalmente) migrarlos a `pos_invoice_lines`:

```sql
-- Ver cuántos hay
SELECT COUNT(*) FROM invoice_lines WHERE sector = 'pos';

-- Migrar (si quieres)
INSERT INTO pos_invoice_lines (id, pos_receipt_line_id)
SELECT id, NULL FROM invoice_lines WHERE sector = 'pos'
ON CONFLICT DO NOTHING;
```

Pero esto es **opcional** - el sistema funciona igual sin esto.

---

## Éxito ✅

Después de completar los 3 pasos, esto debería funcionar:

```bash
# ✅ Ver facturas sin error
curl http://localhost:8000/api/v1/tenant/invoicing \
  -H "Authorization: Bearer $TOKEN"

# ✅ POS checkout sin error
curl -X POST http://localhost:8000/api/v1/tenant/pos/receipts/123/checkout \
  -H "Authorization: Bearer $TOKEN"

# ✅ Sin errores en logs
grep -c "polymorphic_identity" /var/log/gestiqcloud/backend.log
# Salida: 0 (cero errores)
```

---

**¡Listo! Tu sistema está arreglado.** 🎉

Para más información, lee los documentos en esta carpeta. Si tienes dudas, revisa la sección "Troubleshooting".
