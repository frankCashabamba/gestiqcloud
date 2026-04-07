import React, { Suspense, lazy } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'

const DashboardPage = lazy(() => import('./pages/DashboardPage'))
const ImportsPage = lazy(() => import('./pages/ImportsPage'))
const UploadPage = lazy(() => import('./pages/UploadPage'))
const SalesPage = lazy(() => import('./pages/SalesPage'))
const PurchasesPage = lazy(() => import('./pages/PurchasesPage'))
const StockPage = lazy(() => import('./pages/StockPage'))

const Loader = () => <div className="p-4">Loading...</div>

function Lazy({ children }: { children: React.ReactElement }) {
  return <Suspense fallback={<Loader />}>{children}</Suspense>
}

export default function HistoricalRoutes() {
  return (
    <Routes>
      <Route index element={<Lazy><DashboardPage /></Lazy>} />
      <Route path="imports" element={<Lazy><ImportsPage /></Lazy>} />
      <Route path="upload" element={<Lazy><UploadPage /></Lazy>} />
      <Route path="sales" element={<Lazy><SalesPage /></Lazy>} />
      <Route path="purchases" element={<Lazy><PurchasesPage /></Lazy>} />
      <Route path="stock" element={<Lazy><StockPage /></Lazy>} />
      <Route path="*" element={<Navigate to="." replace />} />
    </Routes>
  )
}
