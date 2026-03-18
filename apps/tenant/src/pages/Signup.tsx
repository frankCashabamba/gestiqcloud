import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { TENANT_AUTH } from '@shared/endpoints'
import tenantApi from '../shared/api/client'
import { useAuth } from '../auth/AuthContext'
import { useToast, getErrorMessage } from '../shared/toast'

type SignupForm = {
  company_name: string
  first_name: string
  last_name: string
  email: string
  password: string
  country_code: string
  default_language: string
  timezone: string
  currency: string
}

const INITIAL_FORM: SignupForm = {
  company_name: '',
  first_name: '',
  last_name: '',
  email: '',
  password: '',
  country_code: 'ES',
  default_language: 'es',
  timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'Europe/Madrid',
  currency: 'EUR',
}

export default function Signup() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const { success, error } = useToast()
  const [form, setForm] = useState<SignupForm>(INITIAL_FORM)
  const [submitting, setSubmitting] = useState(false)

  const update = (field: keyof SignupForm, value: string) => {
    setForm(prev => ({ ...prev, [field]: value }))
  }

  const onSubmit: React.FormEventHandler = async (event) => {
    event.preventDefault()
    try {
      setSubmitting(true)
      await tenantApi.post(TENANT_AUTH.signup, form)
      await login({ identificador: form.email, password: form.password })
      success('Cuenta creada correctamente')
      navigate('/onboarding')
    } catch (err: any) {
      error(getErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-10">
      <div className="mx-auto grid max-w-6xl overflow-hidden rounded-[32px] bg-white shadow-2xl shadow-slate-900/10 lg:grid-cols-[0.95fr,1.05fr]">
        <aside className="hidden bg-slate-900 p-12 text-white lg:flex lg:flex-col lg:justify-between">
          <div>
            <div className="inline-flex rounded-full bg-emerald-500/15 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em] text-emerald-200">
              Alta autoservicio
            </div>
            <h1 className="mt-6 text-4xl font-bold leading-tight">Crea tu empresa y entra al onboarding en el mismo paso.</h1>
            <p className="mt-4 max-w-md text-sm leading-7 text-slate-300">
              El alta crea la empresa, el usuario administrador y la configuracion base para que empieces a trabajar sin depender del panel admin.
            </p>
          </div>
          <div className="space-y-3 text-sm text-slate-300">
            <p>1. Registra tu empresa</p>
            <p>2. Inicia sesion automaticamente</p>
            <p>3. Completa onboarding y activa tu plan</p>
          </div>
        </aside>

        <section className="p-6 sm:p-10 lg:p-12">
          <div className="mx-auto max-w-2xl">
            <div className="mb-8 flex items-center justify-between gap-4">
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.24em] text-blue-600">Crear cuenta</p>
                <h2 className="mt-2 text-3xl font-bold text-slate-900">Empieza en minutos</h2>
              </div>
              <Link to="/login" className="text-sm font-medium text-slate-500 hover:text-slate-900">
                Ya tengo cuenta
              </Link>
            </div>

            <form onSubmit={onSubmit} className="grid gap-5 md:grid-cols-2">
              <label className="md:col-span-2">
                <span className="mb-1.5 block text-sm font-medium text-slate-700">Empresa</span>
                <input
                  className="w-full rounded-xl border border-slate-200 px-4 py-3 outline-none transition focus:border-blue-500"
                  value={form.company_name}
                  onChange={(event) => update('company_name', event.target.value)}
                  placeholder="Ej: Gestiq Foods SL"
                  required
                />
              </label>

              <label>
                <span className="mb-1.5 block text-sm font-medium text-slate-700">Nombre</span>
                <input
                  className="w-full rounded-xl border border-slate-200 px-4 py-3 outline-none transition focus:border-blue-500"
                  value={form.first_name}
                  onChange={(event) => update('first_name', event.target.value)}
                  required
                />
              </label>

              <label>
                <span className="mb-1.5 block text-sm font-medium text-slate-700">Apellidos</span>
                <input
                  className="w-full rounded-xl border border-slate-200 px-4 py-3 outline-none transition focus:border-blue-500"
                  value={form.last_name}
                  onChange={(event) => update('last_name', event.target.value)}
                />
              </label>

              <label className="md:col-span-2">
                <span className="mb-1.5 block text-sm font-medium text-slate-700">Email</span>
                <input
                  type="email"
                  className="w-full rounded-xl border border-slate-200 px-4 py-3 outline-none transition focus:border-blue-500"
                  value={form.email}
                  onChange={(event) => update('email', event.target.value)}
                  required
                />
              </label>

              <label className="md:col-span-2">
                <span className="mb-1.5 block text-sm font-medium text-slate-700">Contrasena</span>
                <input
                  type="password"
                  className="w-full rounded-xl border border-slate-200 px-4 py-3 outline-none transition focus:border-blue-500"
                  value={form.password}
                  onChange={(event) => update('password', event.target.value)}
                  minLength={8}
                  required
                />
              </label>

              <label>
                <span className="mb-1.5 block text-sm font-medium text-slate-700">Pais</span>
                <select
                  className="w-full rounded-xl border border-slate-200 px-4 py-3 outline-none transition focus:border-blue-500"
                  value={form.country_code}
                  onChange={(event) => update('country_code', event.target.value)}
                >
                  <option value="ES">Espana</option>
                  <option value="EC">Ecuador</option>
                  <option value="MX">Mexico</option>
                  <option value="US">Estados Unidos</option>
                </select>
              </label>

              <label>
                <span className="mb-1.5 block text-sm font-medium text-slate-700">Moneda</span>
                <select
                  className="w-full rounded-xl border border-slate-200 px-4 py-3 outline-none transition focus:border-blue-500"
                  value={form.currency}
                  onChange={(event) => update('currency', event.target.value)}
                >
                  <option value="EUR">EUR</option>
                  <option value="USD">USD</option>
                  <option value="MXN">MXN</option>
                </select>
              </label>

              <label>
                <span className="mb-1.5 block text-sm font-medium text-slate-700">Idioma</span>
                <select
                  className="w-full rounded-xl border border-slate-200 px-4 py-3 outline-none transition focus:border-blue-500"
                  value={form.default_language}
                  onChange={(event) => update('default_language', event.target.value)}
                >
                  <option value="es">Espanol</option>
                  <option value="en">English</option>
                </select>
              </label>

              <label>
                <span className="mb-1.5 block text-sm font-medium text-slate-700">Zona horaria</span>
                <input
                  className="w-full rounded-xl border border-slate-200 px-4 py-3 outline-none transition focus:border-blue-500"
                  value={form.timezone}
                  onChange={(event) => update('timezone', event.target.value)}
                  required
                />
              </label>

              <div className="md:col-span-2 flex flex-col gap-3 pt-2">
                <button
                  type="submit"
                  disabled={submitting}
                  className="inline-flex items-center justify-center rounded-xl bg-blue-600 px-5 py-3 font-semibold text-white transition hover:bg-blue-700 disabled:opacity-60"
                >
                  {submitting ? 'Creando cuenta...' : 'Crear empresa y continuar'}
                </button>
                <p className="text-xs text-slate-500">
                  Al crear la cuenta entraras directamente al onboarding. La activacion del plan se gestiona despues desde suscripciones.
                </p>
              </div>
            </form>
          </div>
        </section>
      </div>
    </div>
  )
}
