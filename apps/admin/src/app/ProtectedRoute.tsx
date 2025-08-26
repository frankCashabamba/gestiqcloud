import React from 'react'
import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

export default function ProtectedRoute() {
  const { token, loading } = useAuth()
  if (loading) return <div className='center'>Cargando…</div>
  if (!token) return <Navigate to='/login' replace />
  return <Outlet />
}
