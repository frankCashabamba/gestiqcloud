import { lazy } from 'react'

export const manifest = {
  id: 'reconciliation',
  name: 'Conciliación',
  icon: '🔄',
  color: '#6366F1',
  order: 85,
  routes: [
    {
      path: '',
      label: 'Conciliación',
      component: lazy(() => import('./Placeholder'))
    }
  ]
}
