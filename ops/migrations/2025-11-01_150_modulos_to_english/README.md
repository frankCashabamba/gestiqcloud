# Migration: Renombrar columnas de modulos_modulo a inglés

**Fecha**: 2025-11-01  
**Tipo**: Schema change (renombrado de columnas)

## Objetivo

Estandarizar nombres de columnas en inglés en la tabla `modulos_modulo` para mantener consistencia con el resto del sistema.

## Cambios

### Tabla: `modulos_modulo`

- `nombre` → `name`
- `descripcion` → `description`
- `activo` → `active`

## Impacto

- **Backend**: Requiere actualizar modelo `Modulo` en `app/models/core/modulo.py`
- **Frontend**: Requiere actualizar interfaces TypeScript que consumen estos datos
- **Schemas**: Los schemas Pydantic ya esperan estos nombres en inglés

## Testing

```bash
# Verificar columnas antes
docker exec db psql -U postgres -d gestiqclouddb_dev -c "\d modulos_modulo"

# Aplicar migración
python scripts/py/bootstrap_imports.py --dir ops/migrations/2025-11-01_150_modulos_to_english

# Verificar columnas después
docker exec db psql -U postgres -d gestiqclouddb_dev -c "\d modulos_modulo"

# Verificar datos
docker exec db psql -U postgres -d gestiqclouddb_dev -c "SELECT id, name, description, active FROM modulos_modulo LIMIT 5;"
```

## Rollback

```bash
# Revertir cambios
docker exec db psql -U postgres -d gestiqclouddb_dev -f /path/to/down.sql
```
