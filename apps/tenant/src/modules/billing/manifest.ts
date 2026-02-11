import React from 'react'

const FacturasList = React.lazy(() => import('./List'))
const FacturasForm = React.lazy(() => import('./Form'))

export const manifest = {
  id: 'billing',
  name: 'Invoicing',
  version: '1.0.0',
  permissions: ['facturacion.read', 'facturacion.write', 'facturacion.einvoice'],
  routes: [
    { path: '/invoicing', element: FacturasList },
    { path: '/invoicing/new', element: FacturasForm },
    { path: '/invoicing/:id/edit', element: FacturasForm }
  ],
  menu: {
    title: 'Invoicing',
    icon: '📄',
    route: '/invoicing',
    order: 15
  }
}
