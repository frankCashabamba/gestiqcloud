import React from 'react'
import { Routes, Route, Outlet, Navigate } from 'react-router-dom'
import ProtectedRoute from './ProtectedRoute'
import Login from '../pages/Login'
import AdminPanel from '../pages/AdminPanel'
import { LayoutAdmin } from '../style/LayoutAdmin'
import { CrearEmpresa } from '../pages/CreateCompany'
import { EmpresaPanel } from '../pages/CompanyPanel'
import ImportarEmpresas from '../pages/ImportCompanies'
import ConfiguracionSistema from '../features/configuracion/ConfiguracionSistema'
import ModuleRoutes from '../features/modulos/ModuleRoutes'
import Usuarios from '../pages/Users'
import AsignarNuevoAdmin from '../pages/AssignNewAdmin'
import ErrorPage from '../pages/ErrorPage'
import { EditarEmpresa } from '../pages/EditCompany'
import { EmpresaModulos } from '../pages/CompanyModules'
import CompanyConfiguracion from '../pages/CompanyConfiguration'
import { CompanyUsuarios } from '../pages/CompanyUsers'
import Migraciones from '../pages/Migrations'
import LogsViewer from '../pages/LogsViewer'
import IncidenciasPanel from '../pages/IncidentsPanel'
import { SectorConfigAdmin } from '../pages/SectorConfigAdmin'
import CountryPacksRoutes from '../modules/country-packs/Routes'
import { Dashboard } from '../pages/Dashboard'
import { Notifications } from '../pages/Notifications'
import { WebhooksPanel } from '../pages/WebhooksPanel'

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
      <Route path="/" element={<Navigate to="/login" replace />} />

      <Route element={<ProtectedRoute />}>
        <Route path="/admin" element={<LayoutRoute />}>
          <Route index element={<AdminPanel />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="notifications" element={<Notifications />} />
          <Route path="webhooks" element={<WebhooksPanel />} />
          <Route path="companies" element={<EmpresaPanel />} />
          <Route path="companies/import" element={<ImportarEmpresas />} />
          <Route path="companies/create" element={<CrearEmpresa />} />
          <Route path="usuarios" element={<Usuarios />} />
          <Route path="usuarios/:id/asignar-nuevo-admin" element={<AsignarNuevoAdmin />} />
          <Route path="config/*" element={<ConfiguracionSistema />} />
          <Route path="modules/*" element={<ModuleRoutes />} />
          <Route path="companies/:id/edit" element={<EditarEmpresa />} />
          <Route path="companies/modules/:id" element={<EmpresaModulos />} />
          <Route path="companies/:id/config" element={<CompanyConfiguracion />} />
          <Route path="companies/:id/users" element={<CompanyUsuarios />} />
          <Route path="ops/migraciones" element={<Migraciones />} />
           <Route path="logs" element={<LogsViewer />} />
          <Route path="incidencias" element={<IncidenciasPanel />} />
          <Route path="sector-config" element={<SectorConfigAdmin />} />
          <Route path="country-packs/*" element={<CountryPacksRoutes />} />
        </Route>
      </Route>

      <Route path="/login" element={<Login />} />
      <Route path="/error" element={<ErrorPage />} />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}
