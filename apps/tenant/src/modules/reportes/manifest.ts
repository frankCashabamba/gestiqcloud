import { lazy } from 'react'

export const manifest = {
  id: 'reportes',
  name: 'Reportes',
  icon: '📊',
  color: '#0EA5E9',
  order: 55,
  routes: [
    {
      path: '',
      label: 'Margenes',
      component: lazy(() => import('./MarginsDashboard'))
    }
  ]
}
