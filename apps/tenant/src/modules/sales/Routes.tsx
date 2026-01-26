import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import VentasList from './List'
import VentaForm from './Form'
import VentaDetail from './Detail'

export default function VentasRoutes() {
  return (
    <Routes>
      <Route index element={<VentasList />} />
      <Route path="nueva" element={<VentaForm />} />
      <Route path=":id" element={<VentaDetail />} />
      <Route path=":id/editar" element={<VentaForm />} />
      <Route path="*" element={<Navigate to="." replace />} />
    </Routes>
  )
}
