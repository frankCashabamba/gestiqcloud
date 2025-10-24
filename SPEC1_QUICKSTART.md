# SPEC-1 Quickstart Guide

## 🚀 Activación Rápida (5 pasos)

### 1. Aplicar Migraciones
```bash
# Desde la raíz del proyecto
python scripts/py/bootstrap_imports.py --dir ops/migrations

# O específicamente la migración SPEC-1
docker exec -it backend python scripts/py/bootstrap_imports.py --dir ops/migrations/2025-10-24_140_spec1_tables
```

### 2. Verificar Tablas Creadas
```bash
docker exec -it db psql -U postgres -d gestiqclouddb_dev
```

```sql
-- Listar tablas SPEC-1
\dt daily_inventory
\dt purchase
\dt milk_record
\dt sale_header
\dt sale_line
\dt uom
\dt uom_conversion
\dt production_order
\dt import_log

-- Verificar seeds UoM
SELECT * FROM uom;
SELECT * FROM uom_conversion;

-- Salir
\q
```

### 3. Reiniciar Backend
```bash
# Para cargar los nuevos routers
docker compose restart backend

# Ver logs para confirmar montaje
docker logs backend | grep "SPEC-1"
docker logs backend | grep "Daily Inventory"
```

Deberías ver:
```
Daily Inventory router mounted at /api/v1/daily-inventory
Purchase router mounted at /api/v1/purchases
Milk Record router mounted at /api/v1/milk-records
SPEC-1 Importer router mounted at /api/v1/imports/spec1
```

### 4. Probar API
```bash
# Health check
curl http://localhost:8000/health

# Obtener tenant_id (reemplaza con tu tenant real)
TENANT_ID="tu-tenant-uuid-aqui"

# Listar inventario diario (vacío inicialmente)
curl "http://localhost:8000/api/v1/daily-inventory/" \
  -H "X-Tenant-ID: $TENANT_ID"

# Ver template del importador
curl "http://localhost:8000/api/v1/imports/spec1/template"
```

### 5. Importar Excel de Ejemplo
```bash
# Usando el archivo 22-10-20251.xlsx
curl -X POST "http://localhost:8000/api/v1/imports/spec1/excel" \
  -H "X-Tenant-ID: $TENANT_ID" \
  -F "file=@22-10-20251.xlsx" \
  -F "simulate_sales=true"
```

Respuesta esperada:
```json
{
  "success": true,
  "filename": "22-10-20251.xlsx",
  "stats": {
    "products_created": 283,
    "daily_inventory_created": 283,
    "sales_created": 283,
    "errors": [],
    "warnings": []
  }
}
```

---

## 📊 Casos de Uso

### Caso 1: Ver Inventario de un Día
```bash
curl "http://localhost:8000/api/v1/daily-inventory/?fecha_desde=2025-10-22&fecha_hasta=2025-10-22" \
  -H "X-Tenant-ID: $TENANT_ID"
```

### Caso 2: Obtener KPIs de Inventario
```bash
curl "http://localhost:8000/api/v1/daily-inventory/stats/summary?fecha_desde=2025-10-01&fecha_hasta=2025-10-31" \
  -H "X-Tenant-ID: $TENANT_ID"
```

Respuesta:
```json
{
  "total_registros": 283,
  "total_ventas_unidades": 1234.5,
  "total_ingresos": 5678.90,
  "registros_con_ajuste": 12,
  "precio_promedio": 4.60
}
```

### Caso 3: Crear Compra Manual
```bash
curl -X POST "http://localhost:8000/api/v1/purchases/" \
  -H "X-Tenant-ID: $TENANT_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "fecha": "2025-10-23",
    "supplier_name": "Proveedor ABC",
    "product_id": "producto-uuid",
    "cantidad": 100,
    "costo_unitario": 2.50,
    "notas": "Compra semanal de harina"
  }'
```

### Caso 4: Registrar Leche del Día
```bash
curl -X POST "http://localhost:8000/api/v1/milk-records/" \
  -H "X-Tenant-ID: $TENANT_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "fecha": "2025-10-23",
    "litros": 150.5,
    "grasa_pct": 3.8,
    "notas": "Entrega matutina"
  }'
```

### Caso 5: Activar Backflush en POS
```bash
# 1. Añadir variable de entorno en .env
echo "BACKFLUSH_ENABLED=1" >> .env

# 2. Reiniciar backend
docker compose restart backend

# 3. Ahora al crear receipts en POS, se consumirá MP automáticamente
```

---

## 🔧 Troubleshooting

### Error: "Tabla daily_inventory no existe"
```bash
# Verificar que la migración se aplicó
docker exec db psql -U postgres -d gestiqclouddb_dev -c "\dt daily_inventory"

# Si no existe, aplicar manualmente
docker exec db psql -U postgres -d gestiqclouddb_dev < ops/migrations/2025-10-24_140_spec1_tables/up.sql
```

### Error: "Router not mounted"
```bash
# Ver logs del backend
docker logs backend | grep -i error

# Verificar imports en Python
docker exec -it backend python -c "from app.routers.spec1_daily_inventory import router; print('OK')"
```

### Error: "X-Tenant-ID required"
```bash
# El middleware RLS requiere tenant_id en header
# Obtener tu tenant_id:
docker exec db psql -U postgres -d gestiqclouddb_dev -c "SELECT id, name FROM tenants;"

# Usar en todos los requests:
-H "X-Tenant-ID: <UUID>"
```

### Excel no importa correctamente
```bash
# Verificar formato del archivo
curl "http://localhost:8000/api/v1/imports/spec1/template"

# Ver logs del importador
docker logs backend | grep "Importando hoja REGISTRO"

# Probar con fecha manual
curl -X POST "http://localhost:8000/api/v1/imports/spec1/excel" \
  -F "file=@archivo.xlsx" \
  -F "fecha_manual=2025-10-22"
```

---

## 📱 Swagger UI

Accede a la documentación interactiva:
```
http://localhost:8000/docs
```

Busca las secciones:
- `daily-inventory`
- `purchases`
- `milk-records`
- `imports-spec1`

Podrás probar todos los endpoints directamente desde el navegador.

---

## 🧪 Tests de Integración

```bash
# Crear script de prueba completo
cat > test_spec1.sh << 'EOF'
#!/bin/bash
set -e

TENANT_ID="tu-tenant-uuid"
BASE_URL="http://localhost:8000/api/v1"

echo "=== Test 1: Health Check ==="
curl -s "$BASE_URL/../health" | jq

echo "\n=== Test 2: Template Info ==="
curl -s "$BASE_URL/imports/spec1/template" | jq

echo "\n=== Test 3: Create Daily Inventory ==="
curl -s -X POST "$BASE_URL/daily-inventory/" \
  -H "X-Tenant-ID: $TENANT_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": "test-product-uuid",
    "fecha": "2025-10-23",
    "stock_inicial": 100,
    "venta_unidades": 30,
    "stock_final": 70,
    "precio_unitario_venta": 5.50
  }' | jq

echo "\n=== Test 4: List Inventory ==="
curl -s "$BASE_URL/daily-inventory/" \
  -H "X-Tenant-ID: $TENANT_ID" | jq

echo "\n=== Test 5: Stats ==="
curl -s "$BASE_URL/daily-inventory/stats/summary" \
  -H "X-Tenant-ID: $TENANT_ID" | jq

echo "\n✅ All tests passed!"
EOF

chmod +x test_spec1.sh
./test_spec1.sh
```

---

## 🎯 Próximos Pasos

1. **Frontend**: Crear módulos React en `apps/tenant/src/modules/spec1/`
2. **Reportes**: Añadir exportación a PDF/Excel de inventarios
3. **Dashboard**: KPIs visuales en panadería.tsx
4. **Backflush**: Integrar en routers POS y Sales
5. **Production Orders**: Implementar flujo completo

---

## 📚 Referencias

- **Documentación completa**: SPEC1_IMPLEMENTATION_SUMMARY.md
- **SPEC original**: spec_1_digitalizacion_de_registro_de_ventas_y_compras_gestiqcloud.md
- **Migraciones**: ops/migrations/2025-10-24_140_spec1_tables/
- **Código fuente**: apps/backend/app/{models,schemas,routers}/spec1/

---

**Versión**: 1.0  
**Fecha**: Enero 2025  
**Soporte**: GestiQCloud Team
