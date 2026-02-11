import React from 'react'

const PanelRRHH = React.lazy(() => import('./Panel'))
const VacacionesList = React.lazy(() => import('./VacacionesList'))
const FichajesView = React.lazy(() => import('./FichajesView'))
const NominaView = React.lazy(() => import('./NominaView'))

export const manifest = {
  id: 'hr',
  name: 'HR',
  version: '1.0.0',
  permissions: ['rrhh.read', 'rrhh.write'],
  routes: [
    { path: '/hr', element: PanelRRHH },
    { path: '/hr/vacations', element: VacacionesList },
    { path: '/hr/timekeeping', element: FichajesView },
    { path: '/hr/payroll', element: NominaView }
  ],
  menu: {
    title: 'HR',
    icon: '👷',
    route: '/hr',
    order: 60
  }
}
