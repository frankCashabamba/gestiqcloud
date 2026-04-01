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
    <div className="gc-login-page relative overflow-hidden bg-[#1a2b45]">
      {/* Background glows */}
      <div className="pointer-events-none absolute inset-0" aria-hidden="true">
        <div className="absolute left-[-120px] top-[-120px] h-[280px] w-[280px] rounded-full bg-blue-400/15 blur-3xl" />
        <div className="absolute bottom-[-100px] right-[-60px] h-[260px] w-[260px] rounded-full bg-indigo-400/10 blur-3xl" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(59,130,246,0.12),transparent_30%),radial-gradient(circle_at_bottom_right,rgba(99,102,241,0.08),transparent_30%)]" />
      </div>

      <div className="relative mx-auto flex min-h-screen w-full max-w-[1240px] items-center px-4 py-8 sm:px-6 lg:px-10">
        <div className="grid w-full overflow-hidden rounded-[28px] border border-white/10 bg-white/70 shadow-2xl shadow-slate-950/30 backdrop-blur-xl lg:grid-cols-[1.08fr,0.92fr]">

          {/* ─── Hero panel (desktop only) ─── */}
          <aside className="relative hidden overflow-hidden bg-[#1e3054] p-9 text-white lg:flex lg:min-h-[700px] lg:flex-col lg:justify-between xl:p-11">
            <div
              className="absolute inset-0 bg-[radial-gradient(ellipse_70%_50%_at_10%_-10%,rgba(59,130,246,.22),transparent),radial-gradient(ellipse_50%_70%_at_100%_100%,rgba(99,102,241,.12),transparent)]"
              aria-hidden="true"
            />
            <div
              className="absolute inset-0 opacity-[0.05]"
              style={{
                backgroundImage:
                  'url("data:image/svg+xml,%3Csvg width=\'42\' height=\'42\' viewBox=\'0 0 42 42\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cg fill=\'%23fff\' fill-rule=\'evenodd\'%3E%3Ccircle cx=\'21\' cy=\'21\' r=\'1\'/%3E%3C/g%3E%3C/svg%3E")',
              }}
              aria-hidden="true"
            />

            <div className="relative z-10 space-y-7">
              {/* Brand + demo CTA */}
              <div className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white/10 text-sm font-extrabold text-white ring-1 ring-white/15 backdrop-blur-sm">
                    GC
                  </div>
                  <div>
                    <p className="text-sm font-semibold tracking-wide text-white/90">GestiqCloud</p>
                    <p className="text-xs text-slate-400">{t('login.subtitle')}</p>
                  </div>
                </div>

                <Link
                  to="/demo"
                  className="inline-flex items-center rounded-xl border border-white/15 bg-white/10 px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/15"
                >
                  {t('login.requestDemo')}
                </Link>
              </div>

              {/* Hero copy */}
              <div className="max-w-xl">
                <span className="inline-flex items-center gap-2 rounded-full bg-blue-500/15 px-3.5 py-1.5 text-[11px] font-bold uppercase tracking-[0.22em] text-blue-200 ring-1 ring-blue-400/20">
                  {t('login.badgePlatform')}
                </span>

                <h1 className="mt-4 text-[1.65rem] font-bold leading-[1.15] tracking-[-0.02em] text-white xl:text-[1.9rem]">
                  {t('login.heroTagline')}
                </h1>

                <p className="mt-3 max-w-lg text-sm leading-6 text-slate-300/90">
                  {t('login.heroDescription')}
                </p>
              </div>

              {/* Stats */}
              <div className="grid gap-4 sm:grid-cols-3">
                {([
                  { value: '99.9%', label: t('login.stat1Label') },
                  { value: 'RBAC',  label: t('login.stat2Label') },
                  { value: 'MFA',   label: t('login.stat3Label') },
                ] as const).map(({ value, label }) => (
                  <div key={value} className="rounded-xl border border-white/10 bg-white/5 px-3 py-3 backdrop-blur-sm">
                    <p className="text-lg font-bold text-white">{value}</p>
                    <p className="mt-0.5 text-xs text-slate-400">{label}</p>
                  </div>
                ))}
              </div>

              {/* Features */}
              <div className="grid gap-3">
                {([
                  t('login.featurePipeline'),
                  t('login.featureOps'),
                  t('login.featureBilling'),
                ] as const).map((item, index) => (
                  <div
                    key={item}
                    className="flex items-start gap-3 rounded-xl border border-white/10 bg-white/5 px-3.5 py-2.5 backdrop-blur-sm"
                  >
                    <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-blue-500/25 text-[11px] font-bold text-blue-200 ring-1 ring-white/10">
                      {index + 1}
                    </span>
                    <p className="text-xs leading-5 text-slate-300">{item}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Trust badges */}
            <div className="relative z-10 flex flex-wrap gap-3 text-xs text-slate-400">
              {([
                { color: 'bg-emerald-400', label: t('login.badgeSecurityLabel') },
                { color: 'bg-blue-400',    label: t('login.badgeRolesLabel') },
                { color: 'bg-cyan-300',    label: t('login.badgeMt') },
              ] as const).map(({ color, label }) => (
                <span
                  key={label}
                  className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 backdrop-blur-sm"
                >
                  <span className={`h-2 w-2 rounded-full ${color}`} />
                  {label}
                </span>
              ))}
            </div>
          </aside>

          {/* ─── Form panel ─── */}
          <section className="flex flex-col justify-center bg-white px-6 py-10 sm:px-10 lg:px-12 lg:py-14 xl:px-14">

            {/* Mobile brand + demo (hidden on lg+) */}
            <div className="mb-8 flex items-center justify-between gap-4 lg:hidden">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-[var(--gc-primary)] text-xs font-extrabold text-white shadow-lg shadow-blue-600/25">
                  GC
                </div>
                <div>
                  <p className="text-sm font-semibold text-slate-700">GestiqCloud</p>
                  <p className="text-[11px] text-slate-400">{t('login.subtitle')}</p>
                </div>
              </div>

              <Link
                to="/demo"
                className="inline-flex items-center rounded-xl border border-slate-200 px-3.5 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
              >
                {t('login.requestDemo')}
              </Link>
            </div>

            <div className="mx-auto w-full max-w-[430px]">
              <header className="space-y-2">
                <span className="inline-flex items-center rounded-full bg-blue-50 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-[0.22em] text-[var(--gc-primary)]">
                  {t('login.clientAccess')}
                </span>
                <h2 className="text-2xl font-bold tracking-[-0.02em] text-slate-800">
                  {t('login.accessTitle')}
                </h2>
                <p className="text-sm leading-5 text-slate-500">
                  {t('login.accessSubtitle')}
                </p>
              </header>

              <form onSubmit={onSubmit} className="mt-6 space-y-4" noValidate>
                {/* Username */}
                <div className="space-y-1.5">
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
                    className="h-12 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 text-sm text-slate-900 shadow-sm outline-none transition placeholder:text-slate-400 focus:border-[var(--gc-primary)] focus:bg-white focus:ring-4 focus:ring-blue-100"
                    value={identificador}
                    onChange={(event) => setIdentificador(event.target.value)}
                    placeholder="usuario@empresa.com"
                    required
                  />
                </div>

                {/* Password */}
                <div className="space-y-1.5">
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
                      className="h-12 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 pr-20 text-sm text-slate-900 shadow-sm outline-none transition placeholder:text-slate-400 focus:border-[var(--gc-primary)] focus:bg-white focus:ring-4 focus:ring-blue-100"
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

                {/* Error */}
                {error && (
                  <div
                    className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
                    role="alert"
                  >
                    {error}
                  </div>
                )}

                {/* Remember + MFA row */}
                <div className="flex items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                  <label className="inline-flex cursor-pointer items-center gap-2.5">
                    <input
                      type="checkbox"
                      className="h-4 w-4 rounded border-slate-300 text-[var(--gc-primary)] focus:ring-[var(--gc-primary)]"
                    />
                    <span>{t('login.rememberSession')}</span>
                  </label>
                  <span className="hidden text-xs font-medium text-slate-400 sm:inline">
                    {t('login.mfaEnabled')}
                  </span>
                </div>

                {/* Submit */}
                <button
                  type="submit"
                  className="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-[linear-gradient(135deg,var(--gc-primary),#0ea5e9)] px-5 py-3.5 text-sm font-semibold text-white shadow-lg shadow-blue-600/20 transition hover:-translate-y-0.5 hover:shadow-xl hover:shadow-blue-600/25 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--gc-primary)] disabled:cursor-not-allowed disabled:opacity-70"
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

                {/* Sign up CTA */}
                <div className="rounded-2xl border border-slate-200 bg-white p-4 text-center text-sm text-slate-500 shadow-sm">
                  <span>{t('login.noAccount')} </span>
                  <Link
                    to="/demo"
                    className="font-semibold text-[var(--gc-primary)] hover:underline"
                  >
                    {t('login.requestDemo')}
                  </Link>
                </div>
              </form>

              <footer className="mt-8 space-y-1.5 text-center text-xs text-slate-400">
                <p>{t('login.copyright', { year })}</p>
                <p className="text-slate-400">{t('login.footerTagline')}</p>
              </footer>
            </div>
          </section>

        </div>
      </div>
    </div>
  )
}
