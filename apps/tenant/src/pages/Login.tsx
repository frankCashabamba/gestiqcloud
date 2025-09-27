import React, { useState } from 'react'
import { useAuth } from '../auth/AuthContext'
import { useNavigate } from 'react-router-dom'
import { apiFetch } from '../lib/http'

const ADMIN_ORIGIN =
  import.meta.env.VITE_ADMIN_ORIGIN || window.location.origin.replace('8082', '8081')
const TENANT_ORIGIN =
  import.meta.env.VITE_TENANT_ORIGIN || window.location.origin

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
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
        await apiFetch('/v1/admin/auth/csrf', { retryOn401: false } as any)
      } catch {}
      const data = await apiFetch<{ access_token?: string }>('/v1/admin/auth/login', {
        method: 'POST',
        body: JSON.stringify({ identificador: identificador.trim(), password }),
        retryOn401: false,
      } as any)
      const token = data?.access_token
      const target = token ? `${ADMIN_ORIGIN}/#access_token=${encodeURIComponent(token)}` : ADMIN_ORIGIN
      window.location.href = target
    } catch (res: any) {
      if (res?.status === 429) {
        const wait = res?.retryAfter || 'unos'
        throw new Error(`Demasiados intentos. Intenta en ${wait} segundos.`)
      }
      throw new Error('Credenciales inválidas')
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
        setError(err?.message || 'Error de servidor')
        setSubmitting(false)
        return
      }
      try {
        await loginAdminFallback()
      } catch (fallbackErr: any) {
        setError(fallbackErr?.message || 'Credenciales inválidas')
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
                  Impulsa tu ERP y CRM en una plataforma modular.
                </h1>
                <p className="mt-3 max-w-xl text-sm text-slate-200">
                  Conecta equipos, procesos y datos en un solo lugar. Configura los módulos que tu negocio necesita y escálalos a tu ritmo.
                </p>
              </div>
              <ul className="space-y-4 text-sm text-slate-100">
                <li className="flex items-start gap-3">
                  <span className="mt-1 inline-flex h-6 w-6 items-center justify-center rounded-full bg-blue-500/30 text-xs font-semibold text-blue-100">
                    1
                  </span>
                  Orquesta operaciones, ventas y finanzas con flujos conectados.
                </li>
                <li className="flex items-start gap-3">
                  <span className="mt-1 inline-flex h-6 w-6 items-center justify-center rounded-full bg-blue-500/30 text-xs font-semibold text-blue-100">
                    2
                  </span>
                  Activa módulos por área y personaliza permisos para cada equipo.
                </li>
                <li className="flex items-start gap-3">
                  <span className="mt-1 inline-flex h-6 w-6 items-center justify-center rounded-full bg-blue-500/30 text-xs font-semibold text-blue-100">
                    3
                  </span>
                  Obtén indicadores en tiempo real para tomar decisiones informadas.
                </li>
              </ul>
            </div>
            <div className="relative z-10 flex flex-wrap items-center gap-4 text-xs text-slate-300">
              <span className="rounded-full border border-white/15 px-3 py-1">
                Seguridad empresarial
              </span>
              <span className="rounded-full border border-white/15 px-3 py-1">
                Roles y módulos configurables
              </span>
            </div>
          </aside>

          <section className="flex flex-col justify-center rounded-3xl border border-slate-200 bg-white p-8 shadow-sm sm:p-10">
            <header className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-wide text-blue-600">Bienvenido</span>
              <h2 className="text-2xl font-semibold text-slate-900">Inicia sesión en GestiqCloud</h2>
              <p className="text-sm text-slate-500">
                Accede con tus credenciales corporativas para continuar. Si tienes permisos globales te redirigiremos automáticamente al panel administrativo.
              </p>
            </header>

            <form onSubmit={onSubmit} className="mt-8 space-y-6" noValidate>
              <div className="space-y-1.5">
                <label htmlFor="identificador" className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Usuario o email
                </label>
                <input
                  id="identificador"
                  name="identificador"
                  type="text"
                  autoComplete="username"
                  className={inputClass}
                  value={identificador}
                  onChange={(event) => setIdentificador(event.target.value)}
                  placeholder="usuario@empresa.com"
                  required
                />
              </div>

              <div className="space-y-1.5">
                <label htmlFor="password" className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Contraseña
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
                {submitting ? 'Ingresando…' : 'Entrar'}
              </button>
            </form>

            <footer className="mt-10 text-center text-xs text-slate-400">
              <p>© GestiqCloud {year}. Todos los derechos reservados.</p>
              <p className="mt-1">ERP · CRM · Plataforma modular para tu empresa.</p>
            </footer>
          </section>
        </div>
      </div>
    </div>
  )
}
