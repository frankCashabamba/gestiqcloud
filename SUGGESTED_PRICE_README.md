# Precio Sugerido desde Receta - Documentación Completa

## 📋 Contenido

Este documento proporciona una visión general de la implementación. Para detalles específicos, ver:

- **Quick Start**: `SUGGESTED_PRICE_QUICK_START.md` - Cómo usar la feature
- **Implementación**: `IMPLEMENTATION_SUMMARY_SUGGESTED_PRICE.md` - Detalles técnicos
- **Deployment**: `DEPLOYMENT_CHECKLIST_SUGGESTED_PRICE.md` - Checklist de despliegue
- **Feature**: `SUGGESTED_PRICE_FEATURE.md` - Especificación completa

---

## 🎯 Resumen Ejecutivo

### ¿Qué es?

Sistema que calcula automáticamente un **precio de venta sugerido** para productos que tienen una receta asociada.

**Fórmula**: `Precio Sugerido = Costo Unitario × 2`
- Markup: 100%
- Margen: 50%

### ¿Para qué sirve?

- Ayuda a establecer precios basados en costos reales
- Evita pricing manual
- Refleja cambios en costos de ingredientes automáticamente
- Flexible: el usuario puede aplicar o rechazar el precio sugerido

### ¿Quién se beneficia?

- **Panadería/Pastelería**: Precificar productos con recetas
- **Manufacturera**: Calcular costos de producción
- **Restaurantes**: Establecer precios según ingredientes

---

## 🚀 Inicio Rápido

### Para Usuarios

1. **Crear Receta**
   - Ir a: Producción → Recetas
   - Crear nueva receta para un producto
   - Agregar ingredientes con costos
   - El sistema calcula automáticamente

2. **Ver Precio Sugerido**
   - Editar el producto
   - Buscar sección "Precio Sugerido desde Receta"
   - Ver el precio calculado

3. **Aplicar Precio**
   - Marcar checkbox "Usar Precio Sugerido"
   - El precio se actualiza automáticamente
   - Guardar cambios

### Para Desarrolladores

```bash
# 1. Aplicar migración
./apply_migration.sh 2026-02-21_000_add_suggested_price_to_products

# 2. Verificar cambios
python test_suggested_price.py

# 3. Revisar endpoints
curl http://localhost:8000/api/v1/tenant/products/{id}
```

---

## 📊 Ejemplo Real: PAN TAPADO

```
Producto: PAN TAPADO
├─ Receta
│  ├─ Ingredientes:
│  │  ├─ Harina: 50 lb × ($35/110 lb) = $15.91
│  │  ├─ Agua: 25 L × ($0.50/L) = $12.50
│  │  └─ Levadura: 2 kg × ($50/kg) = $100.00
│  │
│  ├─ Costo Total: $14.18
│  ├─ Rendimiento: 216 unidades
│  └─ Costo/Unidad: $0.066
│
└─ Precio Sugerido
   ├─ Cálculo: $0.066 × 2 = $0.13
   ├─ Markup: 100%
   ├─ Margen: 50%
   └─ Aplicar: ☐ Usar Precio Sugerido → Precio = $0.13
```

---

## 🔧 Cambios Técnicos

### Base de Datos

```sql
-- Nuevas columnas en tabla products
ALTER TABLE products ADD COLUMN suggested_price NUMERIC(12, 2);
ALTER TABLE products ADD COLUMN use_suggested_price BOOLEAN DEFAULT FALSE;
```

**Ubicación**: `ops/migrations/2026-02-21_000_add_suggested_price_to_products/`

### Backend

**Archivos modificados**:
1. `apps/backend/app/models/core/products.py` - Modelo
2. `apps/backend/app/services/recipe_calculator.py` - Lógica
3. `apps/backend/app/modules/products/interface/http/tenant.py` - Schemas/Endpoints
4. `apps/backend/app/modules/production/interface/http/tenant.py` - Sincronización

**Nuevos endpoints**:
- `POST /recipes/{id}/sync-product-price` - Sincronizar precio sugerido

### Frontend

**Archivos modificados**:
1. `apps/tenant/src/modules/products/Form.tsx` - Nueva sección UI

**Componentes nuevos**:
- Sección "Precio Sugerido desde Receta"
- Campo readonly para precio sugerido
- Checkbox para aplicar precio

---

## 📈 Flujo de Datos

```
┌─────────────────────────────────────────────────────┐
│ Usuario edita RECETA                               │
├─────────────────────────────────────────────────────┤
│ Backend: calculate_recipe_cost()                   │
├─────────────────────────────────────────────────────┤
│ • Suma costos de ingredientes                      │
│ • Divide por rendimiento → unit_cost               │
│ • Calcula: suggested_price = unit_cost * 2         │
│ • Almacena en tabla products.suggested_price       │
├─────────────────────────────────────────────────────┤
│ Frontend: Editar PRODUCTO                          │
├─────────────────────────────────────────────────────┤
│ • Muestra sección "Precio Sugerido"               │
│ • Display: suggested_price (readonly)             │
│ • Checkbox: "Usar Precio Sugerido"                │
├─────────────────────────────────────────────────────┤
│ Usuario marca checkbox                             │
├─────────────────────────────────────────────────────┤
│ • Frontend: actualiza price = suggested_price      │
│ • Envía PUT /products/{id}                        │
│ • Backend: guarda price y use_suggested_price     │
├─────────────────────────────────────────────────────┤
│ Resultado: Producto usa precio sugerido           │
└─────────────────────────────────────────────────────┘
```

---

## ⚙️ Configuración

### Markup/Margen

**Ubicación**: `apps/backend/app/services/recipe_calculator.py` línea 94

**Actual**:
```python
suggested_price = round(unit_cost * 2, 2)  # 100% markup = 50% margin
```

**Para cambiar a 150% markup (60% margen)**:
```python
suggested_price = round(unit_cost * 2.5, 2)
```

### API Response

El endpoint GET `/products/{id}` retorna:

```json
{
  "id": "uuid",
  "name": "PAN TAPADO",
  "price": 0.13,
  "stock": 216,
  "unit": "unit",
  "suggested_price": 0.13,
  "use_suggested_price": true,
  ...
}
```

---

## 🧪 Testing

### Test Manual

Seguir guía en: `SUGGESTED_PRICE_QUICK_START.md`

### Test Automatizado

```bash
python test_suggested_price.py
```

Expected output:
```
Test 1: Crear Producto con Receta ✓
Test 2: Crear Receta con Ingredientes ✓
Test 3: Sincronizar Precio Sugerido ✓
Test 4: Verificar Producto ✓
Test 5: Aplicar Precio Sugerido ✓
```

---

## 📋 API Reference

### GET /products/{id}

**Response**:
```json
{
  "id": "uuid",
  "name": "string",
  "price": 0.00,
  "suggested_price": 0.00,
  "use_suggested_price": false
}
```

### PUT /products/{id}

**Request**:
```json
{
  "use_suggested_price": true,
  "price": 0.13
}
```

### POST /recipes/{id}/sync-product-price

**Response**:
```json
{
  "success": true,
  "recipe_id": "uuid",
  "suggested_price": 0.13,
  "unit_cost": 0.066,
  "message": "Precio sugerido sincronizado con el producto"
}
```

---

## ⚠️ Notas Importantes

### Limitaciones Conocidas

1. **Margen Fijo**: El markup es fijo en 100% (configurable en código)
2. **Sin Histórico**: No guarda versiones anteriores de precios
3. **Manual**: Require interacción del usuario para aplicar el precio
4. **Solo Productos con Receta**: Si no hay receta, no hay precio sugerido

### Consideraciones de Performance

- Nuevas columnas son nullable (sin impacto en queries existentes)
- Sin índices adicionales por defecto
- Cálculo ocurre solo cuando se modifica receta

### Compatibilidad

- ✅ PostgreSQL 10+
- ✅ SQLAlchemy 1.4+
- ✅ React 18+
- ✅ Sin breaking changes en API existente

---

## 🔄 Rollback

Si es necesario revertir:

```bash
# Ejecutar migración down
./apply_migration.sh --down 2026-02-21_000_add_suggested_price_to_products

# Revertir código
git checkout HEAD~1 -- apps/backend/...
git checkout HEAD~1 -- apps/tenant/...

# Reiniciar servicios
systemctl restart gestiqcloud-backend gestiqcloud-frontend
```

---

## 📞 Soporte

### Errores Comunes

**P: No veo la sección "Precio Sugerido"**
- Verificar que el producto tiene una receta asociada
- Limpiar caché del navegador (Ctrl+Shift+R)
- Verificar que la migración se ejecutó correctamente

**P: El precio no se actualiza**
- Verificar que el checkbox está marcado
- Revisar logs del backend
- Confirmar que `use_suggested_price = true` en BD

**P: El precio sugerido es incorrecto**
- Verificar costos de ingredientes
- Revisar que `yield_qty` es correcto
- Ejecutar `/sync-product-price` manualmente

---

## 📚 Documentación Relacionada

- [Documentación de Recetas](./docs/recipes.md)
- [Documentación de Productos](./docs/products.md)
- [API Documentation](./docs/api.md)
- [Database Schema](./docs/schema.md)

---

## 👥 Historial de Cambios

| Versión | Fecha | Cambios |
|---------|-------|---------|
| 1.0 | 2026-02-21 | Implementación inicial |

---

## 📝 Checklist de Verificación

- [x] Feature implementada
- [x] Tests escritos
- [x] Documentación completa
- [x] Migración creada
- [x] Changelog actualizado
- [ ] Deployed a staging
- [ ] Deployed a producción
- [ ] Monitoreo en marcha

---

**Última actualización**: 2026-02-21  
**Responsable**: Frank Cashabamba  
**Estado**: ✅ Completado y listo para deploy

---

## 🎓 Para Más Información

1. **Usuarios**: Ver `SUGGESTED_PRICE_QUICK_START.md`
2. **Developers**: Ver `IMPLEMENTATION_SUMMARY_SUGGESTED_PRICE.md`
3. **DevOps**: Ver `DEPLOYMENT_CHECKLIST_SUGGESTED_PRICE.md`
4. **Detalle Técnico**: Ver `SUGGESTED_PRICE_FEATURE.md`
