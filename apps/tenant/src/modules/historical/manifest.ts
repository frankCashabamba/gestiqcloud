import { lazy } from 'react'

export const manifest = {
  id: 'historical',
  name: 'Histórico',
  icon: '📦',
  color: '#8B5CF6',
  order: 85,
  routes: [
    {
      path: '',
      label: 'Dashboard',
      component: lazy(() => import('./pages/DashboardPage')),
    },
    {
      path: 'imports',
      label: 'Imports',
      component: lazy(() => import('./pages/ImportsPage')),
    },
    {
      path: 'upload',
      label: 'Upload',
      component: lazy(() => import('./pages/UploadPage')),
    },
  ],
}
