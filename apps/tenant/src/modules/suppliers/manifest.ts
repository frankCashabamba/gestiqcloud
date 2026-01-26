import { lazy } from 'react'

export const manifest = {
  id: 'suppliers',
  name: 'Suppliers',
  icon: '👥',
  color: '#06B6D4',
  order: 60,
  routes: [
    {
      path: '',
      label: 'Suppliers',
      component: lazy(() => import('./List'))
    }
  ]
}
