import React from 'react'
import { Navigate, Outlet } from 'react-router-dom'

type UseAuthHook = () => { token: string | null; loading: boolean }

export default function ProtectedRoute({ useAuth }: { useAuth: UseAuthHook }) {
  const { token, loading } = useAuth()
  if (loading) return <div className="center">Cargando…</div>
  return token ? <Outlet /> : <Navigate to="/login" replace />
}
