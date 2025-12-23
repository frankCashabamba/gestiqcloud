# Migración: Seed Business Categories

**Fecha:** 29 Noviembre 2025
**Objetivo:** Insertar datos de ejemplo en tabla `business_categories`

---

## ¿Qué hace?

Inserta 6 categorías de negocio en la BD:
- `retail` - Retail / Tienda
- `services` - Servicios
- `manufacturing` - Manufactura
- `food_beverage` - Alimentos y Bebidas
- `healthcare` - Salud
- `education` - Educación

## ¿Por qué?

**Eliminación de hardcoding:**
- Antes: Categorías hardcodeadas en frontend/backend
- Ahora: Cargadas dinámicamente desde BD vía endpoint `/api/v1/business-categories`

## Archivos relacionados

- `apps/backend/app/routers/business_categories.py` - Nuevo router
- `apps/backend/app/platform/http/router.py` - Registro del router
- PASO 1 completado en eliminación de hardcoding

## Ejecución

```bash
# Ejecutar migración
alembic upgrade head

# Verificar datos
psql -U postgres -d gestiqcloud -c "SELECT code, name FROM business_categories;"
```

## Rollback

```bash
# Revertir migración
alembic downgrade -1
```
