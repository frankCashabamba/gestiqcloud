import React from 'react'

const ImportadorPanel = React.lazy(() => import('./Panel'))
const Wizard = React.lazy(() => import('./Wizard'))

export const manifest = {
  id: 'imports',
  name: 'Imports',
  version: '1.0.0',
  permissions: ['imports.read', 'imports.write'],
  routes: [
    { path: '/imports', element: ImportadorPanel },
    { path: '/imports/wizard', element: Wizard }
  ],
  menu: {
    title: 'Imports',
    icon: '📤',
    route: '/imports',
    order: 55,
    category: 'tools'
  }
}
