import React from 'react'

const TablesView = React.lazy(() => import('./TablesView'))

export const manifest = {
  id: 'restaurant',
  name: 'Restaurante',
  version: '1.0.0',
  permissions: ['restaurant.read', 'restaurant.write'],
  routes: [
    { path: '/restaurant', element: TablesView },
  ],
  menu: {
    title: 'Restaurante',
    icon: '🍽️',
    route: '/restaurant',
    order: 12
  }
}
