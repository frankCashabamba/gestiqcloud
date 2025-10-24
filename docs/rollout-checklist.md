# Functional Rollout Checklist

1. Infra y dominio API disponibles (Render) con CORS/headers correctos.
2. Migraciones aplicadas (legacy + Alembic) y RLS forzado.
3. Tenancy: `tenants` poblada desde `core_empresa` y GUCs activos (`app.tenant_id`).
4. Ventas + Inventario: flujo pedido→confirm→entrega→factura→post probado.
5. Numeración: `assign_next_number` sin colisiones en concurrencia.
6. PDFs de factura: plantilla base operativa.
7. E‑invoicing: colas Celery, worker y beat (si aplica), envs configurados.
8. Plantillas/Overlays: paquetes seeds asignados a tenants piloto.
9. Copiloto: /ai habilitado por tenant y acciones limitadas.
10. Observabilidad: OTEL habilitable (collector), logs JSON con request_id/tenant/user.
11. Seguridad: rate-limit activo (Redis), HSTS en prod, ALLOWED_HOSTS/COOKIE_*/CORS correctos.
12. Backups: script `ops/scripts/db_backup.sh` ejecutado y restauración verificada en entorno aparte.
13. CI: pipeline de backend verde en main.

