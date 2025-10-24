import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import ClientesList from './List'
import ClienteForm from './Form'

export default function ClientesRoutes() {
  return (
    <Routes>
      <Route index element={<ClientesList />} />
      <Route path="nuevo" element={<ClienteForm />} />
      <Route path=":id/editar" element={<ClienteForm />} />
      <Route path="*" element={<Navigate to="." replace />} />
    </Routes>
  )
}

