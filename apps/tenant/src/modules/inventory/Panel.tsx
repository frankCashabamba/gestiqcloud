import React from 'react'
import { Routes, Route, Navigate, Link } from 'react-router-dom'
import ProductsList from './components/ProductsList'
import WarehousesList from './components/WarehousesList'
import KardexView from './components/KardexView'
import { AlertasConfig } from './components/AlertasConfig'
import AlertConfigManager from './components/AlertConfigManager'

function Index() {
  // Redirigir directo a productos
  return <Navigate to="products" replace />
}

const PanaderiaProducto = React.lazy(() => import('./components/PanaderiaProducto'))

export default function InventarioPanel() {
  return (
    <Routes>
      <Route index element={<Index />} />
      <Route path="products" element={<ProductsList />} />
      <Route path="alerts" element={<AlertConfigManager />} />
      <Route path="*" element={<Navigate to="products" replace />} />
    </Routes>
  )
}
