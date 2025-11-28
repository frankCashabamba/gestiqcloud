# ADR-0002: SQLite en CI para backend

## Contexto
- CI ejecuta pytest del backend en GitHub Actions.
- No se dispone de Postgres gestionado en CI; se busca velocidad y simplicidad.

## Decisión
- Usar SQLite (`test.db`) en CI, recreado antes de tests:
  - `Base.metadata.create_all` para esquema completo.
  - PYTHONPATH ajustado para resolver imports.
- Config en `.github/workflows/ci.yml` establece `DATABASE_URL=sqlite:///./test.db` y borra el archivo antes de tests.

## Consecuencias
- Tests deben ser compatibles con SQLite (tipos, constraints, diferencias en JSON/UUID).
- Validar en entornos con Postgres antes de producción; agregar tests específicos si se usan features PG.
- Alembic no se ejecuta en CI; se crea esquema desde modelos.

## Referencias
- `.github/workflows/ci.yml` pasos backend.
- `apps/backend/app/config/database.py` y tests en `app/tests`.
