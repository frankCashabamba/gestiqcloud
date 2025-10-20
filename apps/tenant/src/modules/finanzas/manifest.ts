import React from 'react'

const CajaList = React.lazy(() => import('./CajaList'))
const BancoList = React.lazy(() => import('./BancoList'))

export const manifest = {
  id: 'finanzas',
  name: 'Finanzas',
  version: '1.0.0',
  permissions: ['finanzas.read', 'finanzas.write'],
  routes: [
    { path: '/finanzas/caja', element: CajaList },
    { path: '/finanzas/bancos', element: BancoList }
  ],
  menu: {
    title: 'Finanzas',
    icon: '💰',
    route: '/finanzas/caja',
    order: 45
  }
}
