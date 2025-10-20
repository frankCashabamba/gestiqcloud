import React from 'react'

const ComprasList = React.lazy(() => import('./List'))
const ComprasForm = React.lazy(() => import('./Form'))
const ComprasDetail = React.lazy(() => import('./Detail'))

export const manifest = {
  id: 'compras',
  name: 'Compras',
  version: '1.0.0',
  permissions: ['compras.read', 'compras.write'],
  routes: [
    { path: '/compras', element: ComprasList },
    { path: '/compras/nueva', element: ComprasForm },
    { path: '/compras/:id', element: ComprasDetail },
    { path: '/compras/:id/editar', element: ComprasForm }
  ],
  menu: {
    title: 'Compras',
    icon: '🛒',
    route: '/compras',
    order: 30
  }
}
