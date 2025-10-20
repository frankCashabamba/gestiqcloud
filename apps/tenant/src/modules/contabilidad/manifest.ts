import React from 'react'

const PanelContable = React.lazy(() => import('./Panel'))
const LibroDiario = React.lazy(() => import('./components/LibroDiario'))
const PlanContable = React.lazy(() => import('./components/PlanContable'))

export const manifest = {
  id: 'contabilidad',
  name: 'Contabilidad',
  version: '1.0.0',
  permissions: ['contabilidad.read', 'contabilidad.write'],
  routes: [
    { path: '/contabilidad', element: PanelContable },
    { path: '/contabilidad/libro-diario', element: LibroDiario },
    { path: '/contabilidad/plan-contable', element: PlanContable }
  ],
  menu: {
    title: 'Contabilidad',
    icon: '📈',
    route: '/contabilidad',
    order: 25
  }
}
