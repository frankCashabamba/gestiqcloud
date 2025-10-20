import React from 'react'

const FacturasList = React.lazy(() => import('./List'))
const FacturasForm = React.lazy(() => import('./Form'))

export const manifest = {
  id: 'facturacion',
  name: 'Facturación',
  version: '1.0.0',
  permissions: ['facturacion.read', 'facturacion.write', 'facturacion.einvoice'],
  routes: [
    { path: '/facturacion', element: FacturasList },
    { path: '/facturacion/nueva', element: FacturasForm },
    { path: '/facturacion/:id/editar', element: FacturasForm }
  ],
  menu: {
    title: 'Facturación',
    icon: '📄',
    route: '/facturacion',
    order: 15
  }
}
