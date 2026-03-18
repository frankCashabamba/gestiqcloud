import React, { useState } from 'react'
import { useAuth } from '../auth/AuthContext'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useEnv } from '@ui/env'
import { resolveTenantPath } from '../lib/tenantNavigation'

export default function Login() {
  const { t } = useTranslation(['common'])
  const { login } = useAuth()
  const navigate = useNavigate()
  const { adminOrigin } = useEnv()
  const [identificador, setIdentificador] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const year = new Date().getFullYear()

  const onSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      const result = await login({ identificador, password })
      if (result.scope === 'admin') {
        const target = result.accessToken
          ? `${adminOrigin}/#access_token=${encodeURIComponent(result.accessToken)}`
          : adminOrigin
        window.location.assign(target)
        return
      }
      const target = await resolveTenantPath()
      navigate(target)
    } catch (err: any) {
      if (err?.status === 429) {
        const wait = err?.retryAfter || 'a few'
        setError(t('login.tooManyAttempts', { wait }))
      } else if (err?.status === 401) {
        setError(t('login.invalidCredentials'))
      } else {
        setError(err?.message || t('login.serverError'))
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="gc-login-page">
      {/* Decorative background shapes */}
      <div className="gc-login-page__bg" aria-hidden="true">
        <div className="gc-login-page__orb gc-login-page__orb--1" />
        <div className="gc-login-page__orb gc-login-page__orb--2" />
        <div className="gc-login-page__orb gc-login-page__orb--3" />
      </div>

      <div className="mx-auto flex min-h-screen w-full max-w-[1140px] flex-col justify-center px-5 py-12 sm:px-8 lg:px-12">
        <div className="grid gap-0 overflow-hidden rounded-[28px] shadow-2xl shadow-slate-900/10 lg:grid-cols-[1.1fr,0.9fr]">
          {/* ─── Left hero panel ─── */}
          <aside className="relative hidden overflow-hidden bg-slate-900 p-12 text-white lg:flex lg:flex-col lg:justify-between">
            <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_60%_at_10%_-10%,rgba(59,130,246,.28),transparent),radial-gradient(ellipse_50%_80%_at_100%_100%,rgba(99,102,241,.18),transparent)]" aria-hidden="true" />
            {/* Subtle grid pattern */}
            <div className="absolute inset-0 opacity-[0.04]" style={{ backgroundImage: 'url("data:image/svg+xml,%3Csvg width=\'40\' height=\'40\' viewBox=\'0 0 40 40\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cg fill=\'%23fff\' fill-rule=\'evenodd\'%3E%3Ccircle cx=\'20\' cy=\'20\' r=\'1\'/%3E%3C/g%3E%3C/svg%3E")' }} aria-hidden="true" />

            <div className="relative z-10 flex flex-col gap-10">
              {/* Brand mark */}
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/10 text-sm font-extrabold backdrop-blur-sm">
                  GC
                </div>
                <span className="text-sm font-semibold tracking-wide text-white/70">GestiqCloud</span>
              </div>

              <div>
                <span className="inline-flex items-center gap-2 rounded-full bg-blue-500/15 px-3.5 py-1 text-[11px] font-semibold uppercase tracking-widest text-blue-200 ring-1 ring-blue-400/20">
                  {t('login.platformBadge')}
                </span>
                <h1 className="mt-5 text-[2.125rem] font-bold leading-[1.15] tracking-tight text-white">
                  {t('login.heroTitle')}
                </h1>
                <p className="mt-4 max-w-md text-[0.9375rem] leading-relaxed text-slate-300">
                  {t('login.heroSubtitle')}
                </p>
              </div>

              <ul className="space-y-4">
                {[t('login.feature1'), t('login.feature2'), t('login.feature3')].map((feature, i) => (
                  <li key={i} className="flex items-start gap-3.5 text-sm text-slate-200">
                    <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500/30 to-indigo-500/20 text-xs font-bold text-blue-100 ring-1 ring-white/10">
                      {i + 1}
                    </span>
                    <span className="pt-0.5">{feature}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="relative z-10 flex flex-wrap items-center gap-3 text-xs text-slate-400">
              <span className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 backdrop-blur-sm">
                <svg className="h-3 w-3 text-emerald-400" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M10 1a4.5 4.5 0 00-4.5 4.5V9H5a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2h-.5V5.5A4.5 4.5 0 0010 1zm3 8V5.5a3 3 0 10-6 0V9h6z" clipRule="evenodd"/></svg>
                {t('login.badgeSecurity')}
              </span>
              <span className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 backdrop-blur-sm">
                <svg className="h-3 w-3 text-blue-400" fill="currentColor" viewBox="0 0 20 20"><path d="M9 6a3 3 0 11-6 0 3 3 0 016 0zM17 6a3 3 0 11-6 0 3 3 0 016 0zM12.93 17c.046-.327.07-.66.07-1a6.97 6.97 0 00-1.5-4.33A5 5 0 0119 16v1h-6.07zM6 11a5 5 0 015 5v1H1v-1a5 5 0 015-5z"/></svg>
                {t('login.badgeRoles')}
              </span>
            </div>
          </aside>

          {/* ─── Right form panel ─── */}
          <section className="flex flex-col justify-center bg-white px-8 py-12 sm:px-12 lg:px-14 lg:py-16">
            {/* Mobile brand (visible < lg) */}
            <div className="mb-8 flex items-center gap-3 lg:hidden">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[var(--gc-primary)] text-xs font-extrabold text-white shadow-md shadow-blue-600/25">
                GC
              </div>
              <span className="text-sm font-semibold text-slate-500">GestiqCloud</span>
            </div>

            <header className="space-y-2">
              <span className="text-xs font-bold uppercase tracking-widest text-[var(--gc-primary)]">{t('login.welcome')}</span>
              <h2 className="text-[1.625rem] font-bold tracking-tight text-slate-900">{t('login.signInTitle')}</h2>
              <p className="text-sm text-slate-500">
                {t('login.signInSubtitle')}
              </p>
            </header>

            <form onSubmit={onSubmit} className="mt-8 space-y-5" noValidate>
              <div className="space-y-1.5">
                <label htmlFor="identificador" className="text-[11px] font-bold uppercase tracking-widest text-slate-400">
                  {t('login.usernameLabel')}
                </label>
                <input
                  id="identificador"
                  name="identificador"
                  type="text"
                  autoComplete="username"
                  className="gc-login-input"
                  value={identificador}
                  onChange={(event) => setIdentificador(event.target.value)}
                  placeholder="user@company.com"
                  required
                />
              </div>

              <div className="space-y-1.5">
                <label htmlFor="password" className="text-[11px] font-bold uppercase tracking-widest text-slate-400">
                  {t('login.passwordLabel')}
                </label>
                <input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  className="gc-login-input"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="••••••••"
                  required
                />
              </div>

              {error && (
                <div className="gc-alert gc-alert--error" role="alert">
                  {error}
                </div>
              )}

              <button
                type="submit"
                className="gc-login-submit"
                disabled={submitting}
              >
                {submitting && (
                  <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                )}
                {submitting ? t('login.signingIn') : t('login.signIn')}
              </button>

              <div className="text-center text-sm text-slate-500">
                <span>No tienes cuenta? </span>
                <Link to="/signup" className="font-semibold text-[var(--gc-primary)] hover:underline">
                  Crear empresa
                </Link>
              </div>
            </form>

            <footer className="mt-12 text-center text-xs text-slate-400">
              <p>{t('login.copyright', { year })}</p>
              <p className="mt-1 text-slate-300">{t('login.tagline')}</p>
            </footer>
          </section>
        </div>
      </div>
    </div>
  )
}
