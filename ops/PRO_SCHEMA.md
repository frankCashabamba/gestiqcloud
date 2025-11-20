# PRO Schema (Single SQL)

Genera un único script SQL con el esquema final (sin legacy) listo para provisionar en PRO.

## Objetivo
- Un archivo `ops/pro_schema.sql` con todas las tablas y objetos en su estado final moderno.
- Evita condicionales legacy (`COALESCE`, columnas ES) y columnas obsoletas.

## Pasos recomendados

1) Arranca DB y aplica todas las migraciones en local/CI

```
docker compose up -d db
DB_DSN=postgresql://postgres:root@localhost:5432/gestiqclouddb_dev \
  python scripts/py/bootstrap_imports.py --dir ops/migrations
```

2) Exporta el esquema consolidado con pg_dump (usa el contenedor `db`)

- En Linux/macOS:

```
bash scripts/pro/export_pro_schema.sh gestiqclouddb_dev db ops/pro_schema.sql
```

- En Windows (PowerShell):

```
./scripts/pro/export_pro_schema.ps1 -Database gestiqclouddb_dev -Container db -Output ops/pro_schema.sql
```

3) Verifica que en `ops/pro_schema.sql` aparecen sólo columnas modernas

- `stock_alerts`: `alert_type`, `current_qty`, `threshold_qty`, `status` (no `nivel_*`, no `diferencia`)
- `stock_items`: `qty_on_hand`
- `stock_moves`: `tenant_id uuid`, `ref_type`, `ref_id`
- POS UUID en `pos_*`

4) Provisiona PRO con el SQL consolidado

```
psql "postgresql://<user>:<pass>@<host>:<port>/<db>" -f ops/pro_schema.sql
```

Notas
- El export requiere que la migración `2025-11-01_231_stock_alerts_modernize_schema` esté aplicada (añadida en este repo).
- Si añades/eliminas tablas, vuelve a exportar para mantener `pro_schema.sql` actualizado.
- El dump no incluye datos (solo esquema). Seeds/series iniciales deben aplicarse aparte.
