import React from 'react'
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import ProtectedRoute from '../../auth/ProtectedRoute'
import PermissionDenied from '../../components/PermissionDenied'
import UsuariosList from './List'
import UsuarioForm from './Form'
import { listUsuarios } from './services'

export default function UsuariosRoutes() {
  return (
    <ProtectedRoute
      permission="usuarios:read"
      fallback={<PermissionDenied permission="usuarios:read" />}
    >
      <Routes>
        <Route index element={<GuardedList />} />
        <Route
          path="nuevo"
          element={
            <ProtectedRoute permission="usuarios:create">
              <UsuarioForm />
            </ProtectedRoute>
          }
        />
        <Route
          path=":id/editar"
          element={
            <ProtectedRoute permission="usuarios:update">
              <UsuarioForm />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="." replace />} />
      </Routes>
    </ProtectedRoute>
  )
}

function GuardedList() {
  return <UsuariosList />
}
