import React, { useState } from 'react'
import { useAuth } from '../auth/AuthContext'
import { useNavigate } from 'react-router-dom'
import { useEnv } from '@ui/env'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const { tenantOrigin } = useEnv()
  const [identificador, setIdentificador] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)


  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await login({ identificador, password }) // → /v1/admin/auth/login
      navigate('/admin', { replace: true });
    } catch (err: any) {
      setError(err?.message || 'Credenciales inválidas')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className='container'>
      <h1>Iniciar sesión (Admin)</h1>
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
      <p style={{marginTop:'.5rem', fontSize:'.85rem', color:'#64748b'}}>
        ¿Eres usuario de empresa? <a href={`${tenantOrigin}/login`}>Inicia sesión aquí</a>
      </p>
    </div>
  )
}
