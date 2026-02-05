// apps/tenant/src/modules/products/Routes.tsx
import React from 'react'
import { Route, Routes as RouterRoutes } from 'react-router-dom'
import ProductosList from './List'
import ProductoForm from './Form'
import ProductosPurge from './actions/PurgeAll'

export default function ProductosRoutes() {
  return (
    <RouterRoutes>
      <Route index element={<ProductosList />} />
      <Route path="purge" element={<ProductosPurge />} />
      <Route path="nuevo" element={<ProductoForm />} />
      <Route path=":id/editar" element={<ProductoForm />} />
    </RouterRoutes>
  )
}
