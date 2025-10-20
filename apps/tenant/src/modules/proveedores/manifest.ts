import React from 'react'

const ProveedoresList = React.lazy(() => import('./List'))
const ProveedoresForm = React.lazy(() => import('./Form'))

export const manifest = {
  id: 'proveedores',
  name: 'Proveedores',
  version: '1.0.0',
  permissions: ['proveedores.read', 'proveedores.write'],
  routes: [
    { path: '/proveedores', element: ProveedoresList },
    { path: '/proveedores/nuevo', element: ProveedoresForm },
    { path: '/proveedores/:id/editar', element: ProveedoresForm }
  ],
  menu: {
    title: 'Proveedores',
    icon: '🚚',
    route: '/proveedores',
    order: 40
  }
}
