import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import GastosList from './List'
import GastoForm from './Form'

export default function GastosRoutes() {
  return (
    <Routes>
      <Route index element={<GastosList />} />
      <Route path="nuevo" element={<GastoForm />} />
      <Route path=":id/editar" element={<GastoForm />} />
      <Route path="*" element={<Navigate to="." replace />} />
    </Routes>
  )
}

