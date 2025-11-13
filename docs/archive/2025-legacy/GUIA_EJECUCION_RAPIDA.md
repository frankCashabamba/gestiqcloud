# 🚀 GUÍA DE EJECUCIÓN RÁPIDA - GESTIQCLOUD MVP

**Fecha:** Noviembre 2025  
**Objetivo:** Levantar y probar el sistema en 30 minutos

---

## ⚡ QUICK START (5 minutos)

### 1. Levantar Stack Completo
```bash
cd c:\Users\pc_cashabamba\Documents\GitHub\proyecto

# Opción A: Stack completo (DB + Backend + Frontend + Workers)
docker compose --profile web --profile worker up -d

# Opción B: Minimal (solo DB + Backend)
docker compose up -d db backend

# Esperar a que esté listo (30-60 segundos)
docker compose ps
```

### 2. Verificar Health
```bash
# Backend health
curl http://localhost:8000/health
# Response: {"status":"ok"}

# Frontend Admin
open http://localhost:8080

# Frontend Tenant
open http://localhost:8081
```

### 3. Acceder a Swagger
```bash
open http://localhost:8000/docs
```

---

## 🧪 TESTING E-FACTURACIÓN (10 minutos)

### 1. Obtener Token JWT
```bash
# Login (admin)
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@gestiqcloud.com",
    "password": "admin123"
  }'

# Response:
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "user": {...}
}

# Guardar token en variable
TOKEN="eyJ0eXAiOiJKV1QiLCJhbGc..."
TENANT_ID="550e8400-e29b-41d4-a716-446655440000"
```

### 2. Crear Factura de Prueba
```bash
# Crear factura
curl -X POST http://localhost:8000/api/v1/facturacion/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: $TENANT_ID" \
  -d '{
    "numero": "001-001-000000001",
    "fecha": "2025-11-02",
    "subtotal": 100.00,
    "iva": 21.00,
    "total": 121.00,
    "estado": "posted",
    "cliente_id": 1
  }'

# Response:
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "numero": "001-001-000000001",
  "fecha": "2025-11-02",
  "total": 121.00,
  ...
}

# Guardar invoice_id
INVOICE_ID="550e8400-e29b-41d4-a716-446655440001"
```

### 3. Enviar a SRI (Ecuador)
```bash
# Enviar factura a SRI
curl -X POST http://localhost:8000/api/v1/einvoicing/send \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: $TENANT_ID" \
  -d '{
    "invoice_id": "'$INVOICE_ID'",
    "country": "EC"
  }'

# Response:
{
  "message": "E-invoice processing initiated",
  "task_id": "abc123def456"
}
```

### 4. Obtener Estado
```bash
# Obtener estado de e-factura
curl http://localhost:8000/api/v1/einvoicing/status/$INVOICE_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: $TENANT_ID"

# Response:
{
  "invoice_id": "550e8400-e29b-41d4-a716-446655440001",
  "status": "authorized",
  "clave_acceso": "1711202401017000001010010010000000011234567891",
  "error_message": null,
  "submitted_at": "2025-11-02T16:30:00Z",
  "created_at": "2025-11-02T16:30:00Z"
}
```

### 5. Enviar a Facturae (España)
```bash
# Enviar factura a Facturae
curl -X POST http://localhost:8000/api/v1/einvoicing/send \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: $TENANT_ID" \
  -d '{
    "invoice_id": "'$INVOICE_ID'",
    "country": "ES"
  }'

# Response:
{
  "message": "E-invoice processing initiated",
  "task_id": "xyz789uvw012"
}
```

---

## 🧪 TESTING POS/TPV (10 minutos)

### 1. Crear Caja (Register)
```bash
curl -X POST http://localhost:8000/api/v1/pos/registers \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: $TENANT_ID" \
  -d '{
    "name": "Caja 1",
    "active": true
  }'

# Response:
{
  "id": "550e8400-e29b-41d4-a716-446655440002",
  "name": "Caja 1",
  "active": true
}

REGISTER_ID="550e8400-e29b-41d4-a716-446655440002"
```

### 2. Abrir Turno (Shift)
```bash
curl -X POST http://localhost:8000/api/v1/pos/shifts \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: $TENANT_ID" \
  -d '{
    "register_id": "'$REGISTER_ID'",
    "opened_by": "'$USER_ID'",
    "opening_float": 100.00
  }'

# Response:
{
  "id": "550e8400-e29b-41d4-a716-446655440003",
  "register_id": "'$REGISTER_ID'",
  "status": "open",
  "opening_float": 100.00
}

SHIFT_ID="550e8400-e29b-41d4-a716-446655440003"
```

### 3. Crear Ticket
```bash
curl -X POST http://localhost:8000/api/v1/pos/receipts \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: $TENANT_ID" \
  -d '{
    "register_id": "'$REGISTER_ID'",
    "shift_id": "'$SHIFT_ID'",
    "number": "001",
    "gross_total": 50.00,
    "tax_total": 10.50,
    "currency": "EUR"
  }'

# Response:
{
  "id": "550e8400-e29b-41d4-a716-446655440004",
  "number": "001",
  "status": "draft",
  "gross_total": 50.00,
  "tax_total": 10.50
}

RECEIPT_ID="550e8400-e29b-41d4-a716-446655440004"
```

### 4. Cobrar Ticket
```bash
curl -X POST http://localhost:8000/api/v1/pos/receipts/$RECEIPT_ID/checkout \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: $TENANT_ID" \
  -d '{
    "method": "cash",
    "amount": 60.50
  }'

# Response:
{
  "id": "'$RECEIPT_ID'",
  "status": "paid",
  "paid_at": "2025-11-02T16:35:00Z"
}
```

### 5. Convertir a Factura
```bash
curl -X POST http://localhost:8000/api/v1/pos/receipts/$RECEIPT_ID/to_invoice \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: $TENANT_ID" \
  -d '{
    "customer": {
      "name": "Cliente Test",
      "tax_id": "12345678A",
      "country": "ES"
    }
  }'

# Response:
{
  "invoice_id": "550e8400-e29b-41d4-a716-446655440005",
  "number": "001-001-000000002",
  "status": "posted"
}
```

### 6. Imprimir Ticket
```bash
# Obtener HTML para imprimir
curl http://localhost:8000/api/v1/pos/receipts/$RECEIPT_ID/print \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: $TENANT_ID"

# Response: HTML completo para imprimir en 58mm
```

---

## 🧪 TESTING PAGOS ONLINE (5 minutos)

### 1. Crear Enlace de Pago (Stripe)
```bash
curl -X POST http://localhost:8000/api/v1/payments/link \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: $TENANT_ID" \
  -d '{
    "invoice_id": "'$INVOICE_ID'",
    "provider": "stripe",
    "amount": 121.00,
    "currency": "EUR"
  }'

# Response:
{
  "payment_link": "https://checkout.stripe.com/pay/cs_test_...",
  "provider": "stripe"
}
```

### 2. Crear Enlace de Pago (Kushki - Ecuador)
```bash
curl -X POST http://localhost:8000/api/v1/payments/link \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: $TENANT_ID" \
  -d '{
    "invoice_id": "'$INVOICE_ID'",
    "provider": "kushki",
    "amount": 121.00,
    "currency": "USD"
  }'

# Response:
{
  "payment_link": "https://checkout.kushkipagos.com/...",
  "provider": "kushki"
}
```

---

## 📊 TESTING IMPORTADOR (5 minutos)

### 1. Subir Archivo Excel
```bash
curl -X POST http://localhost:8000/api/v1/imports/upload \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: $TENANT_ID" \
  -F "file=@Stock-02-11-2025.xlsx" \
  -F "entity_type=products"

# Response:
{
  "batch_id": "550e8400-e29b-41d4-a716-446655440006",
  "total_rows": 283,
  "status": "draft"
}

BATCH_ID="550e8400-e29b-41d4-a716-446655440006"
```

### 2. Validar Batch
```bash
curl -X POST http://localhost:8000/api/v1/imports/batches/$BATCH_ID/validate \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: $TENANT_ID"

# Response:
{
  "batch_id": "'$BATCH_ID'",
  "status": "validated",
  "valid_rows": 227,
  "error_rows": 56
}
```

### 3. Promocionar Batch
```bash
curl -X POST http://localhost:8000/api/v1/imports/batches/$BATCH_ID/promote \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: $TENANT_ID"

# Response:
{
  "batch_id": "'$BATCH_ID'",
  "status": "promoted",
  "promoted_rows": 227
}
```

---

## 🔍 DEBUGGING

### Ver Logs Backend
```bash
docker logs -f backend
```

### Ver Logs Celery
```bash
docker logs -f celery-worker
```

### Acceder a DB
```bash
docker exec -it db psql -U postgres -d gestiqclouddb_dev

# Queries útiles:
SELECT * FROM tenants LIMIT 5;
SELECT * FROM invoices LIMIT 5;
SELECT * FROM sri_submissions LIMIT 5;
SELECT * FROM pos_receipts LIMIT 5;
```

### Ver Redis
```bash
docker exec -it redis redis-cli

# Comandos útiles:
KEYS *
GET celery-task-meta-*
FLUSHDB  # Limpiar (cuidado!)
```

---

## 🛑 PARAR STACK

```bash
# Parar todos los servicios
docker compose down

# Parar y eliminar volúmenes (CUIDADO: borra datos)
docker compose down -v

# Parar solo backend
docker compose stop backend

# Reiniciar backend
docker compose restart backend
```

---

## 📋 CHECKLIST DE VERIFICACIÓN

### Backend
- [ ] Health check OK
- [ ] Swagger accesible
- [ ] Login funciona
- [ ] E-facturación endpoints responden
- [ ] POS endpoints responden
- [ ] Pagos endpoints responden

### Frontend
- [ ] Admin PWA carga
- [ ] Tenant PWA carga
- [ ] Módulo facturación visible
- [ ] Módulo POS visible
- [ ] Módulo importador visible

### Database
- [ ] PostgreSQL corriendo
- [ ] Migraciones aplicadas
- [ ] Tablas creadas
- [ ] RLS policies activas

### Workers
- [ ] Redis corriendo
- [ ] Celery worker corriendo
- [ ] Tasks se ejecutan

---

## 🎯 PRÓXIMOS PASOS

1. ✅ Verificar que todo funciona
2. 📝 Implementar endpoints pagos online
3. 📝 Implementar frontend pagos
4. 📝 Testing completo
5. 📝 Documentación API

---

## 📞 SOPORTE

**Documentación:**
- AGENTS.md - Arquitectura
- README_DEV.md - Desarrollo
- PLAN_ACCION_INMEDIATO.md - Tareas

**Errores comunes:**
- "Connection refused" → Docker no está corriendo
- "Port already in use" → Cambiar puerto en docker-compose.yml
- "Database error" → Esperar a que PostgreSQL inicie

---

**Guía creada:** Noviembre 2025  
**Versión:** 2.0.0  
**Tiempo estimado:** 30 minutos
