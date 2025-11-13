import { lazy } from 'react'

export const manifest = {
  id: 'compras',
  name: 'Compras',
  icon: '🛍️',
  color: '#8B5CF6',
  order: 50,
  routes: [
    {
      path: '',
      label: 'Compras',
      component: lazy(() => import('./List'))
    }
  ]
}
