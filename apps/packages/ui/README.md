@shared/ui
=================

Componentes UI compartidos para admin y tenant.

- Import básico
  - Default (SessionKeepAlive): `import SessionKeepAlive from '@shared/ui'`
  - Nombrados: `import { BuildBadge, OfflineBanner, OfflineReadyToast, UpdatePrompt, ProtectedRoute, applyTheme } from '@shared/ui'`

- Componentes disponibles
  - SessionKeepAlive (default y nombrado)
  - BuildBadge
  - OfflineBanner
  - OfflineReadyToast
  - UpdatePrompt
  - ProtectedRoute (default)
  - SecureRoute
  - PermisoGuard
  - withPermiso
  - IdleLogout (default)
  - applyTheme (helper)

Asegúrate de tener los alias configurados en tsconfig y vite:
- `@shared/ui` -> `apps/packages/ui/src`
