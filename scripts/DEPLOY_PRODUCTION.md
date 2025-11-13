# 🚀 Guía de Despliegue a Producción - GestiQCloud

## ⚠️ IMPORTANTE: Orden de Despliegue

Para evitar errores de SQLAlchemy con tablas faltantes, **SIEMPRE** seguir este orden:

### 1️⃣ **ANTES de desplegar** - Preparar DB

```bash
# En servidor de producción (o localmente si tienes acceso a DB prod)

# 1. Aplicar todas las migraciones SQL
docker exec -i db_produccion psql -U postgres -d gestiqclouddb_prod < ops/migrations/2025-11-03_200_add_recipe_computed_columns/up.sql
docker exec -i db_produccion psql -U postgres -d gestiqclouddb_prod < ops/migrations/2025-11-03_200_production_orders/up.sql
docker exec -i db_produccion psql -U postgres -d gestiqclouddb_prod < ops/migrations/2025-11-03_201_add_unit_conversion/up.sql
docker exec -i db_produccion psql -U postgres -d gestiqclouddb_prod < ops/migrations/2025-11-03_201_hr_nominas/up.sql
docker exec -i db_produccion psql -U postgres -d gestiqclouddb_prod < ops/migrations/2025-11-03_202_finance_caja/up.sql
docker exec -i db_produccion psql -U postgres -d gestiqclouddb_prod < ops/migrations/2025-11-03_203_accounting/up.sql

# 2. Aplicar fix de tablas complementarias
docker exec -i db_produccion psql -U postgres -d gestiqclouddb_prod < scripts/fix_all_missing_tables.sql

# 3. Verificar que todas las tablas existen
docker exec db_produccion psql -U postgres -d gestiqclouddb_prod -c "\dt" | grep -E "nominas|empleados|production_orders|plan_cuentas|proveedores|ventas|compras"
```

### 2️⃣ **Reactivar modelos** - Antes de build

```bash
# En tu máquina local, ANTES de hacer git push

# Reactivar los 3 modelos deshabilitados
ren apps\backend\app\models\hr\nomina.py.disabled nomina.py
ren apps\backend\app\models\production\production_order.py.disabled production_order.py
ren apps\backend\app\models\accounting\plan_cuentas.py.disabled plan_cuentas.py

# Commit
git add apps/backend/app/models/
git commit -m "chore: reactivar modelos para producción"
git push origin main
```

### 3️⃣ **Desplegar backend**

```bash
# Ahora sí, despliega normalmente
docker compose up -d --build backend

# O si usas Render/otro servicio
git push # trigger auto-deploy
```

---

## 🔍 Verificación Post-Despliegue

```bash
# 1. Verificar que backend inicia sin errores
docker logs backend | grep -i "error\|exception"

# 2. Probar health check
curl https://tu-dominio.com/api/v1/imports/health

# 3. Probar login admin
curl -X POST https://tu-dominio.com/api/v1/admin/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"tu_password"}'
```

---

## 🏠 Desarrollo Local - Estado Actual

**Modelos deshabilitados** (temporalmente para desarrollo):
- `nomina.py.disabled` → Nóminas
- `production_order.py.disabled` → Órdenes producción
- `plan_cuentas.py.disabled` → Contabilidad

**Razón**: SQLAlchemy valida ForeignKeys al iniciar. En local, las migraciones se aplican después del backend, causando errores.

**Solución local**: Déjalos deshabilitados. No afectan funcionalidad core (importaciones, productos, stock, POS, clientes).

---

## 📋 Checklist Pre-Producción

- [ ] Ejecutar migraciones en DB producción (paso 1)
- [ ] Aplicar `fix_all_missing_tables.sql`
- [ ] Verificar tablas: `\dt` en DB producción
- [ ] Reactivar 3 modelos en local
- [ ] Commit y push
- [ ] Desplegar backend
- [ ] Verificar logs (sin errores SQLAlchemy)
- [ ] Probar login admin
- [ ] Probar módulo importaciones
- [ ] Probar POS (si aplica)

---

## 🆘 Si algo falla en producción

1. **Rollback modelos**:
```bash
git revert HEAD
git push
```

2. **O deshabilitar modelos temporalmente**:
```bash
# En servidor prod
docker exec backend mv /app/app/models/hr/nomina.py /app/app/models/hr/nomina.py.disabled
docker exec backend mv /app/app/models/production/production_order.py /app/app/models/production/production_order.py.disabled
docker exec backend mv /app/app/models/accounting/plan_cuentas.py /app/app/models/accounting/plan_cuentas.py.disabled
docker compose restart backend
```

---

**Última actualización**: 2025-11-03
**Estado**: Migraciones creadas ✅ | Modelos listos ✅ | Scripts preparados ✅
