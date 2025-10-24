import React from 'react'

const PanelRRHH = React.lazy(() => import('./Panel'))
const VacacionesList = React.lazy(() => import('./VacacionesList'))
const FichajesView = React.lazy(() => import('./FichajesView'))
const NominaView = React.lazy(() => import('./NominaView'))

export const manifest = {
  id: 'rrhh',
  name: 'RRHH',
  version: '1.0.0',
  permissions: ['rrhh.read', 'rrhh.write'],
  routes: [
    { path: '/rrhh', element: PanelRRHH },
    { path: '/rrhh/vacaciones', element: VacacionesList },
    { path: '/rrhh/fichajes', element: FichajesView },
    { path: '/rrhh/nomina', element: NominaView }
  ],
  menu: {
    title: 'RRHH',
    icon: '👷',
    route: '/rrhh',
    order: 60
  }
}
