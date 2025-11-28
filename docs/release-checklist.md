# Checklist de release (backend/front + worker)

1) Migraciones
- Aplicar migraciones (Alembic/SQL) antes del deploy o via cron `gestiqcloud-migrate`.
- Backup si hay cambios destructivos (`pg_dump`).

2) Backend (Render)
- Desplegar `gestiqcloud-api` tras migraciones.
- Revisar `/ready` y logs de arranque.

3) Worker CF
- Solo si cambian CORS/cookies/rutas: publicar worker y validar.

4) Frontends (Render static)
- Deploy admin/tenant después de backend si hay cambios de contrato.
- Limpiar caché SW en tenant si cambia `VITE_BASE_PATH` o assets críticos.

5) RLS
- Verificar flags (`RUN_RLS_APPLY`, `RLS_SET_DEFAULT`) y políticas aplicadas; smoke de acceso por tenant.

6) Smoke tests mínimos
- Auth admin y tenant (login + refresh).
- Imports (crear batch + ingest + validate + promote).
- Pagos/e-invoicing (si aplica en la release): intentos sandbox o endpoints de prueba.
- Health: `/health`, `/ready`.

7) Observabilidad
- Revisar métricas/logs tras deploy (errores 5xx, 401/403, imports failed, pagos fallidos, einvoicing errores).

8) Rollback
- Backend: revertir deploy en Render; si migraciones rompieron, restaurar backup.
- Worker: volver a versión previa en CF.
- Frontends: redeploy build anterior.
