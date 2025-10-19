/**
 * POS Module Manifest
 */
import React from 'react'

const POSView = React.lazy(() => import('./POSView'))

export const manifest = {
  id: 'pos',
  name: 'Punto de Venta',
  version: '1.0.0',
  permissions: ['pos.read', 'pos.write', 'pos.cashier'],
  routes: [
    { path: '/pos', element: POSView }
  ],
  menu: { 
    title: 'POS', 
    icon: '🛒', 
    route: '/pos', 
    order: 5 
  }
}
