import React from 'react'

const ProductosList = React.lazy(() => import('./components/ProductosList'))
const KardexView = React.lazy(() => import('./components/KardexView'))
const BodegasList = React.lazy(() => import('./components/BodegasList'))

export const manifest = {
  id: 'inventario',
  name: 'Inventario',
  version: '1.0.0',
  permissions: ['inventario.read', 'inventario.write'],
  routes: [
    { path: '/inventario', element: ProductosList },
    { path: '/inventario/kardex/:productId', element: KardexView },
    { path: '/inventario/bodegas', element: BodegasList }
  ],
  menu: {
    title: 'Inventario',
    icon: '📦',
    route: '/inventario',
    order: 20
  }
}
