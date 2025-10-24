import React from 'react'

const VentasList = React.lazy(() => import('./List'))
const VentasForm = React.lazy(() => import('./Form'))
const VentasDetail = React.lazy(() => import('./Detail'))

export const manifest = {
  id: 'ventas',
  name: 'Ventas',
  version: '1.0.0',
  permissions: ['ventas.read', 'ventas.write'],
  routes: [
    { path: '/ventas', element: VentasList },
    { path: '/ventas/nueva', element: VentasForm },
    { path: '/ventas/:id', element: VentasDetail },
    { path: '/ventas/:id/editar', element: VentasForm }
  ],
  menu: {
    title: 'Ventas',
    icon: '📊',
    route: '/ventas',
    order: 10
  }
}
