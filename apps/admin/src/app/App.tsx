import React from 'react'
import { Routes, Route, Outlet, Navigate } from 'react-router-dom'
import ProtectedRoute from './ProtectedRoute'
import Login from '../pages/Login'
import AdminPanel from '../pages/AdminPanel'
import { LayoutAdmin } from '../style/LayoutAdmin'
import { CrearEmpresa } from "../pages/CrearEmpresa"
import { EmpresaPanel } from '../pages/EmpresaPanel'

// 👇 importa las páginas que faltan (ajusta rutas reales)
//import { EditarEmpresa } from '../pages/EditarEmpresa'
//import { EmpresaUsuarios } from '../pages/EmpresaUsuarios'
//import { EmpresaModulos } from '../pages/EmpresaModulos'

// 👇 si quieres el aviso de sesión
import SessionKeepAlive from '../components/SessionKeepAlive'

function LayoutRoute() {
  return (
    <LayoutAdmin title="Admin — Panel" showBackButton={false}>
      {/* Aviso de sesión (modo prueba: 1 min + 1 min) */}
      <SessionKeepAlive warnAfterMs={60_000} responseWindowMs={60_000} />
      <Outlet />
    </LayoutAdmin>
  )
}

export default function App() {
  return (
    <Routes>
      {/* redirige raíz -> /admin */}
      <Route path="/" element={<Navigate to="/admin" replace />} />

      <Route element={<ProtectedRoute />}>
        <Route path="/admin" element={<LayoutRoute />}>
          <Route index element={<AdminPanel />} />                          {/* /admin */}
          <Route path="empresas" element={<EmpresaPanel />} />              {/* /admin/empresas */}
          <Route path="empresas/crear" element={<CrearEmpresa />} />        {/* /admin/empresas/crear */}
        {/*  <Route path="empresas/:id/editar" element={<EditarEmpresa />} />   /admin/empresas/:id/editar */}
         {/* <Route path="empresas/:id/usuarios" element={<EmpresaUsuarios />} /> /admin/empresas/:id/usuarios */}
         {/* <Route path="empresas/modulos/:id" element={<EmpresaModulos />} /> /admin/empresas/modulos/:id */}
        </Route>
      </Route>

      <Route path="/login" element={<Login />} />
      {/* fallback por si navegan a una ruta inexistente */}
      <Route path="*" element={<Navigate to="/admin" replace />} />
    </Routes>
  )
}
