# Fix Rápido - Sin Alembic (Tu Sistema)

Como no usas alembic, aquí está la forma correcta de aplicar la migración.

## Paso 1: Actualizar Código

```bash
git pull origin main
```

Se actualizan:
- ✅ `apps/backend/app/models/core/invoiceLine.py` (agregada clase POSLine)
- ✅ `apps/backend/app/modules/pos/application/invoice_integration.py` (mejor manejo de errores)
- ✅ `ops/migrations/2026-01-22_001_add_pos_invoice_lines/` (nueva migración SQL)

## Paso 2: Ejecutar Migración SQL

### Opción A: Con Script (Recomendado)

```bash
chmod +x ops/run_migration.sh
./ops/run_migration.sh up 2026-01-22_001_add_pos_invoice_lines
```

### Opción B: Directo con psql

```bash
psql -U gestiqcloud_user -d gestiqcloud \
  -f ops/migrations/2026-01-22_001_add_pos_invoice_lines/up.sql
```

### Opción C: Desde psql interactivo

```bash
psql -U gestiqcloud_user -d gestiqcloud
```

Luego en el prompt psql:

```sql
\i ops/migrations/2026-01-22_001_add_pos_invoice_lines/up.sql
```

## Paso 3: Verificar

```bash
# En psql
psql -U gestiqcloud_user -d gestiqcloud -c "\dt pos_invoice_lines"
```

Deberías ver:
```
               List of relations
 Schema |         Name          | Type  | Owner
--------+-----------------------+-------+----------
 public | pos_invoice_lines     | table | postgres
```

## Paso 4: Reiniciar Backend

```bash
systemctl restart gestiqcloud-backend
```

## Paso 5: Probar APIs

```bash
# Debería traer facturas sin error "No such polymorphic_identity 'pos'"
curl -X GET http://localhost:8000/api/v1/tenant/invoicing \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"

# Debería crear order sin error "InFailedSqlTransaction"
curl -X POST http://localhost:8000/api/v1/tenant/pos/receipts/{id}/checkout \
  -H "Authorization: Bearer $TOKEN"
```

## Si Necesitas Deshacer

```bash
./ops/run_migration.sh down 2026-01-22_001_add_pos_invoice_lines
# o
psql -U gestiqcloud_user -d gestiqcloud \
  -f ops/migrations/2026-01-22_001_add_pos_invoice_lines/down.sql
```

## Archivos Generados

```
ops/
└── migrations/
    └── 2026-01-22_001_add_pos_invoice_lines/
        ├── up.sql          ← Aplica la migración
        ├── down.sql        ← Deshace la migración
        └── README.md       ← Documentación

ops/
└── run_migration.sh        ← Script para ejecutar migraciones fácilmente
```

## Documentación Completa

- **Con más detalle:** `APPLY_MIGRATION_NO_ALEMBIC.md`
- **Solución técnica:** `SOLUTION_POLYMORPHIC_IDENTITY_ERROR.md`
- **Índice general:** `README_FIX_POLYMORPHIC_POS.md`

## Checklist

- [ ] Pull código: `git pull origin main`
- [ ] Ejecutar migración SQL (up.sql)
- [ ] Verificar tabla: `\dt pos_invoice_lines`
- [ ] Reiniciar backend
- [ ] Probar API de facturas
- [ ] Probar POS checkout
- [ ] Verificar logs (no debe haber errores polymorphic)

---

**Tiempo total:** ~5 minutos  
**Riesgo:** Bajo (cambios aditivos, reversibles)
