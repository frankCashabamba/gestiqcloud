import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import ProtectedRoute from './ProtectedRoute'
import Login from '../pages/Login'
import Dashboard from '../pages/Dashboard'
import SectorStart from '../pages/SectorStart'
import EmpresaLoader from '../pages/EmpresaLoader'
import { OfflineBanner, BuildBadge, UpdatePrompt, OfflineReadyToast } from '@shared/ui'
import Onboarding from '../pages/Onboarding'
import SetPassword from '../pages/SetPassword'
import ErrorPage from '../pages/ErrorPage'
import PlantillaLoader from '../pages/PlantillaLoader'
import PlantillaToEmpresaRedirect from '../pages/PlantillaToEmpresaRedirect'
import Unauthorized from '../pages/Unauthorized'
import ModuleLoader from '../modules/ModuleLoader'
import TenantShell from './TenantShell'

export default function App() {
  return (
    <>
      <Routes>
        <Route element={<ProtectedRoute />}>
          <Route element={<TenantShell />}>
          <Route path='/' element={<SectorStart />} />
          {/* Empresa vanity URL: /:empresa -> load plantilla by sector fetched for empresa */}
          <Route path='/:empresa' element={<EmpresaLoader />} />
          {/* Redirect old plantilla path under empresa to empresa root */}
          {/* Nota: evitar placeholders literales en 'to'. Usar relative '.' */}
          <Route path='/:empresa/plantilla/:slug' element={<Navigate to='..' replace relative='path' />} />
          <Route path='/:empresa/dashboard' element={<Dashboard />} />
          <Route path='/dashboard' element={<Dashboard />} />
          <Route path='/onboarding' element={<Onboarding />} />
          <Route path='/:empresa/:mod/*' element={<ModuleLoader />} />
          <Route path='/:mod/*' element={<ModuleLoader />} />
          {/* Legacy routes -> redirect to base of the same matched path (strip trailing /*) */}
          <Route path='/contabilidad/*' element={<Navigate to='/contabilidad' replace />} />
          <Route path='/inventario/*' element={<Navigate to='/inventario' replace />} />
          <Route path='/productos' element={<Navigate to='/inventario' replace />} />
          <Route path='/clientes/*' element={<Navigate to='/clientes' replace />} />
          <Route path='/proveedores/*' element={<Navigate to='/proveedores' replace />} />
          <Route path='/ventas/*' element={<Navigate to='/ventas' replace />} />
          <Route path='/compras/*' element={<Navigate to='/compras' replace />} />
          <Route path='/finanzas/*' element={<Navigate to='/finanzas' replace />} />
          <Route path='/facturacion/*' element={<Navigate to='/facturacion' replace />} />
          <Route path='/gastos/*' element={<Navigate to='/gastos' replace />} />
          <Route path='/rrhh/*' element={<Navigate to='/rrhh' replace />} />
          <Route path='/importar/*' element={<Navigate to='/importador' replace />} />
          <Route path='/usuarios/*' element={<Navigate to='/usuarios' replace />} />
          <Route path='/settings/*' element={<Navigate to='/settings' replace />} />
          <Route path='/plantilla/:slug' element={<PlantillaToEmpresaRedirect />} />
          </Route>
        </Route>
        <Route path='/login' element={<Login />} />
        <Route path='/set-password' element={<SetPassword />} />
        <Route path='/error' element={<ErrorPage />} />
        <Route path='/unauthorized' element={<Unauthorized />} />
      </Routes>
      <OfflineBanner />
      <BuildBadge />
      <UpdatePrompt />
      <OfflineReadyToast />
    </>
  )
}

