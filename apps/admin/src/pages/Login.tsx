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


  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await login({ identificador, password }) // → /v1/admin/auth/login
      navigate('/admin', { replace: true });
    } catch (err: any) {
      setError(err?.message || t('login.invalidCredentials'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className='container'>
      <h1>{t('login.title')}</h1>
      <form onSubmit={onSubmit}>
        <div style={{marginBottom:'.75rem'}}>
          <label htmlFor='admin-identificador'>{t('login.identifier')}</label>
          <input id='admin-identificador' name='identificador' value={identificador} onChange={e=>setIdentificador(e.target.value)} autoComplete='username' required/>
        </div>
        <div style={{marginBottom:'.75rem'}}>
          <label>{t('login.password')}</label>
          <input id='admin-password' name='password' type='password' value={password} onChange={e=>setPassword(e.target.value)} autoComplete='current-password' required/>
        </div>
        {error && <div className='error' style={{marginBottom:'.75rem'}}>{error}</div>}
        <button className='btn' type='submit' disabled={submitting}>{submitting ? t('login.submitting') : t('login.submit')}</button>
      </form>
      <p style={{marginTop:'.5rem', fontSize:'.85rem', color:'#64748b'}}>
        {t('login.tenantPrompt')} <a href={`${tenantOrigin}/login`}>{t('login.tenantLink')}</a>
      </p>
    </div>
  )
}
