// apps/tenant/src/modules/inventario/Routes.tsx
import React from 'react'
import { Route, Routes as RouterRoutes } from 'react-router-dom'
import StockList from './StockListFixed'
import MovimientoForm from './MovementFormBulk'
import AlertConfigManager from './components/AlertConfigManager'

export default function InventarioRoutes() {
return (
<RouterRoutes>
<Route index element={<StockList />} />
  <Route path="movimientos/nuevo" element={<MovimientoForm />} />
    <Route path="alerts" element={<AlertConfigManager />} />
    </RouterRoutes>
  )
}
