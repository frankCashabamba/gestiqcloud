import React, { useState } from 'react'
import { useAuth } from '../auth/AuthContext'
import { useNavigate } from 'react-router-dom'
import { apiFetch, API_URL } from '../lib/http'

const ADMIN_ORIGIN =
  import.meta.env.VITE_ADMIN_ORIGIN || window.location.origin.replace('8082', '8081')
const TENANT_ORIGIN =
  import.meta.env.VITE_TENANT_ORIGIN || window.location.origin

export default function Login() {
  const { login } = useAuth() // TENANT login
  const navigate = useNavigate()
  const [identificador, setIdentificador] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function loginAdminFallback() {
    // Fallback directo contra endpoints de ADMIN.
    // Capturamos el access_token y lo pasamos por fragment al admin para que establezca su sesión.
    try {
      try { await apiFetch('/v1/admin/auth/csrf', { retryOn401: false } as any) } catch {}
      const data = await apiFetch<{ access_token?: string }>('/v1/admin/auth/login', {
        method: 'POST',
        body: JSON.stringify({ identificador: identificador.trim(), password }),
        retryOn401: false,
      } as any)
      const tok = data?.access_token
      const href = tok ? `${ADMIN_ORIGIN}/#access_token=${encodeURIComponent(tok)}` : ADMIN_ORIGIN
      window.location.href = href
    } catch (res: any) {
      if (res?.status === 429) {
        const ra = res?.retryAfter || 'unos'
        throw new Error(`Demasiados intentos. Intenta en ${ra} segundos.`)
      }
      throw new Error('Credenciales inválidas')
    }
  }

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      // 1) INTENTO TENANT
      await login({ identificador, password })
      navigate('/')
    } catch (err: any) {
      if (err?.status && err.status !== 401) {
        setError(err?.message || 'Error de servidor')
        setSubmitting(false)
        return
      }
      // 2) FALLBACK → ADMIN
      try {
        await loginAdminFallback()
      } catch (e: any) {
        setError(e?.message || 'Credenciales inválidas')
        setSubmitting(false)
      }
    }
  }

  return (
    <div className='container'>
      <h1>Iniciar sesión</h1>
      <form onSubmit={onSubmit}>
        <div style={{marginBottom:'.75rem'}}>
          <label>Usuario o email</label>
          <input value={identificador} onChange={e=>setIdentificador(e.target.value)} autoComplete='username' required/>
        </div>
        <div style={{marginBottom:'.75rem'}}>
          <label>Contraseña</label>
          <input type='password' value={password} onChange={e=>setPassword(e.target.value)} autoComplete='current-password' required/>
        </div>
        {error && <div className='error' style={{marginBottom:'.75rem'}}>{error}</div>}
        <button className='btn' type='submit' disabled={submitting}>{submitting ? 'Entrando…' : 'Entrar'}</button>
      </form>
      <p style={{marginTop:'.25rem', fontSize:'.8rem', color:'#64748b'}}>
        Tenant: {TENANT_ORIGIN} — Admin: {ADMIN_ORIGIN}
      </p>
    </div>
  )
}
