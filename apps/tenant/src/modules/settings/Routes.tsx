import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import ProtectedRoute from '../../auth/ProtectedRoute'
import PermissionDenied from '../../components/PermissionDenied'
import GeneralSettings from './General'
import BrandingSettings from './Branding'
import FiscalSettings from './Fiscal'
import HorariosSettings from './Horarios'
import ModulosPanel from './ModulosPanel'
import NotificacionesSettings from './Notificaciones'
import AvanzadoSettings from './Avanzado'
import OperativoSettings from './Operativo'
import SettingsLayout from './SettingsLayout'
import SettingsHome from './SettingsHome'
import { useSettingsAccess, type SettingsSection } from './useSettingsAccess'

function Guard({ section, children }: { section: SettingsSection; children: React.ReactElement }) {
  const { canAccessSection, limitsLoading } = useSettingsAccess()
  if (limitsLoading) return <div className="p-4">Loading permissions...</div>
  if (!canAccessSection(section)) return <Navigate to="." replace />
  return children
}

export default function SettingsRoutes() {
  return (
    <ProtectedRoute
      permission="settings:read"
      fallback={<PermissionDenied permission="settings:read" />}
    >
      <Routes>
        <Route element={<SettingsLayout />}>
        <Route index element={<SettingsHome />} />
        <Route
          path="general"
          element={
            <Guard section="general">
              <GeneralSettings />
            </Guard>
          }
        />
        <Route
          path="branding"
          element={
            <Guard section="branding">
              <BrandingSettings />
            </Guard>
          }
        />
        <Route
          path="fiscal"
          element={
            <Guard section="fiscal">
              <FiscalSettings />
            </Guard>
          }
        />
        <Route
          path="operativo"
          element={
            <Guard section="operativo">
              <OperativoSettings />
            </Guard>
          }
        />
        <Route
          path="horarios"
          element={
            <Guard section="horarios">
              <HorariosSettings />
            </Guard>
          }
        />
        <Route
          path="notificaciones"
          element={
            <Guard section="notificaciones">
              <NotificacionesSettings />
            </Guard>
          }
        />
        <Route
          path="modulos"
          element={
            <Guard section="modulos">
              <ModulosPanel />
            </Guard>
          }
        />
        <Route
          path="avanzado"
          element={
            <Guard section="avanzado">
              <AvanzadoSettings variant="admin" />
            </Guard>
          }
        />
        <Route path="*" element={<Navigate to="." replace />} />
        </Route>
      </Routes>
    </ProtectedRoute>
  )
}
