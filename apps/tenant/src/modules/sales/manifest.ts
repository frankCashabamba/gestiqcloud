import { lazy } from 'react'

export const manifest = {
  id: 'ventas',
  name: 'Sales',
  icon: '📊',
  color: '#3B82F6',
  order: 40,
  routes: [
    {
      path: '',
      label: 'All',
      component: lazy(() => import('./List'))
    },
    {
      path: 'new',
      label: 'New',
      component: lazy(() => import('./Form'))
    }
  ]
}
