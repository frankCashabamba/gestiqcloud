import React from 'react'
import { Routes, Route, Outlet, Navigate } from 'react-router-dom'
import ProtectedRoute from './ProtectedRoute'
import Login from '../pages/Login'
import AdminPanel from '../pages/AdminPanel'
import { LayoutAdmin } from '../style/LayoutAdmin'
import { CrearEmpresa } from '../pages/CrearEmpresa'
import { EmpresaPanel } from '../pages/EmpresaPanel'
import ImportarEmpresas from '../pages/ImportarEmpresas'
import ConfiguracionSistema from '../features/configuracion/ConfiguracionSistema'
import ModuleRoutes from '../features/modulos/ModuleRoutes'
import Usuarios from '../pages/Usuarios'
import AsignarNuevoAdmin from '../pages/AsignarNuevoAdmin'
import ErrorPage from '../pages/ErrorPage'
import { EditarEmpresa } from '../pages/EditarEmpresa'
import { EmpresaModulos } from '../pages/EmpresaModulos'

import SessionKeepAlive from '@shared/ui'
import { useAuth } from '../auth/AuthContext'
import { OfflineBanner, BuildBadge, UpdatePrompt, OfflineReadyToast, OutboxIndicator } from '@shared/ui'

const SESSION_WARN_AFTER_MS = 9 * 60_000;
const SESSION_RESPONSE_WINDOW_MS = 60_000;


function LayoutRoute() {
  const useAuthHook = useAuth
  return (
    <LayoutAdmin title="Admin Panel" showBackButton={false}>
      <SessionKeepAlive useAuth={useAuthHook as any} warnAfterMs={SESSION_WARN_AFTER_MS} responseWindowMs={SESSION_RESPONSE_WINDOW_MS} />
      <OfflineBanner />
      <BuildBadge />
      <UpdatePrompt />
      <OfflineReadyToast />
      <OutboxIndicator />
      <Outlet />
    </LayoutAdmin>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/admin" replace />} />

      <Route element={<ProtectedRoute />}>
        <Route path="/admin" element={<LayoutRoute />}>
          <Route index element={<AdminPanel />} />
          <Route path="empresas" element={<EmpresaPanel />} />
          <Route path="empresas/import" element={<ImportarEmpresas />} />
          <Route path="empresas/crear" element={<CrearEmpresa />} />
          <Route path="usuarios" element={<Usuarios />} />
          <Route path="usuarios/:id/asignar-nuevo-admin" element={<AsignarNuevoAdmin />} />
          <Route path="configuracion/*" element={<ConfiguracionSistema />} />
          <Route path="modulos/*" element={<ModuleRoutes />} />
          <Route path="empresas/:id/editar" element={<EditarEmpresa />} />
          <Route path="empresas/modulos/:id" element={<EmpresaModulos />} />
        </Route>
      </Route>

      <Route path="/login" element={<Login />} />
      <Route path="/error" element={<ErrorPage />} />
      <Route path="*" element={<Navigate to="/admin" replace />} />
    </Routes>
  )
}




