import { lazy } from 'react'

export const manifest = {
  id: 'usuarios',
  name: 'Usuarios',
  icon: '👤',
  color: '#6366F1',
  order: 80,
  routes: [
    {
      path: '',
      label: 'Usuarios',
      component: lazy(() => import('./List'))
    }
  ]
}
