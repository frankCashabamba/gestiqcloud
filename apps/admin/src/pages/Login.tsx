import React, { useState } from 'react'

import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'

import { useEnv } from '@ui/env'

import { useAuth } from '../auth/AuthContext'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const { tenantOrigin } = useEnv()
  const { t } = useTranslation()
  const [identificador, setIdentificador] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const year = new Date().getFullYear()

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await login({ identificador, password })
      navigate('/admin', { replace: true })
    } catch (err: any) {
      setError(err?.message || t('login.invalidCredentials'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="gc-admin-login">
      {/* Background decoration */}
      <div className="gc-admin-login__bg" aria-hidden="true">
        <div className="gc-admin-login__orb gc-admin-login__orb--1" />
        <div className="gc-admin-login__orb gc-admin-login__orb--2" />
      </div>

      <div className="gc-admin-login__card">
        {/* Logo */}
        <div className="gc-admin-login__logo-wrap">
          <div className="gc-admin-login__logo">
            <svg viewBox="0 0 24 24" fill="none" className="gc-admin-login__logo-icon">
              <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
        </div>

        {/* Header */}
        <div className="gc-admin-login__header">
          <h1 className="gc-admin-login__title">{t('login.title')}</h1>
          <p className="gc-admin-login__subtitle">{t('login.adminSubtitle', { defaultValue: 'Panel de administración' })}</p>
        </div>

        {/* Form */}
        <form onSubmit={onSubmit} className="gc-admin-login__form">
          <div className="gc-admin-login__field">
            <label htmlFor="admin-identificador" className="gc-admin-login__label">{t('login.identifier')}</label>
            <input
              id="admin-identificador"
              name="identificador"
              className="gc-admin-login__input"
              value={identificador}
              onChange={e => setIdentificador(e.target.value)}
              autoComplete="username"
              placeholder="admin@gestiqcloud.com"
              required
            />
          </div>
          <div className="gc-admin-login__field">
            <label htmlFor="admin-password" className="gc-admin-login__label">{t('login.password')}</label>
            <input
              id="admin-password"
              name="password"
              type="password"
              className="gc-admin-login__input"
              value={password}
              onChange={e => setPassword(e.target.value)}
              autoComplete="current-password"
              placeholder="••••••••"
              required
            />
          </div>

          {error && (
            <div className="gc-admin-login__error" role="alert">
              <svg className="gc-admin-login__error-icon" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd"/>
              </svg>
              {error}
            </div>
          )}

          <button className="gc-admin-login__submit" type="submit" disabled={submitting}>
            {submitting ? (
              <svg className="gc-admin-login__spinner" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
            ) : null}
            {submitting ? t('login.submitting') : t('login.submit')}
          </button>
        </form>

        {/* Divider */}
        <div className="gc-admin-login__divider">
          <span>{t('login.tenantPrompt', { defaultValue: '¿Eres usuario de empresa?' })}</span>
        </div>

        <a href={`${tenantOrigin}/login`} className="gc-admin-login__tenant-link">
          {t('login.tenantLink', { defaultValue: 'Ir al login de empresa' })}
          <svg className="gc-admin-login__arrow" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clipRule="evenodd"/></svg>
        </a>

        <footer className="gc-admin-login__footer">
          © {year} GestiqCloud
        </footer>
      </div>
    </div>
  )
}
