import React, { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import tenantApi from '../shared/api/client'
import { TENANT_AUTH } from '@shared/endpoints'
import { useToast, getErrorMessage } from '../shared/toast'
import { useAuth } from '../auth/AuthContext'
import { resolveTenantPath } from '../lib/tenantNavigation'

export default function SetPassword() {
  const { t } = useTranslation()
  const [sp] = useSearchParams()
  const token = sp.get('token') || ''
  const [pwd, setPwd] = useState('')
  const [pwd2, setPwd2] = useState('')
  const [saving, setSaving] = useState(false)
  const { success, error } = useToast()
  const { login } = useAuth()
  const nav = useNavigate()

  // Preload CSRF cookie so /set-password passes the backend CSRF middleware
  useEffect(() => {
    tenantApi.get(TENANT_AUTH.csrf).catch(() => {})
  }, [])

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault()
    try {
      if (!token) throw new Error(t('pages.setPassword.errors.invalidToken'))
      if (!pwd || pwd.length < 8) throw new Error(t('pages.setPassword.errors.minLength'))
      if (pwd !== pwd2) throw new Error(t('pages.setPassword.errors.mismatch'))
      setSaving(true)
      const { data } = await tenantApi.post(TENANT_AUTH.setPassword, { token, password: pwd })
      const ident = (data?.email || data?.username || '').trim()
      if (!ident) throw new Error(t('pages.setPassword.errors.loginFailed'))
      await login({ identificador: ident, password: pwd })
      success(t('pages.setPassword.success'))
      const target = await resolveTenantPath()
      nav(target)
    } catch (e:any) {
      error(getErrorMessage(e))
    } finally { setSaving(false) }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white p-8 rounded-lg shadow-lg w-full max-w-md">
        <h2 className="text-2xl font-bold mb-4 text-gray-800">{t('pages.setPassword.title')}</h2>
        <form onSubmit={onSubmit} className="space-y-4">
          <input type="password" value={pwd} onChange={(e)=> setPwd(e.target.value)} className="w-full px-3 py-2 border rounded" placeholder={t('pages.setPassword.newPassword')} required />
          <input type="password" value={pwd2} onChange={(e)=> setPwd2(e.target.value)} className="w-full px-3 py-2 border rounded" placeholder={t('pages.setPassword.confirmPassword')} required />
          <button type="submit" disabled={saving} className="bg-blue-600 disabled:opacity-60 text-white px-4 py-2 rounded">{saving ? t('pages.setPassword.saving') : t('pages.setPassword.save')}</button>
        </form>
      </div>
    </div>
  )
}
