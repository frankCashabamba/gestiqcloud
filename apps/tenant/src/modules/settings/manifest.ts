import React from 'react'

const GeneralSettings = React.lazy(() => import('./General'))
const BrandingSettings = React.lazy(() => import('./Branding'))
const FiscalSettings = React.lazy(() => import('./Fiscal'))
const LimitsSettings = React.lazy(() => import('./Limites'))
const HorariosSettings = React.lazy(() => import('./Horarios'))

export const manifest = {
  id: 'settings',
  name: 'Configuración',
  version: '1.0.0',
  permissions: ['settings.read', 'settings.write'],
  routes: [
    { path: '/settings/general', element: GeneralSettings },
    { path: '/settings/branding', element: BrandingSettings },
    { path: '/settings/fiscal', element: FiscalSettings },
    { path: '/settings/limits', element: LimitsSettings },
    { path: '/settings/horarios', element: HorariosSettings }
  ],
  menu: {
    title: 'Configuración',
    icon: '⚙️',
    route: '/settings/general',
    order: 65
  }
}
