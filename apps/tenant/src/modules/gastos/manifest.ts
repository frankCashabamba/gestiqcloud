import React from 'react'

const GastosList = React.lazy(() => import('./List'))
const GastosForm = React.lazy(() => import('./Form'))

export const manifest = {
  id: 'gastos',
  name: 'Gastos',
  version: '1.0.0',
  permissions: ['gastos.read', 'gastos.write'],
  routes: [
    { path: '/gastos', element: GastosList },
    { path: '/gastos/nuevo', element: GastosForm },
    { path: '/gastos/:id/editar', element: GastosForm }
  ],
  menu: {
    title: 'Gastos',
    icon: '💸',
    route: '/gastos',
    order: 50
  }
}
