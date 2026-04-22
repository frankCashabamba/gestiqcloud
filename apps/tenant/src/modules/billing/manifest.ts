import React from 'react'

const InvoicesList = React.lazy(() => import('./List'))
const InvoiceForm = React.lazy(() => import('./Form'))

export const manifest = {
  id: 'billing',
  name: 'Invoicing',
  version: '1.0.0',
  permissions: ['billing.read', 'billing.write', 'billing.einvoice'],
  routes: [
    { path: '/invoicing', element: InvoicesList },
    { path: '/invoicing/new', element: InvoiceForm },
    { path: '/invoicing/:id/edit', element: InvoiceForm }
  ],
  menu: {
    title: 'Invoicing',
    icon: '📄',
    route: '/invoicing',
    order: 15
  }
}
