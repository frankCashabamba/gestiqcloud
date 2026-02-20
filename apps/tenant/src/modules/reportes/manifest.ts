import { lazy } from 'react'

export const manifest = {
  id: 'reportes',
  name: 'Reportes',
  icon: '📊',
  color: '#0EA5E9',
  order: 55,
  routes: [
    { path: '', label: 'Dashboard', component: lazy(() => import('./ReportsDashboard')) },
    { path: 'ventas', label: 'Ventas', component: lazy(() => import('./SalesReport')) },
    { path: 'inventario', label: 'Inventario', component: lazy(() => import('./InventoryReport')) },
    { path: 'financiero', label: 'Financiero', component: lazy(() => import('./FinancialReport')) },
    { path: 'margenes', label: 'Márgenes', component: lazy(() => import('./MarginsDashboard')) },
  ]
}
