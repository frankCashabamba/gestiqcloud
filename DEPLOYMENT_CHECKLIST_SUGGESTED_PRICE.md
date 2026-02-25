# Deployment Checklist: Precio Sugerido desde Receta

## Fase 1: Preparación (Pre-Deploy)

- [ ] Revisar todos los cambios en los archivos modificados
- [ ] Backup de base de datos
- [ ] Revisar logs de migración anterior
- [ ] Confirmar versión de PostgreSQL (compatibilidad con NUMERIC)

## Fase 2: Migración de Base de Datos

- [ ] Verificar archivo: `ops/migrations/2026-02-21_000_add_suggested_price_to_products/up.sql`
- [ ] Ejecutar migración:
  ```bash
  ./apply_migration.sh 2026-02-21_000_add_suggested_price_to_products
  ```
- [ ] Verificar en BD:
  ```sql
  SELECT column_name, data_type
  FROM information_schema.columns
  WHERE table_name = 'products'
  AND column_name IN ('suggested_price', 'use_suggested_price');
  ```
- [ ] Resultado esperado:
  ```
  suggested_price  | numeric
  use_suggested_price | boolean
  ```

## Fase 3: Despliegue Backend

### 3.1 Archivos a Desplegar

- [ ] `apps/backend/app/models/core/products.py` - Actualizado con nuevos campos
- [ ] `apps/backend/app/services/recipe_calculator.py` - Lógica de cálculo actualizada
- [ ] `apps/backend/app/modules/products/interface/http/tenant.py` - Schemas y endpoints
- [ ] `apps/backend/app/modules/production/interface/http/tenant.py` - Nuevo endpoint de sincronización

### 3.2 Instalación

- [ ] Copiar archivos a producción
- [ ] Reiniciar servicio backend:
  ```bash
  systemctl restart gestiqcloud-backend
  # o
  docker-compose restart backend
  ```
- [ ] Verificar logs:
  ```bash
  tail -f /var/log/gestiqcloud/backend.log
  # o
  docker-compose logs -f backend
  ```
- [ ] Esperado: Sin errores de importación

### 3.3 Verificación de Endpoints

- [ ] GET `/api/v1/tenant/products/{id}` retorna `suggested_price` y `use_suggested_price`
- [ ] PUT `/api/v1/tenant/products/{id}` acepta nuevos campos
- [ ] POST `/api/v1/tenant/recipes/{id}/sync-product-price` funciona

**Test rápido con curl:**
```bash
# Obtener producto
curl -H "Authorization: Bearer TOKEN" \
  http://localhost:8000/api/v1/tenant/products/PRODUCT_ID

# Esperado: campos "suggested_price" y "use_suggested_price" presentes
```

## Fase 4: Despliegue Frontend

### 4.1 Archivos a Desplegar

- [ ] `apps/tenant/src/modules/products/Form.tsx` - Nueva sección de precio sugerido

### 4.2 Build y Despliegue

- [ ] Build del frontend:
  ```bash
  npm run build
  # o
  yarn build
  ```
- [ ] Sin errores de compilación
- [ ] Desplegar archivos estáticos
- [ ] Limpiar caché del navegador

### 4.3 Verificación Visual

- [ ] Abrir módulo de Productos
- [ ] Editar un producto con receta
- [ ] Verificar que aparece sección "Precio Sugerido desde Receta"
- [ ] Campo "Precio Sugerido" es readonly
- [ ] Checkbox "Usar Precio Sugerido" funciona
- [ ] Al marcar checkbox, el precio se actualiza

**Si no aparece la sección:**
- Limpiar caché (Ctrl+Shift+R)
- Verificar que el producto tiene una receta asociada
- Revisar consola del navegador (F12)

## Fase 5: Testing Post-Deploy

### 5.1 Test Manual

```bash
# 1. Crear producto
POST /api/v1/tenant/products
{
  "name": "TEST PRODUCT",
  "price": 0.0,
  "stock": 0,
  "unit": "unit"
}
# Guardar ID

# 2. Crear receta con ingredientes
POST /api/v1/tenant/recipes
{
  "product_id": "PRODUCT_ID",
  "name": "Test Recipe",
  "yield_qty": 100,
  "ingredients": [...]
}
# Guardar ID

# 3. Obtener producto actualizado
GET /api/v1/tenant/products/PRODUCT_ID

# Verificar:
# - suggested_price > 0
# - use_suggested_price = false

# 4. Sincronizar precio
POST /api/v1/tenant/recipes/RECIPE_ID/sync-product-price

# Verificar respuesta exitosa

# 5. Aplicar precio sugerido
PUT /api/v1/tenant/products/PRODUCT_ID
{
  "use_suggested_price": true
}

# Verificar: price = suggested_price
```

### 5.2 Test Automatizado

```bash
python test_suggested_price.py
```

Debería mostrar:
```
✓ Producto creado
✓ Receta creada
✓ Sincronización exitosa
✓ Precio sugerido verificado
✓ Precio aplicado correctamente
```

### 5.3 Test de Regresión

- [ ] Crear producto sin receta → Sin "Precio Sugerido"
- [ ] Crear producto con receta → Muestra "Precio Sugerido"
- [ ] Listar productos → No hay cambios en estructura
- [ ] Exportar productos → Nuevos campos presentes
- [ ] Importar productos → Sin errores

## Fase 6: Monitoreo Post-Deploy

### 6.1 Logs

- [ ] Revisar logs de errores en backend:
  ```bash
  grep "error\|Error\|ERROR" /var/log/gestiqcloud/backend.log
  ```
- [ ] Revisar logs de BD:
  ```bash
  # PostgreSQL
  tail -f /var/log/postgresql/postgresql.log
  ```

### 6.2 Performance

- [ ] Query de productos sigue siendo rápido
  ```sql
  EXPLAIN ANALYZE
  SELECT * FROM products WHERE tenant_id = 'XXX' LIMIT 100;
  ```
- [ ] Sin cambios significativos en tiempo de ejecución

### 6.3 Integridad de Datos

```sql
-- Verificar que no hay inconsistencias
SELECT id, name, suggested_price, use_suggested_price, price
FROM products
WHERE suggested_price IS NOT NULL
LIMIT 10;

-- Verificar que se respetan constraints
SELECT COUNT(*) FROM products WHERE use_suggested_price IS NULL;
-- Debería retornar 0
```

## Fase 7: Rollback (Si es necesario)

Si algo falla en producción:

### 7.1 Revertir Migración BD

```bash
# Ejecutar down.sql
./apply_migration.sh --down 2026-02-21_000_add_suggested_price_to_products
```

Esto eliminará las columnas agregadas.

### 7.2 Revertir Código

```bash
# Git rollback
git revert <commit-hash>

# O restaurar versión anterior
git checkout HEAD~1 -- apps/backend/app/models/core/products.py
git checkout HEAD~1 -- apps/backend/app/services/recipe_calculator.py
git checkout HEAD~1 -- apps/backend/app/modules/products/interface/http/tenant.py
git checkout HEAD~1 -- apps/backend/app/modules/production/interface/http/tenant.py
git checkout HEAD~1 -- apps/tenant/src/modules/products/Form.tsx
```

### 7.3 Reiniciar Servicios

```bash
systemctl restart gestiqcloud-backend
systemctl restart gestiqcloud-frontend
```

## Fase 8: Comunicación

- [ ] Notificar al equipo del cambio
- [ ] Documentar en changelog/release notes
- [ ] Actualizar documentación de usuario si es necesario
- [ ] Instruir a QA sobre nuevas características

## Checklist Resumen

```
PRE-DEPLOY
├── [ ] Backup BD
├── [ ] Revisar cambios
└── [ ] Confirmar compatibilidad

MIGRATION
├── [ ] Ejecutar up.sql
└── [ ] Verificar columnas en BD

BACKEND
├── [ ] Desplegar archivos
├── [ ] Reiniciar servicio
├── [ ] Verificar endpoints
└── [ ] Sin errores en logs

FRONTEND
├── [ ] Build sin errores
├── [ ] Desplegar archivos
├── [ ] Verificar sección UI
└── [ ] Sin errores en consola

TESTING
├── [ ] Tests manuales exitosos
├── [ ] Tests automatizados exitosos
├── [ ] Regresión OK
└── [ ] Performance OK

MONITORING
├── [ ] Logs sin errores
├── [ ] Integridad de datos OK
└── [ ] Performance stable

ROLLBACK (Si es necesario)
├── [ ] Down.sql ejecutado
├── [ ] Código revertido
└── [ ] Servicios reiniciados
```

---

## Contactos de Emergencia

- **Backend**: [Devops Email]
- **Frontend**: [Frontend Lead Email]
- **BD**: [DBA Email]
- **Escalation**: [Manager Email]

---

## Recursos

- Documentación técnica: `IMPLEMENTATION_SUMMARY_SUGGESTED_PRICE.md`
- Guía de usuario: `SUGGESTED_PRICE_QUICK_START.md`
- Documentación completa: `SUGGESTED_PRICE_FEATURE.md`
- Script de test: `test_suggested_price.py`
- Migración: `ops/migrations/2026-02-21_000_add_suggested_price_to_products/`

---

**Fecha de Deploy**: [Completar]
**Responsable**: [Completar]
**Resultado**: [ ] Éxito [ ] Rollback [ ] Parcial

**Notas Post-Deploy**:
```
[Agregar notas aquí]
```
