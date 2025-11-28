# Paquetes compartidos

Monorepo de paquetes usados por admin y tenant.

## Listado de paquetes
- `ui`: componentes React y guardas (PWA prompts, rutas protegidas, banners offline, permisos).
- `auth-core`: helpers de auth y sesión.
- `http-core`: cliente HTTP configurable.
- `endpoints`: definiciones de endpoints (admin/tenant).
- `api-types`: tipos/contratos de API.
- `utils`: utilidades (permisos, formularios, etc.).
- `shared`: helpers de telemetry/outbox.
- `pwa`: plugin/configuración PWA.
- `telemetry`: capa de telemetría.
- `domain`: lógica de dominio compartida (onboarding, empresa, etc.).
- `assets`, `zod`: assets y esquemas.

## Cómo desarrollar
- Instalar dependencias en cada paquete si aplica; comparten `package-lock.json` en la raíz de cada paquete.
- Ejecutar typecheck/build desde la app consumidora (admin/tenant) para validar cambios.
- Mantener compatibilidad: probar cambios en admin y tenant antes de subir locks.

## Cómo consumir
- Importar vía paths relativos configurados en TS/alias; los paquetes se resuelven dentro de `apps/packages/*`.

## Versionado/dependencias
- Se mantiene por lockfiles (`package-lock.json`); actualizar con cuidado para no romper admin/tenant.
- Preferir cambios pequeños y probar en ambas apps antes de subir lockfiles.

## Tests/typecheck
- Usar typecheck de las apps consumidoras; agregar pruebas unitarias en cada paquete según necesidad.

## Pendientes
- Documentar comandos específicos de build/test por paquete si se añaden scripts dedicados.
