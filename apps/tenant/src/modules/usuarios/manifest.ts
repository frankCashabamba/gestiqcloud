import { lazy } from 'react'

export const manifest = {
  id: 'users',
  name: 'Users',
  icon: '👤',
  color: '#6366F1',
  order: 80,
  routes: [
    {
      path: '',
      label: 'Users',
      component: lazy(() => import('./List'))
    }
  ]
}
