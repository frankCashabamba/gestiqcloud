import React from 'react'
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import UsuariosList from './List'
import UsuarioForm from './Form'
import { listUsuarios } from './services'

export default function UsuariosRoutes() {
  return (
    <Routes>
      <Route index element={<GuardedList />} />
      <Route path="nuevo" element={<UsuarioForm />} />
      <Route path=":id/editar" element={<UsuarioForm />} />
      <Route path="*" element={<Navigate to="." replace />} />
    </Routes>
  )
}

function GuardedList() {
  return <UsuariosList />
}
