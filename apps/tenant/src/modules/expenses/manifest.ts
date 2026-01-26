import { lazy } from 'react'

export const manifest = {
  id: 'gastos',
  name: 'Gastos',
  icon: '💵',
  color: '#EF4444',
  order: 70,
  routes: [
    {
      path: '',
      label: 'Gastos',
      component: lazy(() => import('./List'))
    }
  ]
}
