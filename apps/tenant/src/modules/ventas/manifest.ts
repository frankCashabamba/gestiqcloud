import { lazy } from 'react'

export const manifest = {
  id: 'ventas',
  name: 'Ventas',
  icon: '📊',
  color: '#3B82F6',
  order: 40,
  routes: [
    {
      path: '',
      label: 'Todas',
      component: lazy(() => import('./List'))
    },
    {
      path: 'nueva',
      label: 'Nueva',
      component: lazy(() => import('./Form'))
    }
  ]
}
