import React, { lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import ParamRedirect from './ParamRedirect'
import ProtectedRoute from './ProtectedRoute'
import { OfflineBanner, BuildBadge, UpdatePrompt, OfflineReadyToast } from '@shared/ui'
import CompanyShell from './CompanyShell'

// Lazy load de páginas para reducir bundle inicial
const Login = lazy(() => import('../pages/Login'))
const Dashboard = lazy(() => import('../pages/Dashboard'))
const SectorStart = lazy(() => import('../pages/SectorStart'))
const EmpresaLoader = lazy(() => import('../pages/EmpresaLoader'))
const Onboarding = lazy(() => import('../pages/Onboarding'))
const SetPassword = lazy(() => import('../pages/SetPassword'))
const ErrorPage = lazy(() => import('../pages/ErrorPage'))
const Unauthorized = lazy(() => import('../pages/Unauthorized'))
const ModuleLoader = lazy(() => import('../modules/ModuleLoader'))

// Fallback de carga
const PageLoader = () => (
  <div style={{
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    height: '100vh',
    fontSize: '1.2rem',
    color: '#666'
  }}>
    Cargando...
  </div>
)

export default function App() {
  return (
    <>
      <Suspense fallback={<PageLoader />}>
        <Routes>
          <Route element={<ProtectedRoute />}>
            <Route element={<CompanyShell />}>
              <Route path='/' element={<SectorStart />} />
              {/* Empresa vanity URL: /:empresa -> load plantilla by sector fetched for empresa */}
              <Route path='/:empresa' element={<EmpresaLoader />} />
              {/* Redirect old plantilla path under empresa to empresa root */}
              <Route path='/:empresa/plantilla/:slug' element={<ParamRedirect to='/:empresa' />} />
              <Route path='/:empresa/dashboard' element={<Dashboard />} />
              <Route path='/dashboard' element={<Dashboard />} />
              <Route path='/onboarding' element={<Onboarding />} />
              {/* Company-scoped module routes only */}
              <Route path='/:empresa/:mod/*' element={<ModuleLoader />} />
              {/* Legacy redirects only when slug changed (avoid loops) */}

              {/* Optional legacy redirects kept minimal to avoid stray paths */}
              {/* <Route path='/plantilla/:slug' element={<PlantillaToEmpresaRedirect />} /> */}
            </Route>
          </Route>
          <Route path='/login' element={<Login />} />
          <Route path='/set-password' element={<SetPassword />} />
          <Route path='/error' element={<ErrorPage />} />
          <Route path='/unauthorized' element={<Unauthorized />} />
        </Routes>
      </Suspense>
      <OfflineBanner />
      <BuildBadge />
      <UpdatePrompt />
      <OfflineReadyToast />
    </>
  )
}
