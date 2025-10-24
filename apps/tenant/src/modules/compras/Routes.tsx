import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import ComprasList from './List'
import CompraForm from './Form'
import CompraDetail from './Detail'

export default function ComprasRoutes() {
  return (
    <Routes>
      <Route index element={<ComprasList />} />
      <Route path="nueva" element={<CompraForm />} />
      <Route path=":id" element={<CompraDetail />} />
      <Route path=":id/editar" element={<CompraForm />} />
      <Route path="*" element={<Navigate to="." replace />} />
    </Routes>
  )
}
