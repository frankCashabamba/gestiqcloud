import { lazy } from 'react'

export const manifest = {
  id: 'proveedores',
  name: 'Proveedores',
  icon: '👥',
  color: '#06B6D4',
  order: 60,
  routes: [
    {
      path: '',
      label: 'Proveedores',
      component: lazy(() => import('./List'))
    }
  ]
}
