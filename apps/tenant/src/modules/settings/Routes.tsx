import React, { Suspense, lazy } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import ProtectedRoute from '../../auth/ProtectedRoute'
import PermissionDenied from '../../components/PermissionDenied'
import { useSettingsAccess, type SettingsSection } from './useSettingsAccess'
import { useCompanyConfig } from '../../contexts/CompanyConfigContext'

const GeneralSettings = lazy(() => import('./General'))
const BrandingSettings = lazy(() => import('./Branding'))
const FiscalSettings = lazy(() => import('./Fiscal'))
const HorariosSettings = lazy(() => import('./Horarios'))
const ModulosPanel = lazy(() => import('./ModulosPanel'))
const NotificacionesSettings = lazy(() => import('./Notificaciones'))
const AvanzadoSettings = lazy(() => import('./Avanzado'))
const OperativoSettings = lazy(() => import('./Operativo'))
const BranchesManager = lazy(() => import('./BranchesManager'))
const SubscriptionManager = lazy(() => import('./SubscriptionManager'))
const ReceiptTemplateSettings = lazy(() => import('./ReceiptTemplateSettings'))
const MFASettings = lazy(() => import('./MFASettings'))
const SettingsLayout = lazy(() => import('./SettingsLayout'))
const SettingsHome = lazy(() => import('./SettingsHome'))
const UsersRoutes = lazy(() => import('../users/Routes'))
const TemplatesRoutes = lazy(() => import('../templates/Routes'))
const WebhooksRoutes = lazy(() => import('../webhooks/Routes'))
const NotificationsRoutes = lazy(() => import('../notifications/Routes'))
const EinvoicingRoutes = lazy(() => import('../einvoicing/Routes'))
const ReconciliationRoutes = lazy(() => import('../reconciliation/Routes'))

const RouteLoader = () => <div className="p-4">Loading...</div>

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

function LazyElement({ children }: { children: React.ReactElement }) {
  return <Suspense fallback={<RouteLoader />}>{children}</Suspense>
}

export default function SettingsRoutes() {
  return (
    <ProtectedRoute
      permission="settings:read"
      fallback={<PermissionDenied permission="settings:read" />}
    >
      <Routes>
        <Route element={<LazyElement><SettingsLayout /></LazyElement>}>
        <Route index element={<LazyElement><SettingsHome /></LazyElement>} />
        <Route
          path="general"
          element={
            <Guard section="general">
              <LazyElement><GeneralSettings /></LazyElement>
            </Guard>
          }
        />
        <Route
          path="branding"
          element={
            <Guard section="branding">
              <LazyElement><BrandingSettings /></LazyElement>
            </Guard>
          }
        />
        <Route
          path="fiscal"
          element={
            <Guard section="fiscal">
              <LazyElement><FiscalSettings /></LazyElement>
            </Guard>
          }
        />
        <Route
          path="operativo"
          element={
            <Guard section="operativo">
              <LazyElement><OperativoSettings /></LazyElement>
            </Guard>
          }
        />
        <Route
          path="horarios"
          element={
            <Guard section="horarios">
              <LazyElement><HorariosSettings /></LazyElement>
            </Guard>
          }
        />
        <Route
          path="notificaciones"
          element={
            <Guard section="notificaciones">
              <LazyElement><NotificacionesSettings /></LazyElement>
            </Guard>
          }
        />
        <Route
          path="modulos"
          element={
            <Guard section="modulos">
              <LazyElement><ModulosPanel /></LazyElement>
            </Guard>
          }
        />
        <Route
          path="avanzado"
          element={
            <Guard section="avanzado">
              <LazyElement><AvanzadoSettings variant="admin" /></LazyElement>
            </Guard>
          }
        />
        <Route path="branches" element={<LazyElement><BranchesManager /></LazyElement>} />
        <Route path="subscription" element={<LazyElement><SubscriptionManager /></LazyElement>} />
        <Route path="receipt-template" element={<LazyElement><ReceiptTemplateSettings /></LazyElement>} />
        <Route path="security" element={<LazyElement><MFASettings /></LazyElement>} />
        <Route
          path="users/*"
          element={
            <ModuleGuard moduleKey="users">
              <LazyElement><UsersRoutes /></LazyElement>
            </ModuleGuard>
          }
        />
        <Route path="templates/*" element={<LazyElement><TemplatesRoutes /></LazyElement>} />
        <Route path="webhooks/*" element={<LazyElement><WebhooksRoutes /></LazyElement>} />
        <Route path="notification-center/*" element={<LazyElement><NotificationsRoutes /></LazyElement>} />
        <Route
          path="einvoicing/*"
          element={
            <ModuleGuard moduleKey="einvoicing">
              <LazyElement><EinvoicingRoutes /></LazyElement>
            </ModuleGuard>
          }
        />
        <Route path="reconciliation/*" element={<LazyElement><ReconciliationRoutes /></LazyElement>} />
        <Route path="*" element={<Navigate to="." replace />} />
        </Route>
      </Routes>
    </ProtectedRoute>
  )
}
