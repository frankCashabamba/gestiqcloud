# UUID Migration - Deployment Guide

**Last Updated**: 2025-11-11  
**Status**: 🚀 **PRODUCTION READY**

---

## Summary

All legacy int IDs have been migrated to UUIDs for:
- `modulos_modulo`
- `modulos_empresamodulo`
- `modulos_moduloasignado`
- `core_rolempresa`

All HTTP endpoints now expect UUIDs instead of integers.

---

## Validation Results

✅ **ALL CHECKS PASSED**

```
Deprecated Functions.................... ✅ PASS
SQLAlchemy Models....................... ✅ PASS
HTTP Interfaces......................... ✅ PASS
Migration Script........................ ✅ PASS
```

Run validation anytime with:
```bash
python test_uuid_migration.py
```

---

## Changes Made

### 1. Code Changes

| File | Change | Status |
|------|--------|--------|
| `app/modules/facturacion/crud.py` | Replaced `generar_numero_factura()` with `generar_numero_documento()` | ✅ |
| `app/models/core/modulo.py` | All IDs converted to PGUUID | ✅ |
| `app/models/empresa/rolempresas.py` | id & rol_base_id converted to UUID | ✅ |
| `app/models/empresa/empresa.py` | PerfilUsuario.usuario_id converted to UUID | ✅ |

### 2. HTTP Endpoints

All endpoints now use UUID path parameters:

```
PATCH /api/v1/tenant/usuarios/{usuario_id: UUID}
PATCH /api/v1/tenant/clientes/{cliente_id: UUID}
PATCH /api/v1/tenant/almacenes/{wid: UUID}
PATCH /api/v1/tenant/facturas/{factura_id: UUID}
POST  /api/v1/tenant/facturas/{factura_id: UUID}/emitir
```

**Invalid UUID format returns**: `422 Unprocessable Entity`

Example valid UUIDs:
```
550e8400-e29b-41d4-a716-446655440000
f47ac10b-58cc-4372-a567-0e02b2c3d479
```

### 3. Migration Script

Location: `alembic/versions/migration_uuid_ids.py`

Handles:
- Table recreation with UUID PKs
- Data preservation (when possible)
- FK updates
- Cascade drops where needed

---

## Pre-Deployment Checklist

### 1. Database Backup
```bash
# PostgreSQL
pg_dump -Fc -v -f backup_$(date +%Y%m%d_%H%M%S).fc production_db

# Verify backup
pg_restore -l backup_*.fc | head -10
```

### 2. Code Deployment
```bash
git pull origin main
python test_uuid_migration.py  # Must pass
```

### 3. Environment Check
```bash
# Verify environment variables
echo $DATABASE_URL
echo $ENV  # Should be "production"

# Database connectivity
python -c "from app.config.database import SessionLocal; db = SessionLocal(); print('✅ DB OK')"
```

---

## Deployment Steps

### Step 1: Maintenance Window
```bash
# Put app in maintenance mode
# Update status page: "Database maintenance in progress"
# Estimated: 5-15 minutes
```

### Step 2: Database Migration
```bash
cd alembic

# Run migration
alembic upgrade head

# Verify all tables updated
psql production_db -c "
  SELECT schemaname, tablename, column_name, data_type
  FROM information_schema.columns
  WHERE tablename IN ('modulos_modulo', 'modulos_empresamodulo', 'core_rolempresa')
  AND column_name = 'id'
  ORDER BY tablename;
"
```

Expected output:
```
modulos_modulo           | id | uuid
modulos_empresamodulo    | id | uuid
modulos_moduloasignado   | id | uuid
core_rolempresa          | id | uuid
```

### Step 3: Application Deployment
```bash
# Stop current app
systemctl stop myapp

# Deploy new code
git pull && pip install -r requirements.txt

# Start app
systemctl start myapp

# Check health
curl http://localhost:8000/api/v1/health
```

### Step 4: Smoke Tests
```bash
# Test with real UUID
curl -H "Authorization: Bearer $TOKEN" \
     http://api.example.com/api/v1/tenant/usuarios/550e8400-e29b-41d4-a716-446655440000

# Test invalid UUID (should return 422)
curl -H "Authorization: Bearer $TOKEN" \
     http://api.example.com/api/v1/tenant/usuarios/123 \
     -w "\nStatus: %{http_code}\n"
```

### Step 5: Resume Operations
```bash
# Update status page: "Database maintenance complete"
# Monitor logs for errors
tail -f /var/log/myapp/error.log
```

---

## Rollback Plan

### If migration fails:

**1. Restore Database**
```bash
# Stop app
systemctl stop myapp

# Restore backup
pg_restore -d production_db -Fc backup_*.fc

# Verify recovery
psql production_db -c "SELECT COUNT(*) FROM modulos_modulo;"

# Start app with old code
git checkout previous_tag
systemctl start myapp
```

**2. Notify Clients**
```
Subject: API Format Update - Rollback Notice

The UUID migration has been rolled back.
Please continue using integer IDs for now.
We will reschedule the migration for [DATE].
```

**3. Post-Incident**
- [ ] Review migration logs
- [ ] Identify failure cause
- [ ] Schedule post-mortem
- [ ] Plan retry

---

## Post-Deployment Verification

### Day 1: Intensive Monitoring
- Monitor error logs for `422 Unprocessable Entity`
- Check database query performance
- Monitor API response times
- Verify RLS still enforces tenant isolation

### Metrics to Watch
```
- Request error rate (should be ~0%)
- UUID validation errors (should be ~0%)
- Database query latency (should be unchanged)
- API response time (should be unchanged)
```

### Commands to Monitor
```bash
# Error rate
tail -100 /var/log/myapp/error.log | grep "422\|uuid\|Unprocessable"

# Database performance
psql production_db -c "
  SELECT query, mean_exec_time, calls
  FROM pg_stat_statements
  WHERE query LIKE '%modulos%'
  ORDER BY mean_exec_time DESC;
"

# RLS verification
psql production_db -c "
  SELECT COUNT(*) FROM modulos_modulo m
  WHERE m.tenant_id = current_setting('rls.tenant_id')::uuid;
"
```

---

## Client Communication

### Email Template

```
Subject: API Update - UUID Format Change

Dear API Consumers,

We've completed a database migration that changes the format of resource IDs:

OLD FORMAT: integer
  GET /api/v1/tenant/usuarios/123

NEW FORMAT: UUID
  GET /api/v1/tenant/usuarios/550e8400-e29b-41d4-a716-446655440000

What you need to do:
1. Update your API clients to send UUIDs instead of integers
2. Update any hardcoded IDs in your configuration
3. Test thoroughly before the migration date

Timeline:
- [DATE] 00:00 UTC: Migration begins
- [DATE] 01:00 UTC: Expected completion
- [DATE] 01:00-02:00 UTC: Monitoring period

Invalid requests will return:
  422 Unprocessable Entity (Invalid UUID format)

Questions? Contact support@example.com
```

---

## Related Documentation

- **Code Changes**: See `MIGRATION_SUMMARY.md`
- **Validation Results**: See `VALIDATION_RESULTS.md`
- **Model Changes**: See `app/models/core/modulo.py`
- **Migration Script**: See `alembic/versions/migration_uuid_ids.py`

---

## Support & Escalation

### During Deployment
- **Slack Channel**: #database-migration
- **On-Call Engineer**: [NAME]
- **Database Admin**: [NAME]

### After Deployment
- Monitor error logs
- Track UUID validation errors
- Prepare rollback plan (keep it ready for 48 hours)

---

## Completion Checklist

- [x] Code migration complete
- [x] Tests passing
- [x] Migration script created
- [x] Documentation complete
- [ ] Backup verified (DO THIS)
- [ ] Maintenance window scheduled
- [ ] Client communication sent
- [ ] Deployment team briefed
- [ ] Rollback plan approved
- [ ] Go/No-Go decision made

---

**Next Step**: Schedule maintenance window and begin deployment.

