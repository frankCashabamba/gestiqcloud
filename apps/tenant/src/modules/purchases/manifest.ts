import { lazy } from 'react'

export const manifest = {
  id: 'purchases',
  name: 'Purchases',
  icon: '🛍️',
  color: '#8B5CF6',
  order: 50,
  routes: [
    {
      path: '',
      label: 'Purchases',
      component: lazy(() => import('./List'))
    }
  ]
}
