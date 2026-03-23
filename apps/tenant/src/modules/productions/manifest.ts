import React from 'react'

const OrdersList = React.lazy(() => import('./OrdersList'))
const OrderForm = React.lazy(() => import('./OrderForm'))
const ProductionPlanner = React.lazy(() => import('./ProductionPlanner'))
const RecetasList = React.lazy(() => import('./RecetasList'))
const Rutas = React.lazy(() => import('./Routes'))

export const manifest = {
    id: 'production',
    name: 'Production',
    version: '1.0.0',
    permissions: ['production.read', 'production.write'],
    routes: [
        { path: '/production', element: RecetasList },
        { path: '/production/recipes', element: RecetasList },
        { path: '/production/planner', element: ProductionPlanner },
        { path: '/production/orders', element: OrdersList },
        { path: '/production/orders/new', element: OrderForm },
        { path: '/production/orders/:id/edit', element: OrderForm },
        { path: '/production/routes', element: Rutas },
        { path: '/production/routes/new', element: OrderForm },
    ],
    menu: {
        title: 'Production',
        icon: '🏭',
        route: '/production/recipes',
        order: 50
    }
}
