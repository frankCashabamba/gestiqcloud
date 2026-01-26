import React from 'react'

const SettingsHome = React.lazy(() => import('./SettingsHome'))
const GeneralSettings = React.lazy(() => import('./General'))
const BrandingSettings = React.lazy(() => import('./Branding'))
const FiscalSettings = React.lazy(() => import('./Fiscal'))
const HorariosSettings = React.lazy(() => import('./Horarios'))
const AvanzadoSettings = React.lazy(() => import('./Avanzado'))
const OperativoSettings = React.lazy(() => import('./Operativo'))
const NotificacionesSettings = React.lazy(() => import('./Notificaciones'))
const ModulosSettings = React.lazy(() => import('./ModulosPanel'))

export const manifest = {
  id: 'settings',
  name: 'Configuracion',
  version: '1.1.0',
  permissions: ['settings.read', 'settings.write'],
  routes: [
    { path: '/settings', element: SettingsHome },
    { path: '/settings/general', element: GeneralSettings },
    { path: '/settings/branding', element: BrandingSettings },
    { path: '/settings/fiscal', element: FiscalSettings },
    { path: '/settings/operativo', element: OperativoSettings },
    { path: '/settings/horarios', element: HorariosSettings },
    { path: '/settings/avanzado', element: AvanzadoSettings },
    { path: '/settings/notificaciones', element: NotificacionesSettings },
    { path: '/settings/modules', element: ModulosSettings },
  ],
  menu: {
    title: 'Configuracion',
    icon: 'settings',
    route: '/settings',
    order: 65,
  },
}
