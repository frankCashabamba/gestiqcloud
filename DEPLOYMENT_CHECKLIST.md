# Deployment Checklist - GestiQCloud

## ✅ Cambios Realizados (Enero 2025)

### 1. Frontend: Corrección de Rutas API ✅
**Archivo**: `apps/tenant/src/lib/http.ts` línea 4

**Antes**:
```typescript
export const API_URL = (env.apiUrl || '/v1').replace(/\/+$/g, '')
```

**Después**:
```typescript
export const API_URL = (env.apiUrl || '/api/v1').replace(/\/+$/g, '')
```

**Impacto**: Todos los módulos frontend ahora apuntan correctamente a `/api/v1/*` 🎯

### 2. Backend: SPEC-1 Implementación Completa ✅

#### Migraciones
- ✅ `ops/migrations/2025-10-24_140_spec1_tables/`
  - 8 nuevas tablas
  - RLS habilitado
  - Seeds UoM incluidas

#### Modelos (8 archivos)
- ✅ `app/models/spec1/` - SQLAlchemy models completos

#### Schemas (5 archivos)
- ✅ `app/schemas/spec1/` - Pydantic con validaciones

#### Routers (4 archivos)
- ✅ `app/routers/spec1_daily_inventory.py` (220 líneas)
- ✅ `app/routers/spec1_purchase.py` (160 líneas)
- ✅ `app/routers/spec1_milk_record.py` (150 líneas)
- ✅ `app/routers/spec1_importer.py` (100 líneas)

#### Servicios (2 archivos)
- ✅ `app/services/backflush.py` (340 líneas)
- ✅ `app/services/excel_importer_spec1.py` (350 líneas)

#### Integración
- ✅ `app/main.py` - 4 routers montados (líneas 250-278)

---

## 🚀 Pasos de Deployment

### Pre-deployment

#### 1. Verificar Variables de Entorno
```bash
# .env (desarrollo)
DB_DSN=postgresql://postgres:root@localhost:5432/gestiqclouddb_dev
REDIS_URL=redis://localhost:6379/0
FRONTEND_URL=http://localhost:8081
BACKFLUSH_ENABLED=0  # Activar cuando esté listo

# .env.production (producción)
DB_DSN=${DATABASE_URL}
REDIS_URL=${REDIS_URL}
FRONTEND_URL=https://app.gestiqcloud.com
BACKFLUSH_ENABLED=1
```

#### 2. Backup Base de Datos
```bash
# Local
docker exec db pg_dump -U postgres gestiqclouddb_dev > backup_pre_spec1_$(date +%Y%m%d_%H%M%S).sql

# Producción
pg_dump $DATABASE_URL > backup_pre_spec1_$(date +%Y%m%d_%H%M%S).sql
```

### Deployment (Local)

#### 1. Aplicar Migraciones
```bash
# Opción A: Script automático
python scripts/py/bootstrap_imports.py --dir ops/migrations

# Opción B: Manual
docker exec db psql -U postgres -d gestiqclouddb_dev < ops/migrations/2025-10-24_140_spec1_tables/up.sql
```

#### 2. Verificar Tablas
```bash
docker exec db psql -U postgres -d gestiqclouddb_dev -c "\dt daily_inventory"
docker exec db psql -U postgres -d gestiqclouddb_dev -c "SELECT COUNT(*) FROM uom;"
# Debe retornar 8 (KG, G, L, ML, UN, LB, OZ, DOC)
```

#### 3. Rebuild Backend
```bash
docker compose build backend
docker compose up -d backend
```

#### 4. Verificar Logs
```bash
docker logs backend | grep "SPEC-1"
docker logs backend | grep "Daily Inventory"
docker logs backend | grep "Purchase"
docker logs backend | grep "Milk Record"
```

Debes ver:
```
Daily Inventory router mounted at /api/v1/daily-inventory
Purchase router mounted at /api/v1/purchases
Milk Record router mounted at /api/v1/milk-records
SPEC-1 Importer router mounted at /api/v1/imports/spec1
```

#### 5. Rebuild Frontend
```bash
cd apps/tenant
npm run build
docker compose build tenant
docker compose up -d tenant
```

#### 6. Tests de Humo
```bash
# Health
curl http://localhost:8000/health

# OpenAPI
curl http://localhost:8000/docs | grep "daily-inventory"

# Tenant frontend
curl http://localhost:8081/ -I
```

### Deployment (Producción)

#### 1. Migraciones
```bash
# Render/Heroku con CLI
render exec postgresql-service pg_dump > backup.sql
render exec backend python scripts/py/bootstrap_imports.py --dir ops/migrations

# O vía SSH
ssh production-server
cd /app
python scripts/py/bootstrap_imports.py --dir ops/migrations
```

#### 2. Deploy Backend
```bash
git push production main

# O Docker Registry
docker build -t gestiqcloud/backend:latest .
docker push gestiqcloud/backend:latest
```

#### 3. Deploy Frontend
```bash
cd apps/tenant
npm run build
# Deploy a CDN/S3 o servicio de hosting
```

#### 4. Verificación Post-Deploy
```bash
# API Health
curl https://api.gestiqcloud.com/health

# SPEC-1 endpoints
curl https://api.gestiqcloud.com/api/v1/imports/spec1/template

# Frontend
curl https://app.gestiqcloud.com/ -I
```

---

## 🧪 Testing Checklist

### Backend Tests
```bash
# Unit tests (si existen)
pytest apps/backend/app/tests/test_spec1*.py

# Integration tests
./test_spec1.sh  # Ver SPEC1_QUICKSTART.md
```

### Frontend Tests
```bash
cd apps/tenant
npm test

# E2E (si aplica)
npm run test:e2e
```

### Manual Testing
- [ ] Login funciona
- [ ] Módulos POS cargan
- [ ] Importador Excel funciona
- [ ] Daily inventory CRUD funciona
- [ ] Backflush se ejecuta (si está habilitado)
- [ ] Sin errores en consola del navegador

---

## 🔄 Rollback Plan

### Si algo falla:

#### 1. Rollback Migraciones
```bash
# Local
docker exec db psql -U postgres -d gestiqclouddb_dev < ops/migrations/2025-10-24_140_spec1_tables/down.sql

# Producción
psql $DATABASE_URL < ops/migrations/2025-10-24_140_spec1_tables/down.sql
```

#### 2. Rollback Código
```bash
git revert HEAD
git push production main
```

#### 3. Restaurar DB
```bash
# Local
docker exec -i db psql -U postgres -d gestiqclouddb_dev < backup_pre_spec1_*.sql

# Producción
psql $DATABASE_URL < backup_pre_spec1_*.sql
```

---

## 📊 Monitoreo Post-Deploy

### Logs a Revisar
```bash
# Backend errors
docker logs backend | grep -i error

# Frontend errors (browser console)
# Abrir DevTools → Console

# DB slow queries
docker exec db psql -U postgres -c "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"
```

### Métricas Clave
- Tiempo de respuesta API < 300ms
- Errores 5xx < 0.5%
- Éxito de importaciones > 95%
- Uso de CPU/RAM dentro de límites

---

## 🎯 Features Flags

### Backflush Automático
```bash
# Desactivado por defecto
BACKFLUSH_ENABLED=0

# Activar gradualmente:
# 1. Solo en tenant de prueba
# 2. Monitorear stock_moves
# 3. Si funciona bien, activar global
BACKFLUSH_ENABLED=1
```

### ElectricSQL Sync (M3)
```bash
# Aún no implementado
ELECTRIC_SYNC_ENABLED=0
```

---

## 📚 Documentación Relacionada

- **SPEC1_IMPLEMENTATION_SUMMARY.md** - Resumen técnico completo
- **SPEC1_QUICKSTART.md** - Guía de inicio rápido
- **AGENTS.md** - Arquitectura del sistema
- **spec_1_digitalizacion...md** - SPEC original

---

## ✅ Final Checklist

Pre-Deploy:
- [ ] Backup DB realizado
- [ ] Variables de entorno configuradas
- [ ] Tests pasando localmente

Deploy:
- [ ] Migraciones aplicadas
- [ ] Backend desplegado
- [ ] Frontend desplegado
- [ ] Logs sin errores críticos

Post-Deploy:
- [ ] Health checks OK
- [ ] Endpoints SPEC-1 responden
- [ ] Frontend carga correctamente
- [ ] Tests manuales completados
- [ ] Monitoreo activado

---

**Aprobado por**: _______________________  
**Fecha**: _______________________  
**Versión**: 1.0.0
