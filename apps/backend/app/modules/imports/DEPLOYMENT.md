# 🚀 Deployment - Sistema de Importación 100% Completo

## ✅ Pre-requisitos

### 1. Base de Datos

Tablas requeridas (ya deberían existir):

```sql
-- Verificar tablas
SELECT tablename FROM pg_tables
WHERE tablename IN (
  'products', 'product_categories', 'stock_items', 'warehouses',
  'invoices', 'invoice_lines', 'clients',
  'bank_transactions', 'bank_accounts',
  'gastos', 'proveedores',
  'import_batches', 'import_items', 'import_lineage'
)
ORDER BY tablename;
```

Si falta alguna tabla, ejecutar migraciones:
```bash
alembic upgrade head
```

### 2. Variables de Entorno

```bash
# .env o configuración del servidor
IMPORTS_ENABLED=1
DATABASE_URL=postgresql://user:pass@host:5432/gestiq
REDIS_URL=redis://localhost:6379/1

# OCR
IMPORTS_OCR_LANG=spa+eng
IMPORTS_OCR_DPI=200
IMPORTS_OCR_PSM=6
IMPORTS_OCR_WORKERS=2
IMPORTS_MAX_PAGES=20
OMP_THREAD_LIMIT=1

# Archivos
IMPORTS_MAX_UPLOAD_MB=10
UPLOADS_DIR=/srv/gestiq/uploads

# Worker
IMPORTS_RUNNER_MODE=inline  # o 'celery'
IMPORTS_RUNNER_LOCK=8102025
```

### 3. Dependencias del Sistema

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y \
  tesseract-ocr \
  tesseract-ocr-spa \
  tesseract-ocr-eng \
  libtesseract-dev \
  libmagic1 \
  redis-server \
  postgresql-client

# Python packages
pip install \
  pytesseract \
  pdf2image \
  openpyxl \
  python-magic \
  pillow \
  pillow-heif  # soporte HEIC/HEIF (fotos de iPhone)
```

---

## 📦 Deployment Steps

### 1. Verificar Instalación

```bash
# Test Tesseract
tesseract --version
tesseract --list-langs  # Debe mostrar: spa, eng

# Test Redis
redis-cli ping  # Debe responder: PONG

# Test Base de datos
psql $DATABASE_URL -c "SELECT version();"
```

### 2. Copiar Archivos

```bash
# Backend
cd /srv/gestiq
git pull origin main

# O copiar archivos manualmente
cp -r apps/backend/app/modules/imports/* /srv/gestiq/app/modules/imports/
```

### 3. Ejecutar Migraciones (si es necesario)

```bash
cd /srv/gestiq
source venv/bin/activate

# Verificar migraciones pendientes
alembic current
alembic history

# Ejecutar migraciones
alembic upgrade head
```

### 4. Reiniciar Servicios

```bash
# API
sudo systemctl restart gestiq-api

# Worker (si usas runner)
sudo systemctl restart gestiq-runner

# O Celery
sudo systemctl restart gestiq-worker

# Verificar estado
sudo systemctl status gestiq-api
sudo systemctl status gestiq-runner  # o gestiq-worker
```

---

## 🧪 Verificación Post-Deployment

### 1. Health Check API

```bash
curl http://localhost:8000/health
# Debe responder: {"status": "healthy"}

curl http://localhost:8000/api/v1/imports/health
# Debe responder: {"imports": "enabled"}
```

### 2. Test de Importación Simple

```bash
# Crear batch de prueba
TOKEN="your-jwt-token"
TENANT_ID="your-tenant-uuid"

curl -X POST "http://localhost:8000/api/v1/imports/batches" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "products",
    "origin": "test"
  }'

# Debería responder con batch ID
```

### 3. Test OCR (si aplica)

```bash
# Crear archivo de prueba simple
echo "Test Receipt
Date: 2024-11-05
Total: $50.00" > /tmp/test_receipt.txt

# Convertir a imagen simple
convert -size 800x600 xc:white \
  -font Arial -pointsize 20 \
  -draw "text 50,100 'Test Receipt'" \
  -draw "text 50,150 'Date: 2024-11-05'" \
  -draw "text 50,200 'Total: \$50.00'" \
  /tmp/test_receipt.png

# Subir
curl -X POST "http://localhost:8000/api/v1/imports/procesar" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/test_receipt.png"

# Debe responder con job_id
```

---

## 🔧 Configuración Específica por Entorno

### Desarrollo Local

```bash
# .env.development
IMPORTS_ENABLED=1
IMPORTS_RUNNER_MODE=inline
IMPORTS_OCR_WORKERS=1
DEBUG=1
```

### Staging

```bash
# .env.staging
IMPORTS_ENABLED=1
IMPORTS_RUNNER_MODE=celery
IMPORTS_OCR_WORKERS=2
CELERY_BROKER_URL=redis://redis-staging:6379/1
```

### Producción

```bash
# .env.production
IMPORTS_ENABLED=1
IMPORTS_RUNNER_MODE=celery
IMPORTS_OCR_WORKERS=4
CELERY_BROKER_URL=redis://redis-prod:6379/1
IMPORTS_MAX_UPLOAD_MB=20
SENTRY_DSN=https://...
```

---

## 📊 Monitoreo

### Logs

```bash
# API logs
tail -f /var/log/gestiq/api.log | grep imports

# Worker logs
tail -f /var/log/gestiq/worker.log

# Systemd journal
journalctl -u gestiq-api -f
journalctl -u gestiq-runner -f
```

### Métricas

```bash
# Verificar batches recientes
psql $DATABASE_URL -c "
SELECT
  source_type,
  status,
  COUNT(*) as count,
  MAX(created_at) as last_import
FROM import_batches
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY source_type, status
ORDER BY source_type, status;
"

# Items promocionados hoy
psql $DATABASE_URL -c "
SELECT COUNT(*) as promoted_today
FROM import_items
WHERE status = 'PROMOTED'
  AND promoted_at::date = CURRENT_DATE;
"
```

---

## 🐛 Troubleshooting

### Error: "IMPORTS_ENABLED not set"

**Solución**:
```bash
# Agregar a .env
echo "IMPORTS_ENABLED=1" >> /etc/gestiq/gestiq.env
sudo systemctl restart gestiq-api
```

### Error: "Tesseract not found"

**Solución**:
```bash
sudo apt-get install tesseract-ocr tesseract-ocr-spa tesseract-ocr-eng
which tesseract  # Verificar instalación
```

### Error: "Worker not processing jobs"

**Solución**:
```bash
# Verificar worker está corriendo
ps aux | grep "job_runner\|celery"

# Verificar cola Redis
redis-cli LLEN imports_pre
redis-cli LRANGE imports_pre 0 5

# Reiniciar worker
sudo systemctl restart gestiq-runner
```

### Error: "Database connection failed"

**Solución**:
```bash
# Verificar DATABASE_URL
echo $DATABASE_URL

# Test conexión directa
psql $DATABASE_URL -c "SELECT 1;"

# Verificar RLS
psql $DATABASE_URL -c "
SELECT tablename, rowsecurity
FROM pg_tables
WHERE tablename LIKE 'import_%';
"
```

---

## 🔒 Seguridad

### 1. Permisos de Archivos

```bash
# Directorio de uploads
sudo mkdir -p /srv/gestiq/uploads
sudo chown www-data:www-data /srv/gestiq/uploads
sudo chmod 750 /srv/gestiq/uploads

# Logs
sudo mkdir -p /var/log/gestiq
sudo chown www-data:www-data /var/log/gestiq
sudo chmod 755 /var/log/gestiq
```

### 2. Variables de Entorno Sensibles

```bash
# NO commitear .env
echo ".env" >> .gitignore

# Usar variables de entorno del sistema
sudo nano /etc/systemd/system/gestiq-api.service
# Agregar:
# EnvironmentFile=/etc/gestiq/gestiq.env
```

### 3. Límites

```bash
# Nginx - límite de upload
# /etc/nginx/sites-available/gestiq
client_max_body_size 20M;

# Gunicorn - timeout
# gestiq-api.service
--timeout 120
```

---

## ⚡ Optimización

### 1. Cache

```bash
# Redis para cache de OCR
CACHE_BACKEND=redis
CACHE_DEFAULT_TIMEOUT=3600
```

### 2. Concurrencia

```bash
# Gunicorn workers (2 * CPU + 1)
--workers 5

# Celery workers
--concurrency 4

# OCR parallel
IMPORTS_OCR_WORKERS=4
```

### 3. Base de Datos

```sql
-- Índices importantes
CREATE INDEX CONCURRENTLY idx_import_items_batch_status
  ON import_items(batch_id, status);

CREATE INDEX CONCURRENTLY idx_import_items_promoted
  ON import_items(promoted_at)
  WHERE status = 'PROMOTED';

CREATE INDEX CONCURRENTLY idx_import_batches_tenant_created
  ON import_batches(tenant_id, created_at DESC);
```

---

## 📋 Checklist de Deployment

Pre-deployment:
- [ ] Backup de base de datos
- [ ] Verificar variables de entorno
- [ ] Test en staging
- [ ] Verificar dependencias instaladas

Deployment:
- [ ] Pull código / Copiar archivos
- [ ] Ejecutar migraciones
- [ ] Reiniciar servicios
- [ ] Verificar logs sin errores

Post-deployment:
- [ ] Health check API
- [ ] Test importación simple
- [ ] Test OCR (si aplica)
- [ ] Verificar métricas
- [ ] Monitorear logs por 10 minutos

Rollback plan:
- [ ] Backup SQL listo para restore
- [ ] Commit anterior identificado
- [ ] Comando rollback preparado: `git checkout <commit>`

---

## 🎉 Deployment Exitoso

Si todos los checks pasan:

```bash
# Verificación final
curl http://localhost:8000/api/v1/imports/batches \
  -H "Authorization: Bearer $TOKEN" | jq

# Debe responder con lista de batches (puede estar vacía)
```

**¡Sistema listo para importar cualquier archivo de `importacion/`!** 🚀

---

**Última actualización**: 2025-11-05
**Versión**: 1.0.0
