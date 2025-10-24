import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import ModuleManagement from './ModuleManagement'
import ModuloForm from './ModuloForm'

export default function ModuleRoutes() {
  return (
    <Routes>
      <Route index element={<ModuleManagement />} />
      <Route path="crear" element={<ModuloForm mode="create" />} />
      <Route path="editar/:id" element={<ModuloForm mode="edit" />} />
      <Route path="*" element={<Navigate to="." replace />} />
    </Routes>
  )
}

