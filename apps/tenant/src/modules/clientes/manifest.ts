import React from 'react'

const ClientesList = React.lazy(() => import('./List'))
const ClientesForm = React.lazy(() => import('./Form'))

export const manifest = {
  id: 'clientes',
  name: 'Clientes',
  version: '1.0.0',
  permissions: ['clientes.read', 'clientes.write'],
  routes: [
    { path: '/clientes', element: ClientesList },
    { path: '/clientes/nuevo', element: ClientesForm },
    { path: '/clientes/:id/editar', element: ClientesForm }
  ],
  menu: {
    title: 'Clientes',
    icon: '👥',
    route: '/clientes',
    order: 35
  }
}
