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
        { path: '/production', element: RecetasList },
        { path: '/production/recipes', element: RecetasList },
        { path: '/production/orders', element: OrdersList },
        { path: '/production/orders/new', element: OrderForm },
        { path: '/production/orders/:id/edit', element: OrderForm },
        { path: '/production/routes', element: Rutas },
        { path: '/production/routes/new', element: OrderForm },
    ],
    menu: {
        title: 'Producción',
        icon: '🏭',
        route: '/production/recipes',
        order: 50
    }
}
