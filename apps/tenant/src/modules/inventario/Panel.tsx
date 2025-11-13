import React from 'react'
import { Routes, Route, Navigate, Link } from 'react-router-dom'
import ProductosList from './components/ProductosList'
import BodegasList from './components/BodegasList'
import KardexView from './components/KardexView'
import { AlertasConfig } from './components/AlertasConfig'
import AlertConfigManager from './components/AlertConfigManager'

function Index() {
  // Redirigir directo a productos
  return <Navigate to="productos" replace />
}

const PanaderiaProducto = React.lazy(() => import('./components/PanaderiaProducto'))

export default function InventarioPanel() {
  return (
    <Routes>
      <Route index element={<Index />} />
      <Route path="productos" element={<ProductosList />} />
      <Route path="alerts" element={<AlertConfigManager />} />
      <Route path="*" element={<Navigate to="productos" replace />} />
    </Routes>
  )
}
