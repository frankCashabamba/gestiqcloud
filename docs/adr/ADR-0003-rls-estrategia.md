# ADR-0003: Estrategia RLS (Row-Level Security)

## Contexto
- Multitenancy basado en `tenant_id` en tablas de negocio.
- Flags en deploy (`RUN_RLS_APPLY`, `RLS_SET_DEFAULT`) para preparar políticas.

## Decisión
- Habilitar RLS por tabla con políticas de aislamiento por `tenant_id` (ver `docs/seguridad.md`).
- Aplicación responsable de fijar `app.current_tenant` en la sesión DB para que la política evalúe el tenant.
- Activación gradual por entornos (staging → prod) y por conjuntos de tablas.

## Consecuencias
- Consultas cross-tenant serán bloqueadas; requiere ajustar tests y seeds.
- Necesario middleware/DB session que establezca `app.current_tenant`; sin eso, RLS bloquea accesos.
- Migraciones deben habilitar RLS y políticas de forma idempotente (scripts en deploy/cron para aplicar).

## Estado
- Flags para aplicar RLS presentes en `render.yaml`; confirmar políticas efectivas en DB (staging/prod).

## Referencias
- `docs/seguridad.md` (comandos RLS).
- `render.yaml` (RUN_RLS_APPLY, RLS_SET_DEFAULT, RLS_SCHEMAS).
- Scripts de cron de migración (aplican RLS idempotente).
