import React from 'react'

const TablesView = React.lazy(() => import('./TablesView'))
const KDSView = React.lazy(() => import('./KDSView'))

export const manifest = {
  id: 'restaurant',
  name: 'Restaurante',
  version: '1.0.0',
  enabled: false,
  permissions: [
    'restaurant.read',
    'restaurant.write',
    'restaurant.kds.view',
    'restaurant.kds.manage',
  ],
  routes: [
    { path: '/restaurant', element: TablesView },
    { path: '/restaurant/kds', element: KDSView },
  ],
  menu: {
    title: 'Restaurante',
    icon: '🍽️',
    route: '/restaurant',
    order: 12
  }
}
