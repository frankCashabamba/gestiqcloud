import React from 'react'

const ImportadorPanel = React.lazy(() => import('./Panel'))
const Wizard = React.lazy(() => import('./Wizard'))

export const manifest = {
  id: 'importador',
  name: 'Importador',
  version: '1.0.0',
  permissions: ['importador.read', 'importador.write'],
  routes: [
    { path: '/importador', element: ImportadorPanel },
    { path: '/importador/wizard', element: Wizard }
  ],
  menu: {
    title: 'Importador',
    icon: '📤',
    route: '/importador',
    order: 55
  }
}
