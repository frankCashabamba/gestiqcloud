import React from 'react'
import { Routes, Route, Navigate, Link } from 'react-router-dom'
import { ProductosList } from './components/ProductosList'
import { BodegasList } from './components/BodegasList'
import { KardexView } from './components/KardexView'

function Index() {
  return (
    <div style={{ padding: 16 }}>
      <h2>Inventario</h2>
      <ul>
        <li><Link to="productos">Productos</Link></li>
        <li><Link to="bodegas">Bodegas</Link></li>
        <li><Link to="kardex">Kardex</Link></li>
        <li><Link to="panaderia">Producto Panadería</Link></li>
      </ul>
    </div>
  )
}

const PanaderiaProducto = React.lazy(() => import('./components/PanaderiaProducto'))

export default function InventarioPanel() {
  return (
    <Routes>
      <Route index element={<Index />} />
      <Route path="productos" element={<ProductosList />} />
      <Route path="bodegas" element={<BodegasList />} />
      <Route path="kardex" element={<KardexView />} />
      <Route path="panaderia" element={<React.Suspense fallback={<div style={{ padding: 16 }}>Cargando…</div>}><PanaderiaProducto /></React.Suspense>} />
      <Route path="*" element={<Navigate to="." replace />} />
    </Routes>
  )
}
