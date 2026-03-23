import React, { useEffect, useState } from 'react'
import api from '../../services/api/client'

const BASE = '/api/v1/tenant/auth/mfa'

type Step = 'idle' | 'setup' | 'verify' | 'enabled' | 'recovery'

export default function MFASettings() {
  const [step, setStep] = useState<Step>('idle')
  const [loading, setLoading] = useState(true)
  const [mfaEnabled, setMfaEnabled] = useState(false)
  const [totpUri, setTotpUri] = useState('')
  const [recoveryCodes, setRecoveryCodes] = useState<string[]>([])
  const [code, setCode] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [qrUrl, setQrUrl] = useState('')
  const [disablePending, setDisablePending] = useState(false)

  const loadStatus = async () => {
    setLoading(true)
    try {
      const res = await api.get(`${BASE}/status`)
      const enabled = res.data?.mfa_enabled ?? false
      setMfaEnabled(enabled)
      setStep(enabled ? 'enabled' : 'idle')
    } catch {
      setMfaEnabled(false)
      setStep('idle')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadStatus() }, [])

  useEffect(() => {
    if (totpUri) {
      setQrUrl(
        `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(totpUri)}`
      )
    }
  }, [totpUri])

  const handleSetup = async () => {
    setBusy(true)
    setError('')
    try {
      const res = await api.post(`${BASE}/setup`)
      setTotpUri(res.data.totp_uri)
      setRecoveryCodes(res.data.recovery_codes)
      setStep('setup')
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Error al iniciar configuración MFA')
    } finally {
      setBusy(false)
    }
  }

  const handleVerify = async () => {
    if (code.length !== 6) { setError('El código debe tener 6 dígitos'); return }
    setBusy(true)
    setError('')
    try {
      await api.post(`${BASE}/verify`, { code })
      setMfaEnabled(true)
      setStep('recovery')
    } catch (e: any) {
      setError(e?.response?.data?.detail === 'invalid_totp_code'
        ? 'Código incorrecto. Verifica la hora de tu dispositivo.'
        : e?.response?.data?.detail || 'Error al verificar código')
    } finally {
      setBusy(false)
    }
  }

  const handleDisable = async () => {
    setDisablePending(false)
    setBusy(true)
    setError('')
    try {
      await api.delete(`${BASE}/disable`)
      setMfaEnabled(false)
      setStep('idle')
      setTotpUri('')
      setRecoveryCodes([])
      setCode('')
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Error al desactivar MFA')
    } finally {
      setBusy(false)
    }
  }

  if (loading) return <div className="p-6 text-sm text-slate-400">Cargando...</div>

  return (
    <div className="space-y-6 max-w-xl">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">Autenticación de dos factores (MFA)</h2>
        <p className="text-sm text-slate-500 mt-1">
          Protege tu cuenta con una capa adicional de seguridad usando una app TOTP
          (Google Authenticator, Authy, etc.).
        </p>
      </div>

      {/* Estado actual */}
      <div className={`flex items-center gap-3 p-3 rounded-lg border ${mfaEnabled ? 'bg-green-50 border-green-200' : 'bg-slate-50 border-slate-200'}`}>
        <span className={`text-lg ${mfaEnabled ? 'text-green-600' : 'text-slate-400'}`}>
          {mfaEnabled ? '🔒' : '🔓'}
        </span>
        <div>
          <p className="text-sm font-medium text-slate-800">
            MFA {mfaEnabled ? 'activado' : 'desactivado'}
          </p>
          <p className="text-xs text-slate-500">
            {mfaEnabled
              ? 'Tu cuenta está protegida con autenticación de dos factores.'
              : 'Activa MFA para mayor seguridad.'}
          </p>
        </div>
      </div>

      {error && (
        <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded p-3">
          {error}
        </div>
      )}

      {/* Paso 1: idle — botón para iniciar */}
      {step === 'idle' && (
        <button
          onClick={handleSetup}
          disabled={busy}
          className="px-4 py-2 bg-blue-600 text-white rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {busy ? 'Configurando...' : 'Activar MFA'}
        </button>
      )}

      {/* Paso 2: setup — mostrar QR y pedir verificación */}
      {step === 'setup' && (
        <div className="space-y-4">
          <div className="border rounded-lg p-4 bg-white space-y-3">
            <p className="text-sm font-medium text-slate-700">1. Escanea este código QR con tu app TOTP:</p>
            {qrUrl && (
              <img src={qrUrl} alt="QR TOTP" className="border rounded" width={200} height={200} />
            )}
            <details className="text-xs text-slate-500">
              <summary className="cursor-pointer hover:text-slate-700">Ver URI manual</summary>
              <code className="block mt-1 break-all bg-slate-50 p-2 rounded text-xs">{totpUri}</code>
            </details>
          </div>

          <div className="border rounded-lg p-4 bg-amber-50 border-amber-200 space-y-2">
            <p className="text-sm font-medium text-amber-800">2. Guarda tus códigos de recuperación:</p>
            <p className="text-xs text-amber-700">
              Estos códigos permiten acceder si pierdes tu dispositivo. Guárdalos en un lugar seguro — no los volverás a ver.
            </p>
            <div className="grid grid-cols-2 gap-1">
              {recoveryCodes.map((c) => (
                <code key={c} className="bg-white border border-amber-200 rounded px-2 py-1 text-xs font-mono text-center">
                  {c}
                </code>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <p className="text-sm font-medium text-slate-700">3. Ingresa el código de 6 dígitos para confirmar:</p>
            <div className="flex gap-2">
              <input
                type="text"
                inputMode="numeric"
                maxLength={6}
                placeholder="000000"
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                className="border rounded px-3 py-2 text-sm font-mono w-32 text-center tracking-widest"
              />
              <button
                onClick={handleVerify}
                disabled={busy || code.length !== 6}
                className="px-4 py-2 bg-blue-600 text-white rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
              >
                {busy ? 'Verificando...' : 'Activar'}
              </button>
              <button
                onClick={() => { setStep('idle'); setTotpUri(''); setRecoveryCodes([]); setCode(''); setError('') }}
                className="px-4 py-2 border rounded text-sm text-slate-600 hover:bg-slate-50"
              >
                Cancelar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Paso 3: recovery — después de activar, mostrar códigos una última vez */}
      {step === 'recovery' && (
        <div className="space-y-4">
          <div className="border rounded-lg p-4 bg-green-50 border-green-200">
            <p className="text-sm font-semibold text-green-800 mb-2">¡MFA activado correctamente!</p>
            <p className="text-xs text-green-700 mb-3">
              Guarda estos códigos de recuperación ahora. No los volverás a ver una vez que cierres esta pantalla.
            </p>
            <div className="grid grid-cols-2 gap-1">
              {recoveryCodes.map((c) => (
                <code key={c} className="bg-white border border-green-200 rounded px-2 py-1 text-xs font-mono text-center">
                  {c}
                </code>
              ))}
            </div>
          </div>
          <button
            onClick={() => { setStep('enabled'); setRecoveryCodes([]) }}
            className="px-4 py-2 bg-blue-600 text-white rounded text-sm font-medium hover:bg-blue-700"
          >
            He guardado los códigos
          </button>
        </div>
      )}

      {/* Paso 4: enabled — opciones de gestión */}
      {step === 'enabled' && (
        <div className="space-y-3">
          <button
            onClick={() => setDisablePending(true)}
            disabled={busy}
            className="px-4 py-2 bg-red-50 text-red-600 border border-red-200 rounded text-sm font-medium hover:bg-red-100 disabled:opacity-50"
          >
            {busy ? 'Desactivando...' : 'Desactivar MFA'}
          </button>
        </div>
      )}
      {disablePending && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-sm">
            <h3 className="font-semibold text-lg mb-2">Desactivar MFA</h3>
            <p className="text-sm text-slate-600 mb-4">¿Desactivar autenticación de dos factores? Tu cuenta quedará menos segura.</p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setDisablePending(false)} className="px-4 py-2 rounded bg-slate-200 hover:bg-slate-300 text-sm">Cancelar</button>
              <button onClick={handleDisable} className="px-4 py-2 rounded bg-red-600 text-white hover:bg-red-700 text-sm">Desactivar</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
