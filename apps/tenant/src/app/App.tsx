import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import ProtectedRoute from './ProtectedRoute'
import Login from '../pages/Login'
import Dashboard from '../pages/Dashboard'
import SectorStart from '../pages/SectorStart'
import EmpresaLoader from '../pages/EmpresaLoader'
import OfflineBanner from '../components/OfflineBanner'
import BuildBadge from '../components/BuildBadge'
import UpdatePrompt from '../components/UpdatePrompt'
import OfflineReadyToast from '../components/OfflineReadyToast'
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
          <Route path='/:empresa/plantilla/:slug' element={<Navigate to='/:empresa' replace />} />
          <Route path='/:empresa/dashboard' element={<Dashboard />} />
          <Route path='/dashboard' element={<Dashboard />} />
          <Route path='/onboarding' element={<Onboarding />} />
          <Route path='/:empresa/mod/:mod/*' element={<ModuleLoader />} />
          <Route path='/mod/:mod/*' element={<ModuleLoader />} />
          {/* Legacy routes -> redirect to ModuleLoader */}
          <Route path='/:empresa/contabilidad/*' element={<Navigate to='/:empresa/mod/contabilidad' replace />} />
          <Route path='/:empresa/inventario/*' element={<Navigate to='/:empresa/mod/inventario' replace />} />
          <Route path='/:empresa/productos' element={<Navigate to='/:empresa/mod/inventario' replace />} />
          <Route path='/:empresa/clientes/*' element={<Navigate to='/:empresa/mod/clientes' replace />} />
          <Route path='/:empresa/proveedores/*' element={<Navigate to='/:empresa/mod/proveedores' replace />} />
          <Route path='/:empresa/ventas/*' element={<Navigate to='/:empresa/mod/ventas' replace />} />
          <Route path='/:empresa/compras/*' element={<Navigate to='/:empresa/mod/compras' replace />} />
          <Route path='/:empresa/finanzas/*' element={<Navigate to='/:empresa/mod/finanzas' replace />} />
          <Route path='/:empresa/facturacion/*' element={<Navigate to='/:empresa/mod/facturacion' replace />} />
          <Route path='/:empresa/gastos/*' element={<Navigate to='/:empresa/mod/gastos' replace />} />
          <Route path='/:empresa/rrhh/*' element={<Navigate to='/:empresa/mod/rrhh' replace />} />
          <Route path='/:empresa/importar/*' element={<Navigate to='/:empresa/mod/importador' replace />} />
          <Route path='/:empresa/usuarios/*' element={<Navigate to='/:empresa/mod/usuarios' replace />} />
          <Route path='/:empresa/settings/*' element={<Navigate to='/:empresa/mod/settings' replace />} />
          <Route path='/contabilidad/*' element={<Navigate to='/mod/contabilidad' replace />} />
          <Route path='/inventario/*' element={<Navigate to='/mod/inventario' replace />} />
          <Route path='/productos' element={<Navigate to='/mod/inventario' replace />} />
          <Route path='/clientes/*' element={<Navigate to='/mod/clientes' replace />} />
          <Route path='/proveedores/*' element={<Navigate to='/mod/proveedores' replace />} />
          <Route path='/ventas/*' element={<Navigate to='/mod/ventas' replace />} />
          <Route path='/compras/*' element={<Navigate to='/mod/compras' replace />} />
          <Route path='/finanzas/*' element={<Navigate to='/mod/finanzas' replace />} />
          <Route path='/facturacion/*' element={<Navigate to='/mod/facturacion' replace />} />
          <Route path='/gastos/*' element={<Navigate to='/mod/gastos' replace />} />
          <Route path='/rrhh/*' element={<Navigate to='/mod/rrhh' replace />} />
          <Route path='/importar/*' element={<Navigate to='/mod/importador' replace />} />
          <Route path='/usuarios/*' element={<Navigate to='/mod/usuarios' replace />} />
          <Route path='/settings/*' element={<Navigate to='/mod/settings' replace />} />
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
