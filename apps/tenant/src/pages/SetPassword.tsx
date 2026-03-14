import React, { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import tenantApi from '../shared/api/client'
import { TENANT_AUTH } from '@shared/endpoints'
import { useToast, getErrorMessage } from '../shared/toast'
import { useAuth } from '../auth/AuthContext'
import { resolveTenantPath } from '../lib/tenantNavigation'

const COMMON_PASSWORDS = new Set([
  '12345678', '123456789', '1234567890', 'password', 'contraseña',
  'qwerty123', 'abc12345', '11111111', '00000000', 'password1',
  'iloveyou', 'admin123', '12341234', 'letmein1',
])

interface PasswordStrength {
  score: number      // 0-4
  label: string
  color: string
  errors: string[]
}

interface SetPasswordResponse {
  email?: string
  username?: string
  requires_onboarding?: boolean
}

function checkStrength(pwd: string): PasswordStrength {
  const errors: string[] = []
  if (pwd.length < 8) errors.push('Mínimo 8 caracteres')
  if (!/[A-Z]/.test(pwd)) errors.push('Al menos una mayúscula')
  if (!/[a-z]/.test(pwd)) errors.push('Al menos una minúscula')
  if (!/[0-9]/.test(pwd)) errors.push('Al menos un número')
  if (!/[^A-Za-z0-9]/.test(pwd)) errors.push('Al menos un símbolo (!@#$%...)')
  if (COMMON_PASSWORDS.has(pwd.toLowerCase())) errors.push('Contraseña demasiado común')

  const score = Math.max(0, 4 - errors.length + (pwd.length >= 12 ? 1 : 0))
  const clamped = Math.min(score, 4) as 0 | 1 | 2 | 3 | 4

  const labels = ['Muy débil', 'Débil', 'Regular', 'Fuerte', 'Muy fuerte']
  const colors = ['bg-red-500', 'bg-orange-400', 'bg-yellow-400', 'bg-blue-500', 'bg-green-500']

  return { score: clamped, label: labels[clamped], color: colors[clamped], errors }
}

export default function SetPassword() {
  const { t } = useTranslation()
  const [sp] = useSearchParams()
  const token = sp.get('token') || ''
  const [pwd, setPwd] = useState('')
  const [pwd2, setPwd2] = useState('')
  const [saving, setSaving] = useState(false)
  const [touched, setTouched] = useState(false)
  const { success, error } = useToast()
  const { login } = useAuth()
  const nav = useNavigate()

  const strength = checkStrength(pwd)
  const isValid = strength.errors.length === 0

  useEffect(() => {
    tenantApi.get(TENANT_AUTH.csrf).catch(() => {})
  }, [])

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault()
    setTouched(true)
    try {
      if (!token) throw new Error(t('pages.setPassword.errors.invalidToken'))
      if (!isValid) throw new Error(strength.errors[0])
      if (pwd !== pwd2) throw new Error(t('pages.setPassword.errors.mismatch'))
      setSaving(true)
      const { data } = await tenantApi.post<SetPasswordResponse>(TENANT_AUTH.setPassword, { token, password: pwd })
      const ident = (data?.email || data?.username || '').trim()
      if (!ident) throw new Error(t('pages.setPassword.errors.loginFailed'))
      await login({ identificador: ident, password: pwd })
      success(t('pages.setPassword.success'))
      const target = data?.requires_onboarding ? '/onboarding' : await resolveTenantPath()
      nav(target)
    } catch (e: any) {
      error(getErrorMessage(e))
    } finally { setSaving(false) }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white p-8 rounded-lg shadow-lg w-full max-w-md">
        <h2 className="text-2xl font-bold mb-4 text-gray-800">{t('pages.setPassword.title')}</h2>
        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <input
              type="password"
              value={pwd}
              onChange={(e) => { setPwd(e.target.value); setTouched(true) }}
              className="w-full px-3 py-2 border rounded"
              placeholder={t('pages.setPassword.newPassword')}
              required
            />

            {/* Barra de fortaleza */}
            {pwd.length > 0 && (
              <div className="mt-2 space-y-1">
                <div className="flex gap-1 h-1.5">
                  {[0, 1, 2, 3].map((i) => (
                    <div
                      key={i}
                      className={`flex-1 rounded-full transition-colors ${i < strength.score ? strength.color : 'bg-gray-200'}`}
                    />
                  ))}
                </div>
                <p className="text-xs text-gray-500">
                  Fortaleza: <span className="font-medium">{strength.label}</span>
                </p>
                {touched && strength.errors.length > 0 && (
                  <ul className="text-xs text-red-600 space-y-0.5 mt-1">
                    {strength.errors.map((err) => (
                      <li key={err} className="flex items-center gap-1">
                        <span>✗</span> {err}
                      </li>
                    ))}
                  </ul>
                )}
                {isValid && (
                  <p className="text-xs text-green-600 flex items-center gap-1">
                    <span>✓</span> Contraseña segura
                  </p>
                )}
              </div>
            )}
          </div>

          <div>
            <input
              type="password"
              value={pwd2}
              onChange={(e) => setPwd2(e.target.value)}
              className={`w-full px-3 py-2 border rounded ${pwd2 && pwd !== pwd2 ? 'border-red-400' : ''}`}
              placeholder={t('pages.setPassword.confirmPassword')}
              required
            />
            {pwd2 && pwd !== pwd2 && (
              <p className="text-xs text-red-600 mt-1">Las contraseñas no coinciden</p>
            )}
          </div>

          <button
            type="submit"
            disabled={saving}
            className="bg-blue-600 disabled:opacity-60 text-white px-4 py-2 rounded w-full"
          >
            {saving ? t('pages.setPassword.saving') : t('pages.setPassword.save')}
          </button>
        </form>
      </div>
    </div>
  )
}
