import React, { useState } from 'react'
import { useAuth } from '../auth/AuthContext'
import { useNavigate } from 'react-router-dom'
import { apiFetch } from '../lib/http'
import { useEnv } from '@ui/env'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const { adminOrigin } = useEnv()
  const [identificador, setIdentificador] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const year = new Date().getFullYear()

  const inputClass =
    'w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-medium text-slate-900 placeholder:text-slate-400 transition focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/40'

  async function loginAdminFallback() {
    try {
      try {
        await apiFetch('/api/v1/admin/auth/csrf', { retryOn401: false } as any)
      } catch {}
      const data = await apiFetch<{ access_token?: string }>('/api/v1/admin/auth/login', {
        method: 'POST',
        body: JSON.stringify({ identificador: identificador.trim(), password }),
        retryOn401: false,
      } as any)
      const token = data?.access_token
      const target = token ? `${adminOrigin}/#access_token=${encodeURIComponent(token)}` : adminOrigin
      // Fallback disabled by policy: prevents admin login from tenant
      throw new Error('fallback_disabled')
    } catch (res: any) {
      if (res?.status === 429) {
        const wait = res?.retryAfter || 'a few'
        throw new Error(`Too many attempts. Try again in ${wait} seconds.`)
      }
      throw new Error('Invalid credentials')
    }
  }

  const onSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await login({ identificador, password })
      navigate('/')
    } catch (err: any) {
      if (err?.status && err.status !== 401) {
        setError(err?.message || 'Server error')
        setSubmitting(false)
        return
      }
      try {
        throw new Error('fallback_disabled')
      } catch (fallbackErr: any) {
        setError(fallbackErr?.message || 'Invalid credentials')
        setSubmitting(false)
      }
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-slate-100">
      <div className="mx-auto flex min-h-screen w-full max-w-6xl flex-col justify-center px-4 py-12 sm:px-8 lg:px-12">
        <div className="grid gap-8 lg:grid-cols-[1.05fr,0.95fr] xl:gap-12">
          <aside className="relative hidden overflow-hidden rounded-3xl bg-slate-900 p-10 text-white shadow-xl lg:flex lg:flex-col lg:justify-between">
            <div className="absolute inset-0 bg-gradient-to-br from-blue-500/20 via-slate-900/80 to-slate-950" aria-hidden="true" />
            <div className="relative z-10 flex flex-col gap-8">
              <div>
                <span className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-blue-100">
                  GestiqCloud Platform
                </span>
                <h1 className="mt-4 text-3xl font-semibold leading-tight text-white">
                  Power your ERP and CRM on a modular platform.
                </h1>
                <p className="mt-3 max-w-xl text-sm text-slate-200">
                  Connect teams, processes and data in one place. Configure the modules your business needs and scale them at your own pace.
                </p>
              </div>
              <ul className="space-y-4 text-sm text-slate-100">
                <li className="flex items-start gap-3">
                   <span className="mt-1 inline-flex h-6 w-6 items-center justify-center rounded-full bg-blue-500/30 text-xs font-semibold text-blue-100">
                     1
                   </span>
                   Orchestrate operations, sales and finance with connected workflows.
                 </li>
                 <li className="flex items-start gap-3">
                   <span className="mt-1 inline-flex h-6 w-6 items-center justify-center rounded-full bg-blue-500/30 text-xs font-semibold text-blue-100">
                     2
                   </span>
                   Activate modules by area and customize permissions for each team.
                 </li>
                 <li className="flex items-start gap-3">
                   <span className="mt-1 inline-flex h-6 w-6 items-center justify-center rounded-full bg-blue-500/30 text-xs font-semibold text-blue-100">
                     3
                   </span>
                   Get real-time indicators to make informed decisions.
                 </li>
              </ul>
            </div>
            <div className="relative z-10 flex flex-wrap items-center gap-4 text-xs text-slate-300">
              <span className="rounded-full border border-white/15 px-3 py-1">
                Enterprise security
              </span>
              <span className="rounded-full border border-white/15 px-3 py-1">
                Configurable roles and modules
              </span>
            </div>
          </aside>

          <section className="flex flex-col justify-center rounded-3xl border border-slate-200 bg-white p-8 shadow-sm sm:p-10">
            <header className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-wide text-blue-600">Welcome</span>
              <h2 className="text-2xl font-semibold text-slate-900">Sign in to GestiqCloud</h2>
              <p className="text-sm text-slate-500">
                Sign in with your corporate credentials to continue. If you have global permissions, we will automatically redirect you to the admin panel.
              </p>
            </header>

            <form onSubmit={onSubmit} className="mt-8 space-y-6" noValidate>
              <div className="space-y-1.5">
                <label htmlFor="identificador" className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Username or email
                </label>
                <input
                  id="identificador"
                  name="identificador"
                  type="text"
                  autoComplete="username"
                  className={inputClass}
                  value={identificador}
                  onChange={(event) => setIdentificador(event.target.value)}
                  placeholder="user@company.com"
                  required
                />
              </div>

              <div className="space-y-1.5">
                <label htmlFor="password" className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Password
                </label>
                <input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  className={inputClass}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="••••••••"
                  required
                />
              </div>

              {error && (
                <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700" role="alert">
                  {error}
                </div>
              )}

              <button
                type="submit"
                className="gc-button gc-button--primary w-full py-3 text-sm font-semibold"
                disabled={submitting}
              >
                {submitting ? 'Signing in…' : 'Sign in'}
              </button>
            </form>

            <footer className="mt-10 text-center text-xs text-slate-400">
              <p>© GestiqCloud {year}. All rights reserved.</p>
              <p className="mt-1">ERP · CRM · Modular platform for your business.</p>
            </footer>
          </section>
        </div>
      </div>
    </div>
  )
}
