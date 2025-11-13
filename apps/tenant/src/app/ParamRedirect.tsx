import React from 'react'
import { Navigate, useLocation, useParams } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

/**
 * Param-aware redirect that expands route patterns like '/:empresa/clientes'
 * using current URL params or inferred tenant slug. Prevents leaking literal
 * ':empresa' when links are built with placeholders.
 */
export default function ParamRedirect({ to, replace = true }: { to: string; replace?: boolean }) {
  const params = useParams()
  const { pathname } = useLocation()
  const { profile } = useAuth()

  // Infer empresa from (1) route params, (2) auth profile, (3) first path segment
  const inferredEmpresa = (() => {
    if (params.empresa && params.empresa !== ':empresa') return params.empresa
    if (profile?.empresa_slug) return profile.empresa_slug
    const seg = (pathname || '').split('/').filter(Boolean)[0]
    if (seg && seg !== ':empresa') return seg
    return undefined
  })()

  let target = to
  // Replace all ":param" with matching values from params when present
  Object.entries(params).forEach(([k, v]) => {
    if (!v) return
    target = target.replace(new RegExp(`:${k}\\b`, 'g'), encodeURIComponent(v))
  })

  // If still contains ':empresa', try inferred value
  if (/:empresa\b/.test(target) && inferredEmpresa) {
    target = target.replace(/:empresa\b/g, encodeURIComponent(inferredEmpresa))
  }

  return <Navigate to={target} replace={replace} />
}

