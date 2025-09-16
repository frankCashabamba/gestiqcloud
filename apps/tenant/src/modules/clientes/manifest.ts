import React from 'react'

export type RouteDef = { path: string; element: React.LazyExoticComponent<any> }
export type ModuleManifest = {
  id: string
  name: string
  version: string
  routes: RouteDef[]
  menu?: { title: string; icon?: string; route: string; order?: number }
  permissions?: string[]
  featureFlags?: string[]
}

const List = React.lazy(() => import('./List'))
const Form = React.lazy(() => import('./Form'))

export const manifest: ModuleManifest = {
  id: 'clientes',
  name: 'Clientes',
  version: '1.0.0',
  permissions: ['clientes.read', 'clientes.write'],
  routes: [
    { path: '/clientes', element: List },
    { path: '/clientes/nuevo', element: Form },
  ],
  menu: { title: 'Clientes', icon: 'users', route: '/clientes', order: 20 },
}

