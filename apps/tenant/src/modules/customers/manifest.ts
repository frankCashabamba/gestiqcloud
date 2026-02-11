import React from 'react'

const ClientesList = React.lazy(() => import('./List'))
const ClientesForm = React.lazy(() => import('./Form'))

export const manifest = {
  id: 'customers',
  name: 'Clientes',
  version: '1.0.0',
  permissions: ['clientes.read', 'clientes.write'],
  routes: [
    { path: '/clients', element: ClientesList },
    { path: '/clients/new', element: ClientesForm },
    { path: '/clients/:id/edit', element: ClientesForm }
  ],
  menu: {
    title: 'Clientes',
    icon: '👥',
    route: '/clients',
    order: 35
  }
}
