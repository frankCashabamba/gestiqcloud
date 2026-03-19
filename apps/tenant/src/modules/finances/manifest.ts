import React from 'react'

const CajaList = React.lazy(() => import('./CajaList'))
const BancoList = React.lazy(() => import('./BancoList'))

export const manifest = {
  id: 'finances',
  name: 'Finance',
  version: '1.0.0',
  permissions: ['finances.read', 'finances.write'],
  routes: [
    { path: '/finance/cash-registers', element: CajaList },
    { path: '/finance/bank-accounts', element: BancoList }
  ],
  menu: {
    title: 'Finance',
    icon: '💰',
    route: '/finance/cash-registers',
    order: 45
  }
}
