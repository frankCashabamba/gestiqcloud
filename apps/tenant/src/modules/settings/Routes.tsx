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
import BranchesManager from './BranchesManager'
import SubscriptionManager from './SubscriptionManager'
import ReceiptTemplateSettings from './ReceiptTemplateSettings'
import MFASettings from './MFASettings'
import SettingsLayout from './SettingsLayout'
import SettingsHome from './SettingsHome'
import { useSettingsAccess, type SettingsSection } from './useSettingsAccess'
import { useCompanyConfig } from '../../contexts/CompanyConfigContext'
import UsersRoutes from '../users/Routes'
import TemplatesRoutes from '../templates/Routes'
import WebhooksRoutes from '../webhooks/Routes'
import NotificationsRoutes from '../notifications/Routes'
import EinvoicingRoutes from '../einvoicing/Routes'
import ReconciliationRoutes from '../reconciliation/Routes'

function Guard({ section, children }: { section: SettingsSection; children: React.ReactElement }) {
  const { canAccessSection, limitsLoading } = useSettingsAccess()
  if (limitsLoading) return <div className="p-4">Loading permissions...</div>
  if (!canAccessSection(section)) return <Navigate to="." replace />
  return children
}

function ModuleGuard({ moduleKey, children }: { moduleKey: string; children: React.ReactElement }) {
  const { isModuleEnabled, loading } = useCompanyConfig()
  if (loading) return <div className="p-4">Loading module...</div>
  if (!isModuleEnabled(moduleKey)) return <Navigate to="." replace />
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
        <Route path="branches" element={<BranchesManager />} />
        <Route path="subscription" element={<SubscriptionManager />} />
        <Route path="receipt-template" element={<ReceiptTemplateSettings />} />
        <Route path="security" element={<MFASettings />} />
        <Route
          path="users/*"
          element={
            <ModuleGuard moduleKey="users">
              <UsersRoutes />
            </ModuleGuard>
          }
        />
        <Route path="templates/*" element={<TemplatesRoutes />} />
        <Route path="webhooks/*" element={<WebhooksRoutes />} />
        <Route path="notification-center/*" element={<NotificationsRoutes />} />
        <Route
          path="einvoicing/*"
          element={
            <ModuleGuard moduleKey="einvoicing">
              <EinvoicingRoutes />
            </ModuleGuard>
          }
        />
        <Route path="reconciliation/*" element={<ReconciliationRoutes />} />
        <Route path="*" element={<Navigate to="." replace />} />
        </Route>
      </Routes>
    </ProtectedRoute>
  )
}
