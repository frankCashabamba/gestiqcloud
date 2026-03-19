import React from 'react'

const ClientesList = React.lazy(() => import('./List'))
const ClientesForm = React.lazy(() => import('./Form'))

export const manifest = {
  id: 'customers',
  name: 'Customers',
  version: '1.0.0',
  permissions: ['customers.read', 'customers.write'],
  routes: [
    { path: '/clients', element: ClientesList },
    { path: '/clients/new', element: ClientesForm },
    { path: '/clients/:id/edit', element: ClientesForm }
  ],
  menu: {
    title: 'Customers',
    icon: '👥',
    route: '/clients',
    order: 35
  }
}
