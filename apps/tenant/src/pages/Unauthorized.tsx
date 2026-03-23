import React from 'react'
import { Navigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../auth/AuthContext'

export default function Unauthorized() {
  const { t } = useTranslation()
  const { token, loading, profile } = useAuth()
  if (loading) return <div className="center">{t('pages.unauthorized.loading')}</div>
  if (!token) return <Navigate to="/login" replace />
  const slug = profile?.empresa_slug
  if (!slug) return <Navigate to="/" replace />
  return <Navigate to={`/${slug}`} replace />
}
