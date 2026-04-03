import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

import { useAuth } from '../auth/AuthContext'
import { useEnv } from '@ui/env'
import { resolveTenantPath } from '../lib/tenantNavigation'

export default function Login() {
  const { t } = useTranslation(['common'])
  const { login } = useAuth()
  const navigate = useNavigate()
  const { adminOrigin } = useEnv()

  const [identificador, setIdentificador] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
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
    <div className="gc-login-page relative min-h-screen overflow-hidden bg-[linear-gradient(180deg,#edf4ff_0%,#f8fbff_45%,#f4efe6_100%)]">
      <div className="pointer-events-none absolute inset-0" aria-hidden="true">
        <div className="absolute left-[-120px] top-[-140px] h-[320px] w-[320px] rounded-full bg-sky-300/35 blur-3xl" />
        <div className="absolute bottom-[-140px] right-[-100px] h-[320px] w-[320px] rounded-full bg-amber-200/40 blur-3xl" />
        <div className="absolute inset-x-0 top-0 h-[420px] bg-[radial-gradient(circle_at_top,rgba(14,165,233,0.12),transparent_55%)]" />
      </div>

      <div className="relative mx-auto flex min-h-screen w-full max-w-[1180px] items-center px-4 py-8 sm:px-6 lg:px-8">
        <div className="grid w-full gap-6 lg:grid-cols-[0.92fr,1.08fr]">
          <section className="relative overflow-hidden rounded-[32px] bg-[#0f172a] p-8 text-white shadow-[0_30px_90px_rgba(15,23,42,0.28)] sm:p-10">
            <div
              className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(56,189,248,0.22),transparent_35%),radial-gradient(circle_at_bottom_right,rgba(251,191,36,0.16),transparent_32%)]"
              aria-hidden="true"
            />
            <div
              className="absolute inset-0 opacity-[0.07]"
              style={{
                backgroundImage:
                  'url("data:image/svg+xml,%3Csvg width=\'44\' height=\'44\' viewBox=\'0 0 44 44\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cg fill=\'none\' fill-rule=\'evenodd\'%3E%3Cg fill=\'%23ffffff\' fill-opacity=\'0.9\'%3E%3Ccircle cx=\'6\' cy=\'6\' r=\'1\'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")',
              }}
              aria-hidden="true"
            />

            <div className="relative z-10 flex h-full flex-col justify-between gap-10">
              <div className="space-y-8">
                <div className="flex items-center gap-3">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white/10 text-sm font-extrabold text-white ring-1 ring-white/15 backdrop-blur">
                    GC
                  </div>
                  <div>
                    <p className="text-sm font-semibold tracking-wide text-white">GestiqCloud</p>
                    <p className="text-xs text-slate-400">{t('login.subtitle')}</p>
                  </div>
                </div>

                <div className="max-w-xl space-y-4">
                  <span className="inline-flex items-center rounded-full bg-white/10 px-3 py-1 text-[11px] font-bold uppercase tracking-[0.22em] text-sky-100 ring-1 ring-white/15">
                    {t('login.quickAccessBadge')}
                  </span>
                  <h1 className="text-[2rem] font-bold leading-[1.05] tracking-[-0.03em] text-white sm:text-[2.35rem]">
                    {t('login.quickAccessTitle')}
                  </h1>
                  <p className="max-w-lg text-sm leading-6 text-slate-300">
                    {t('login.quickAccessSubtitle')}
                  </p>
                </div>

                <div className="flex flex-wrap gap-3">
                  {([
                    t('login.quickItemWorkspace'),
                    t('login.quickItemModules'),
                    t('login.quickItemSecure'),
                  ] as const).map((item) => (
                    <span
                      key={item}
                      className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-slate-200 backdrop-blur-sm"
                    >
                      {item}
                    </span>
                  ))}
                </div>
              </div>

              <div className="space-y-3">
                <div>
                  <Link
                    to="/demo"
                    className="inline-flex w-full items-center justify-center rounded-2xl border border-white/15 bg-white/10 px-5 py-3 text-sm font-semibold text-white transition hover:bg-white/15"
                  >
                    {t('login.requestDemo')}
                  </Link>
                </div>
                <p className="text-xs text-slate-400">{t('login.quickAccessNote')}</p>
              </div>
            </div>
          </section>

          <section className="rounded-[32px] border border-slate-200/70 bg-white/90 p-6 shadow-[0_24px_70px_rgba(148,163,184,0.18)] backdrop-blur sm:p-8 lg:p-10">
            <div className="mx-auto w-full max-w-[430px]">
              <header className="space-y-3">
                <span className="inline-flex items-center rounded-full bg-sky-50 px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.22em] text-[var(--gc-primary)]">
                  {t('login.clientAccess')}
                </span>
                <h2 className="text-3xl font-bold tracking-[-0.03em] text-slate-900">
                  {t('login.accessTitle')}
                </h2>
                <p className="text-sm leading-6 text-slate-500">
                  {t('login.accessSubtitle')}
                </p>
              </header>

              <form onSubmit={onSubmit} className="mt-8 space-y-5" noValidate>
                <div className="space-y-2">
                  <label
                    htmlFor="identificador"
                    className="text-[11px] font-bold uppercase tracking-[0.2em] text-slate-400"
                  >
                    {t('login.usernameLabel')}
                  </label>
                  <input
                    id="identificador"
                    name="identificador"
                    type="text"
                    autoComplete="username"
                    className="h-[52px] w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 text-sm text-slate-900 shadow-sm outline-none transition placeholder:text-slate-400 focus:border-[var(--gc-primary)] focus:bg-white focus:ring-4 focus:ring-sky-100"
                    value={identificador}
                    onChange={(event) => setIdentificador(event.target.value)}
                    placeholder={t('login.usernamePlaceholder')}
                    required
                  />
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between gap-3">
                    <label
                      htmlFor="password"
                      className="text-[11px] font-bold uppercase tracking-[0.2em] text-slate-400"
                    >
                      {t('login.passwordLabel')}
                    </label>
                    <Link
                      to="/forgot-password"
                      className="text-xs font-semibold text-[var(--gc-primary)] hover:underline"
                    >
                      {t('login.forgotPassword')}
                    </Link>
                  </div>

                  <div className="relative">
                    <input
                      id="password"
                      name="password"
                      type={showPassword ? 'text' : 'password'}
                      autoComplete="current-password"
                      className="h-[52px] w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 pr-20 text-sm text-slate-900 shadow-sm outline-none transition placeholder:text-slate-400 focus:border-[var(--gc-primary)] focus:bg-white focus:ring-4 focus:ring-sky-100"
                      value={password}
                      onChange={(event) => setPassword(event.target.value)}
                      placeholder="••••••••"
                      required
                    />

                    <button
                      type="button"
                      onClick={() => setShowPassword((v) => !v)}
                      className="absolute right-3 top-1/2 inline-flex -translate-y-1/2 items-center rounded-xl px-2.5 py-1.5 text-xs font-semibold text-slate-500 transition hover:bg-slate-100 hover:text-slate-700"
                      aria-label={showPassword ? t('login.hidePasswordAria') : t('login.showPasswordAria')}
                    >
                      {showPassword ? t('login.hidePassword') : t('login.showPassword')}
                    </button>
                  </div>
                </div>

                {error && (
                  <div
                    className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
                    role="alert"
                  >
                    {error}
                  </div>
                )}

                <label className="inline-flex cursor-pointer items-center gap-2.5 text-sm text-slate-600">
                  <input
                    type="checkbox"
                    className="h-4 w-4 rounded border-slate-300 text-[var(--gc-primary)] focus:ring-[var(--gc-primary)]"
                  />
                  <span>{t('login.rememberSession')}</span>
                </label>

                <button
                  type="submit"
                  className="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-[linear-gradient(135deg,var(--gc-primary),#0ea5e9)] px-5 py-3.5 text-sm font-semibold text-white shadow-lg shadow-sky-500/20 transition hover:-translate-y-0.5 hover:shadow-xl hover:shadow-sky-500/25 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--gc-primary)] disabled:cursor-not-allowed disabled:opacity-70"
                  disabled={submitting}
                >
                  {submitting && (
                    <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      />
                    </svg>
                  )}
                  {submitting ? t('login.signingIn') : t('login.signIn')}
                </button>

                <div className="rounded-[28px] border border-slate-200 bg-slate-50 p-4 sm:p-5">
                  <p className="text-sm font-semibold text-slate-900">{t('login.noAccount')}</p>
                  <p className="mt-1 text-sm leading-6 text-slate-500">{t('login.newUserSubtitle')}</p>
                  <div className="mt-4">
                    <Link
                      to="/demo"
                      className="inline-flex w-full items-center justify-center rounded-2xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white transition hover:bg-slate-800"
                    >
                      {t('login.requestDemo')}
                    </Link>
                  </div>
                </div>
              </form>

              <footer className="mt-8 space-y-1.5 text-center text-xs text-slate-400">
                <p>{t('login.copyright', { year })}</p>
                <p>{t('login.footerTagline')}</p>
              </footer>
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}
