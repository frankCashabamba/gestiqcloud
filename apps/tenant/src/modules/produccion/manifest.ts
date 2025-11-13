import React from 'react'

const OrdersList = React.lazy(() => import('./OrdersList'))
const OrderForm = React.lazy(() => import('./OrderForm'))
const RecetasList = React.lazy(() => import('./RecetasList'))
const Rutas = React.lazy(() => import('./Rutas'))

export const manifest = {
    id: 'produccion',
    name: 'Producción',
    version: '1.0.0',
    permissions: ['produccion.read', 'produccion.write'],
    routes: [
        { path: '/produccion', element: RecetasList },
        { path: '/produccion/recetas', element: RecetasList },
        { path: '/produccion/ordenes', element: OrdersList },
        { path: '/produccion/ordenes/nuevo', element: OrderForm },
        { path: '/produccion/ordenes/:id/editar', element: OrderForm },
        { path: '/produccion/rutas', element: Rutas },
        { path: '/produccion/rutas/nuevo', element: OrderForm },
    ],
    menu: {
        title: 'Producción',
        icon: '🏭',
        route: '/produccion/recetas',
        order: 50
    }
}
