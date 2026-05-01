import React from 'react'

const Dashboard = React.lazy(() => import('./Dashboard'))

export const manifest = {
  id: 'analytics',
  name: 'Analítica',
  version: '1.0.0',
  enabled: true,
  permissions: ['analytics.view'],
  routes: [
    { path: '/analytics', element: Dashboard },
  ],
  menu: {
    title: 'Analítica',
    icon: '📊',
    route: '/analytics',
    order: 80,
  },
}

export default manifest
