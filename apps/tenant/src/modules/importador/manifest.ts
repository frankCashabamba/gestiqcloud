import { lazy } from 'react'

export const manifest = {
  id: 'importador',
  name: 'Importador',
  icon: '📥',
  color: '#6366F1',
  order: 80,
  routes: [
    {
      path: '',
      label: 'Importador',
      component: lazy(() => import('./Panel')),
    },
  ],
}
