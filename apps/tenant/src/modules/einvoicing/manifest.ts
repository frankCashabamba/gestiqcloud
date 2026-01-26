import { lazy } from 'react'

export const manifest = {
  id: 'einvoicing',
  name: 'Facturación Electrónica',
  icon: '📄',
  color: '#10B981',
  order: 80,
  routes: [
    {
      path: '',
      label: 'Facturación Electrónica',
      component: lazy(() => import('./Placeholder'))
    }
  ]
}
