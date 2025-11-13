# Prompts de Continuidad (Admin/Tenant)

Usa estos prompts como base para continuar tareas frecuentes. Copia/pega y ajusta nombres/rutas.

## Inicio Rápido
- Arranque Compose: Ejecuta `scripts/init.ps1 up` y confirma que admin (:8081) y tenant (:8082) cargan.
- Ver logs: Sigue logs de `backend` para depurar CSRF/refresh.

## Migración de Funcionalidades
- Admin/configuración: Migra vistas de idiomas/monedas/sectores/tipos/horarios desde `gestiqcloud-frontend/src/admin/configuracion/*` a `apps/admin/src/features/configuracion/*` manteniendo rutas y reusando `@shared/endpoints` y `@shared/domain`.
- Admin/módulos: Conecta `ModuleManagement` para listar/activar módulos por empresa usando servicios existentes.
- Tenant/contabilidad: Porta `libro-diario`, `libro-mayor`, `conciliación`, `plan-contable` a `apps/tenant/src/modules/contabilidad/*` reusando stores/servicios y `@shared/http`.
- Tenant/inventario: Migra `productos`, `kardex`, `bodegas` a `apps/tenant/src/modules/inventario/*`.

## Servicios y Alias
- Crea servicios: Implementa servicios en Tenant/Admin que llamen a `@shared/domain` con endpoints de `@shared/endpoints` y cliente `@shared/http`.
- Verifica aliases: Asegura `@shared/*` en `tsconfig.json` y `vite.config.ts` de cada app.

## Depuración TS/Build
- Error TS2307 módulo no encontrado: Alinea `paths` en TS y `resolve.alias` en Vite; confirma rutas reales en `apps/packages/*/src`.
- Error react/jsx-runtime: Añade `types: ["react","react-dom","vite/client"]` y referencia en paquetes UI si es necesario.
- Axios tipos: Instala `axios` en la app que consuma `@shared/domain`.

## Docker Compose
- Reconstrucción limpia: `scripts/init.ps1 rebuild`.
- Revisar servicios: `scripts/init.ps1 status` y `scripts/init.ps1 logs admin|tenant|backend`.

## Ejemplos de Prompt
- "Migra la pantalla de Monedas a Admin creando rutas y componentes en `apps/admin/src/features/configuracion/monedas`, conectando servicios a `@shared/endpoints` y mostrando lista/creación/edición." 
- "Crea servicios de contabilidad en Tenant para listar asientos y generar libro mayor usando `tenantApi` y endpoints actuales; renderiza tabla paginada." 
- "Soluciona errores TS en `apps/packages/ui` relacionados con JSX/React types y ajusta exports si faltan." 
- "Verifica CORS/CSRF en backend y ajusta `VITE_API_URL`/`CORS_ORIGINS` para los puertos 8081/8082." 

---
Mantén cambios pequeños y verificables: prueba rutas, typecheck, y revisa logs tras cada paso.
