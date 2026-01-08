import React from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

export default function Unauthorized() {
  const { token, loading, profile } = useAuth()
  if (loading) return <div className="center">Cargando?</div>
  if (!token) return <Navigate to="/login" replace />
  const slug = profile?.empresa_slug
  if (!slug) return <Navigate to="/login" replace />
  return <Navigate to={`/${slug}`} replace />
}
