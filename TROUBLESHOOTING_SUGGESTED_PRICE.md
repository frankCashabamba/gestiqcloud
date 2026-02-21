# Troubleshooting: Precio Sugerido No Se Muestra

## Síntoma

El formulario de producto muestra sección "Precio Sugerido desde Receta" pero:
- El precio sugerido es siempre **0** o vacío
- El checkbox "Usar Precio Sugerido" no aparece
- La receta calcula el precio correctamente, pero el producto no lo refleja

## Diagnóstico

### Paso 1: Verificar que las Columnas Existen en BD

```sql
-- Ejecutar en tu PostgreSQL
SELECT 
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'products'
AND column_name IN ('suggested_price', 'use_suggested_price');
```

**Esperado**: 2 filas
```
column_name         | data_type | is_nullable
suggested_price     | numeric   | YES
use_suggested_price | boolean   | NO
```

**Si resultado es vacío**: Las columnas NO existen aún

### Paso 2: Aplicar la Migración

Si las columnas no existen:

```bash
# Opción 1: Usando tu script de migración
./apply_migration.sh 2026-02-21_000_add_suggested_price_to_products

# Opción 2: Ejecutar SQL directamente
psql -U your_user -d your_database -f ops/migrations/2026-02-21_000_add_suggested_price_to_products/up.sql

# Opción 3: Con variables de entorno
psql -h localhost -U $DB_USER -d $DB_NAME -f ops/migrations/2026-02-21_000_add_suggested_price_to_products/up.sql
```

**Verificar que funcionó:**
```bash
psql -U your_user -d your_database -c "SELECT suggested_price, use_suggested_price FROM products LIMIT 1;"
```

### Paso 3: Verificar que el Modelo SQLAlchemy Tiene los Campos

```python
# En Python shell o script de test
from app.models.core.products import Product
import inspect

# Ver los atributos del modelo
attrs = [attr for attr in dir(Product) if not attr.startswith('_')]
print('suggested_price' in attrs)  # Debería retornar True
print('use_suggested_price' in attrs)  # Debería retornar True

# O revisar el archivo directamente
# apps/backend/app/models/core/products.py líneas 38-39
```

### Paso 4: Verificar la API

```bash
# Obtener un producto
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/tenant/products/PRODUCT_ID | jq .

# Buscar los campos en la respuesta
# Debería tener: "suggested_price": null/value, "use_suggested_price": false/true
```

## Soluciones

### Solución 1: Ejecutar Migración Faltante

```bash
./apply_migration.sh 2026-02-21_000_add_suggested_price_to_products

# Verificar
psql -c "SELECT column_name FROM information_schema.columns WHERE table_name='products' AND column_name LIKE '%suggested%';"
```

### Solución 2: Verificar Backend está Usando Modelo Actualizado

```bash
# Reiniciar el servicio backend para que cargue el modelo actualizado
systemctl restart gestiqcloud-backend
# o
docker-compose restart backend

# Esperar 5-10 segundos y verificar logs
tail -f /var/log/gestiqcloud/backend.log
```

### Solución 3: Recalcular Precios Sugeridos

```bash
# Script Python para recalcular todos los precios sugeridos
python -c "
from app.config.database import SessionLocal
from app.models.recipes import Recipe
from app.services.recipe_calculator import calculate_recipe_cost

db = SessionLocal()
recipes = db.query(Recipe).filter(Recipe.tenant_id == 'YOUR_TENANT_ID').all()

for recipe in recipes:
    try:
        result = calculate_recipe_cost(db, recipe.id, update_product_price=True)
        print(f'✓ {recipe.name}: suggested_price = {result[\"suggested_price\"]}')
    except Exception as e:
        print(f'✗ {recipe.name}: {str(e)}')

db.close()
"
```

### Solución 4: Verificar Logs

```bash
# Backend logs
tail -100 /var/log/gestiqcloud/backend.log | grep -i "suggested\|price\|error"

# PostgreSQL logs
tail -100 /var/log/postgresql/postgresql.log | grep -i "suggested\|price\|error"

# Docker logs
docker-compose logs backend | grep -i "suggested\|price\|error"
```

## Checklist de Verificación

```
PRE-REQUISITOS
├── [ ] Migración ejecutada (columnas existen en BD)
├── [ ] Código backend actualizado (líneas 38-39 en products.py)
├── [ ] Servicio backend reiniciado
└── [ ] Código frontend actualizado (Form.tsx)

VERIFICACIÓN DE DATOS
├── [ ] Producto tiene una receta asociada
├── [ ] Receta tiene ingredientes con costos
├── [ ] Costo unitario > 0 (costo total / rendimiento)
└── [ ] suggested_price debería ser > 0 en BD

VERIFICACIÓN DE API
├── [ ] GET /products/{id} retorna suggested_price
├── [ ] GET /products/{id} retorna use_suggested_price
├── [ ] PUT /products/{id} acepta use_suggested_price
└── [ ] POST /recipes/{id}/sync-product-price funciona

VERIFICACIÓN DE UI
├── [ ] Sección "Precio Sugerido desde Receta" aparece
├── [ ] Campo muestra un número (no 0 ni vacío)
├── [ ] Checkbox "Usar Precio Sugerido" aparece
└── [ ] Al marcar checkbox, precio se actualiza
```

## Preguntas Frecuentes

### P: ¿Cómo sé que la migración se ejecutó?

```sql
SELECT version, installed_on 
FROM schema_migrations 
WHERE description LIKE '%suggested_price%';

-- O simplemente verificar columnas
\d products
-- Buscar: suggested_price | numeric | | | | | | | |
```

### P: ¿Qué pasa si tengo muchos productos?

La migración solo **agrega las columnas**, no modifica datos existentes. Todos los productos tendrán `suggested_price = NULL` y `use_suggested_price = FALSE` hasta que tengan una receta y se sincronicen.

### P: ¿Cómo forzar la sincronización?

```bash
# Endpoint para sincronizar manualmente
curl -X POST http://localhost:8000/api/v1/tenant/recipes/RECIPE_ID/sync-product-price \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json"

# Response esperado:
# {
#   "success": true,
#   "suggested_price": 0.13,
#   "unit_cost": 0.066,
#   "message": "Precio sugerido sincronizado con el producto"
# }
```

### P: ¿Qué pasa si la receta no tiene `product_id`?

Verifica que la receta está correctamente asociada al producto:

```sql
SELECT id, name, product_id FROM recipes WHERE tenant_id = 'YOUR_TENANT_ID' LIMIT 5;
-- product_id debería NO ser NULL
```

### P: ¿Cómo revertir si algo falla?

```bash
./apply_migration.sh --down 2026-02-21_000_add_suggested_price_to_products

# O manualmente
psql -U your_user -d your_database -f ops/migrations/2026-02-21_000_add_suggested_price_to_products/down.sql
```

## Logs Útiles para Debugging

### Backend Error
```
ERROR: Column "suggested_price" does not exist
→ Solución: Ejecutar migración
```

### SQLAlchemy Error
```
AttributeError: 'Product' object has no attribute 'suggested_price'
→ Solución: Reiniciar backend después de actualizar modelo
```

### API 422 Unprocessable Entity
```
Extra inputs are not permitted
→ Solución: Verificar que ProductOut schema tiene los campos
```

## Testing Final

Después de aplicar todas las soluciones:

```bash
# Test 1: Crear producto sin receta
curl -X POST http://localhost:8000/api/v1/tenant/products \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "TEST PRODUCT",
    "price": 0,
    "stock": 0,
    "unit": "unit"
  }'
# Guardar PRODUCT_ID

# Test 2: Crear receta
curl -X POST http://localhost:8000/api/v1/tenant/recipes \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": "PRODUCT_ID",
    "name": "Test Recipe",
    "yield_qty": 100,
    "ingredients": [...]
  }'
# Guardar RECIPE_ID

# Test 3: Obtener producto (debería tener suggested_price > 0)
curl http://localhost:8000/api/v1/tenant/products/PRODUCT_ID \
  -H "Authorization: Bearer TOKEN" | jq '.suggested_price'

# Esperado: 0.13 (o similar, no 0 ni null)
```

## Resumen

**Si ves 0 o null en suggested_price:**
1. ✓ Ejecuta migración
2. ✓ Reinicia backend
3. ✓ Verifica que producto tiene receta
4. ✓ Verifica que receta tiene ingredientes con costo > 0
5. ✓ Llama a `/sync-product-price` manualmente si es necesario

---

**¿Todavía no funciona?**
- Revisar logs: `tail -f /var/log/gestiqcloud/backend.log`
- Ejecutar: `check_suggested_price_columns.sql`
- Contactar con detalles de los logs
