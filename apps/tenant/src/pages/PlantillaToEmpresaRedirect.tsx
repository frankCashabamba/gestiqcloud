import React from 'react'
import { Navigate, useParams } from 'react-router-dom'

export default function PlantillaToEmpresaRedirect() {
  const { slug } = useParams()
  if (!slug) return <Navigate to="/" replace />
  return <Navigate to={`/${slug}`} replace />
}
