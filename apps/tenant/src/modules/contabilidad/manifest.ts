import React from 'react'

const PanelContable = React.lazy(() => import('./Panel').then(m => ({ default: (m as any).default || (m as any).Panel })))
const LibroDiario = React.lazy(() => import('./components/LibroDiario').then(m => ({ default: (m as any).default || (m as any).LibroDiario })))
const PlanContable = React.lazy(() => import('./components/PlanContable').then(m => ({ default: (m as any).default || (m as any).PlanContable })))

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
