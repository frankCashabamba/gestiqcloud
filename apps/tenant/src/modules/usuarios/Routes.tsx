import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import UsuariosList from './List'
import UsuarioForm from './Form'

export default function UsuariosRoutes() {
  return (
    <Routes>
      <Route index element={<UsuariosList />} />
      <Route path="nuevo" element={<UsuarioForm />} />
      <Route path=":id/editar" element={<UsuarioForm />} />
      <Route path="*" element={<Navigate to="." replace />} />
    </Routes>
  )
}

