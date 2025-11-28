# Datos y migraciones

## Estrategia
- Alembic para cambios incrementales ligados a modelos SQLAlchemy (`apps/backend/alembic`).
- Migraciones SQL manuales para operaciones puntuales o consolidaciones grandes (`ops/migrations`).
- Scripts de soporte en `ops/scripts` para orquestar migraciones idempotentes y generar SQL a partir de modelos.

## Alembic (backend)
- Config: `apps/backend/alembic.ini` y env en `apps/backend/alembic/env.py`.
- Comandos típicos (desde `apps/backend`):
  - `alembic revision -m "mensaje" --autogenerate`
  - `alembic upgrade head`
  - `alembic downgrade -1`
- Recomendaciones: usar autogenerate revisando diffs, nombrar revisiones con prefijo incremental (`00X_descripcion`).

## SQL manual (ops/migrations)
- Ejemplo consolidado: `ops/migrations/2025-11-21_000_complete_consolidated_schema/` con `up.sql` y `down.sql`.
- Útil para snapshots completos o cambios no cubiertos por Alembic.

## Orden sugerido cuando coexisten
1) Ejecutar migraciones SQL manuales si son snapshots/base (p.ej. consolidado).
2) Aplicar Alembic `upgrade head` para los incrementales posteriores.
3) Si se agregan nuevas SQL manuales, registrarlas en los scripts idempotentes.

## Scripts de soporte (ops/scripts)
- `migrate_all_migrations_idempotent.py`: aplica migraciones SQL en orden, saltando las ya aplicadas (requiere `DATABASE_URL`).
- `migrate_all_migrations.py`: versión simple no idempotente.
- `generate_migration_from_models.py`: genera SQL desde modelos actuales para comparar con DB.
- `check_endpoints.py`: smoke test de endpoints FE/BE (usado en CI backend).

## Job de migraciones (Render)
- El botón de UI de migraciones llama al backend para disparar el job de Render configurado en `RENDER_MIGRATE_JOB_ID`.
- Uso actual: manual tras cambios de esquema; en el futuro se podrá automatizar al detectar diffs.
- El estado puede mostrar "Desconocido" y sin historial si nunca se ha disparado; refrescar estado tras ejecutar.

## Rollback y backups
- Antes de aplicar SQL manual, sacar backup (`pg_dump`) del esquema/DB.
  ```bash
  pg_dump "$DATABASE_URL" > backup_$(date +%Y%m%d_%H%M).sql
  ```
- Restaurar (⚠️ sobrescribe):
  ```bash
  psql "$DATABASE_URL" < backup_20250101_1200.sql
  ```
- Para Alembic, usar `downgrade` con cautela y validar compatibilidad con datos.
- Los scripts manuales pueden incluir `down.sql`; úsalo solo en entornos de prueba o con restauración garantizada.

## Checklist post-migración
- Healthchecks OK (`/health`, `/ready`).
- Consultas críticas por módulo (ventas, compras, contabilidad, auth) responden sin errores.
- Validar que tablas clave tienen datos y constraints esperados.
- Revisión de logs de migración y app (errores/tracebacks).
- Si se habilita RLS, probar accesos por tenant y fallos esperados en cross-tenant.

## Pendientes
- Documentar orden recomendado cuando coexistan Alembic y migraciones SQL manuales.
- Añadir checklist de validación post-migración (health checks, consultas críticas, RLS si aplica).
