# Guía de Despliegue: Bulk Pricing

## ✅ Checklist Pre-Despliegue

### Código
- [x] Cambios en `Avanzado.tsx` compilados sin errores
- [x] `BulkPricingService` creado e implementado
- [x] Tests implementados y pasando
- [x] Sin conflictos con código existente

### Base de Datos
- [x] NO requiere migraciones
- [x] Usa `pos_config` JSON existente
- [x] Compatibilidad hacia atrás: 100%

### Documentación
- [x] BULK_PRICING_QUICK_START.md
- [x] BULK_PRICING_SETUP.md
- [x] BULK_PRICING_INTEGRATION.md
- [x] BULK_PRICING_CHANGES.md
- [x] BULK_PRICING_FINAL_SUMMARY.md
- [x] BULK_PRICING_UI_MOCKUP.md
- [x] Este archivo

## 🚀 Pasos de Despliegue

### 1. Backend

```bash
# Copiar archivos
cp apps/backend/app/services/bulk_pricing_service.py \
   apps/backend/app/services/

cp apps/backend/app/tests/test_bulk_pricing_service.py \
   apps/backend/app/tests/

# Ejecutar tests
cd apps/backend
pytest app/tests/test_bulk_pricing_service.py -v

# Resultado esperado: 50+ tests pasando ✓
```

### 2. Frontend

```bash
# Build
cd apps/tenant
npm run build

# Resultado esperado: Sin errores ✓
```

### 3. Testing Completo

```bash
# Backend tests
pytest app/tests/test_bulk_pricing_service.py -v

# Frontend tests (si existen)
npm test

# E2E tests (si es necesario)
# Ir a http://localhost:8082/kusi-panaderia/settings/operativo
# Verificar que la sección de bulk pricing funciona
```

### 4. Despliegue

#### Opción A: Manual
```bash
# Backend
cd apps/backend
python -m pip install -r requirements.txt
python manage.py migrate  # No necesario para bulk pricing

# Frontend
cd apps/tenant
npm install
npm run build
npm run start
```

#### Opción B: Docker (Si aplica)
```bash
docker-compose up -d
# Frontend y backend se desplegarán automáticamente
```

#### Opción C: CI/CD (GitHub Actions, etc.)
```yaml
# Agregar a tu workflow si lo tienes
- name: Test Bulk Pricing
  run: |
    cd apps/backend
    pytest app/tests/test_bulk_pricing_service.py -v
```

## 📋 Verificación Post-Despliegue

### 1. Accesibilidad
- [ ] Ir a http://localhost:8082/kusi-panaderia/settings/operativo
- [ ] Sección "Venta por Cantidad (Panadería)" visible
- [ ] Formulario de agregar producto visible

### 2. Funcionalidad Básica
- [ ] Dropdown de productos carga correctamente
- [ ] Agregar producto funciona
- [ ] Tabla muestra el producto agregado
- [ ] Precio por unidad se calcula correctamente

### 3. Validaciones
- [ ] Error si no selecciona producto
- [ ] Error si cantidad = 0
- [ ] Error si intenta agregar duplicado
- [ ] Mensajes de éxito/error se muestran

### 4. Guardado
- [ ] Hacer clic en "Save configuration"
- [ ] Mensaje de carga aparece
- [ ] Configuración se guarda en DB
- [ ] Recargar página muestra configuración guardada

### 5. Integración Backend
```python
# Test manual en Django shell
from app.services.bulk_pricing_service import BulkPricingService

# Test 1: Buscar config
config = BulkPricingService.get_bulk_config_for_product(
    'prod-1',
    [{'product_id': 'prod-1', 'quantity': 6, 'unit_price': 1.00}]
)
assert config is not None

# Test 2: Calcular precio
result = BulkPricingService.calculate_bulk_price(
    quantity=18,
    bulk_config=config
)
assert result['total_price'] == 3.00

print("✓ Integración backend OK")
```

## 🔍 Rollback Plan

### Si hay problemas

#### Opción 1: Deshabilitar feature (rápido)
```javascript
// En Avanzado.tsx
if (variant !== 'admin') {
    // Comentar esta línea
    // void loadProducts()
}

// Sección de bulk pricing no se mostrará
```

#### Opción 2: Rollback de cambios
```bash
# Git
git revert HEAD~1  # Si es el último commit

# O restaurar archivo anterior
git checkout HEAD~1 -- apps/tenant/src/modules/settings/Avanzado.tsx
```

#### Opción 3: Completo
```bash
# Eliminar archivos nuevos
rm apps/backend/app/services/bulk_pricing_service.py
rm apps/backend/app/tests/test_bulk_pricing_service.py

# Revertir cambios en Avanzado.tsx
git checkout -- apps/tenant/src/modules/settings/Avanzado.tsx

# Redeploy
git push
```

## 📊 Monitoreo

### Logs a revisar

```bash
# Backend
tail -f /var/log/django.log | grep bulk_pricing

# Frontend
tail -f /var/log/node.log | grep Operativo
```

### Métricas importantes
- [ ] Tasa de error: < 1%
- [ ] Tiempo de respuesta al guardar: < 2s
- [ ] Carga de productos: < 1s
- [ ] Tests pasando: 100%

## 🐛 Debugging

### Problema: Los productos no cargan

```python
# Verificar endpoint
GET /api/v1/tenant/products

# Esperado: 200 OK con lista de productos
# Si falla: Revisar API de productos
```

### Problema: Error al guardar

```python
# Verificar esquema en companySettings
GET /api/v1/tenant/company-settings

# Verificar que pos_config existe
# Verificar validación en backend
```

### Problema: Precio calculado incorrectamente

```python
# Test el servicio
from app.services.bulk_pricing_service import BulkPricingService

result = BulkPricingService.calculate_bulk_price(
    quantity=20,
    bulk_config={'quantity': 6, 'unit_price': 1.00}
)
# result['total_price'] debe ser 3.33
```

## 🎯 Criterios de Éxito

- [x] Feature completamente implementada
- [x] Tests 100% pasando
- [x] Documentación completa
- [x] Código formateado
- [x] Sin breaking changes
- [x] Compatible con BD existente
- [x] Interfaz intuitiva
- [x] Validaciones robustas

## 📞 Soporte Post-Despliegue

### Documentos de referencia
1. `BULK_PRICING_QUICK_START.md` - Para usuarios finales
2. `BULK_PRICING_SETUP.md` - Para administradores
3. `BULK_PRICING_INTEGRATION.md` - Para developers
4. `BULK_PRICING_FINAL_SUMMARY.md` - Para tech leads

### Contacto
- Código: Revisar en GitHub
- Bugs: Crear issue con tag `bulk-pricing`
- Preguntas: Revisar documentación primero

---

## Resumen Rápido

| Aspecto | Estado |
|--------|--------|
| Código | ✅ Listo |
| Tests | ✅ Pasando |
| DB | ✅ Compatible |
| Docs | ✅ Completa |
| Rollback | ✅ Planificado |

**Listo para despliegue en producción** 🚀
