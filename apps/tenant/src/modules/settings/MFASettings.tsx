import React, { useEffect, useState } from 'react'
import QRCode from 'qrcode'
import { useTranslation } from 'react-i18next'
import { getMFAStatus, setupMFA, verifyMFA, disableMFA } from '../../services/api/mfa'

type Step = 'idle' | 'setup' | 'verify' | 'enabled' | 'recovery'

export default function MFASettings() {
  const { t } = useTranslation(['settings', 'common'])
  const [step, setStep] = useState<Step>('idle')
  const [loading, setLoading] = useState(true)
  const [mfaEnabled, setMfaEnabled] = useState(false)
  const [totpUri, setTotpUri] = useState('')
  const [recoveryCodes, setRecoveryCodes] = useState<string[]>([])
  const [code, setCode] = useState('')
  const [errorMsg, setErrorMsg] = useState('')
  const [busy, setBusy] = useState(false)
  const [qrUrl, setQrUrl] = useState('')
  const [qrFailed, setQrFailed] = useState(false)
  const [disablePending, setDisablePending] = useState(false)

  const loadStatus = async () => {
    setLoading(true)
    try {
      const data = await getMFAStatus()
      const enabled = data?.mfa_enabled ?? false
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
      setQrFailed(false)
      QRCode.toDataURL(totpUri, { width: 200, margin: 1 })
        .then(setQrUrl)
        .catch(() => {
          setQrUrl('')
          setQrFailed(true)
        })
    }
  }, [totpUri])

  const handleSetup = async () => {
    setBusy(true)
    setErrorMsg('')
    try {
      const data = await setupMFA()
      setTotpUri(data.totp_uri)
      setRecoveryCodes(data.recovery_codes)
      setStep('setup')
    } catch (e: any) {
      setErrorMsg(e?.response?.data?.detail || t('settings:mfa.errorSetup'))
    } finally {
      setBusy(false)
    }
  }

  const handleVerify = async () => {
    if (code.length !== 6) { setErrorMsg(t('settings:mfa.codeLength')); return }
    setBusy(true)
    setErrorMsg('')
    try {
      await verifyMFA({ code })
      setMfaEnabled(true)
      setStep('recovery')
    } catch (e: any) {
      setErrorMsg(
        e?.response?.data?.detail === 'invalid_totp_code'
          ? t('settings:mfa.codeInvalid')
          : e?.response?.data?.detail || t('settings:mfa.errorVerify')
      )
    } finally {
      setBusy(false)
    }
  }

  const handleDisable = async () => {
    setDisablePending(false)
    setBusy(true)
    setErrorMsg('')
    try {
      await disableMFA()
      setMfaEnabled(false)
      setStep('idle')
      setTotpUri('')
      setRecoveryCodes([])
      setCode('')
    } catch (e: any) {
      setErrorMsg(e?.response?.data?.detail || t('settings:mfa.errorDisable'))
    } finally {
      setBusy(false)
    }
  }

  if (loading) return <div className="p-6 text-sm text-slate-400">{t('settings:mfa.loading')}</div>

  return (
    <div className="space-y-6 max-w-xl">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">{t('settings:mfa.title')}</h2>
        <p className="text-sm text-slate-500 mt-1">{t('settings:mfa.subtitle')}</p>
      </div>

      <div className={`flex items-center gap-3 p-3 rounded-lg border ${mfaEnabled ? 'bg-green-50 border-green-200' : 'bg-slate-50 border-slate-200'}`}>
        <span className={`text-lg ${mfaEnabled ? 'text-green-600' : 'text-slate-400'}`}>
          {mfaEnabled ? '🔒' : '🔓'}
        </span>
        <div>
          <p className="text-sm font-medium text-slate-800">
            {mfaEnabled ? t('settings:mfa.statusEnabled') : t('settings:mfa.statusDisabled')}
          </p>
          <p className="text-xs text-slate-500">
            {mfaEnabled ? t('settings:mfa.descEnabled') : t('settings:mfa.descDisabled')}
          </p>
        </div>
      </div>

      {errorMsg && (
        <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded p-3">
          {errorMsg}
        </div>
      )}

      {step === 'idle' && (
        <button
          onClick={handleSetup}
          disabled={busy}
          className="px-4 py-2 bg-blue-600 text-white rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {busy ? t('settings:mfa.activating') : t('settings:mfa.activate')}
        </button>
      )}

      {step === 'setup' && (
        <div className="space-y-4">
          <div className="border rounded-lg p-4 bg-white space-y-3">
            <p className="text-sm font-medium text-slate-700">{t('settings:mfa.step1')}</p>
            {qrUrl && !qrFailed ? (
              <img
                src={qrUrl}
                alt="QR TOTP"
                className="border rounded"
                width={200}
                height={200}
                onError={() => setQrFailed(true)}
              />
            ) : (
              <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded p-2">
                {t('settings:mfa.qrFallback')}
              </p>
            )}
            <details className="text-xs text-slate-500">
              <summary className="cursor-pointer hover:text-slate-700">{t('settings:mfa.manualUri')}</summary>
              <code className="block mt-1 break-all bg-slate-50 p-2 rounded text-xs">{totpUri}</code>
            </details>
          </div>

          <div className="border rounded-lg p-4 bg-amber-50 border-amber-200 space-y-2">
            <p className="text-sm font-medium text-amber-800">{t('settings:mfa.step2')}</p>
            <p className="text-xs text-amber-700">{t('settings:mfa.step2hint')}</p>
            <div className="grid grid-cols-2 gap-1">
              {recoveryCodes.map((c) => (
                <code key={c} className="bg-white border border-amber-200 rounded px-2 py-1 text-xs font-mono text-center">
                  {c}
                </code>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <p className="text-sm font-medium text-slate-700">{t('settings:mfa.step3')}</p>
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
                {busy ? t('settings:mfa.verifying') : t('settings:mfa.verify')}
              </button>
              <button
                onClick={() => { setStep('idle'); setTotpUri(''); setRecoveryCodes([]); setCode(''); setErrorMsg('') }}
                className="px-4 py-2 border rounded text-sm text-slate-600 hover:bg-slate-50"
              >
                {t('settings:mfa.cancel')}
              </button>
            </div>
          </div>
        </div>
      )}

      {step === 'recovery' && (
        <div className="space-y-4">
          <div className="border rounded-lg p-4 bg-green-50 border-green-200">
            <p className="text-sm font-semibold text-green-800 mb-2">{t('settings:mfa.recoveryTitle')}</p>
            <p className="text-xs text-green-700 mb-3">{t('settings:mfa.recoveryHint')}</p>
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
            {t('settings:mfa.savedCodes')}
          </button>
        </div>
      )}

      {step === 'enabled' && (
        <div className="space-y-3">
          <button
            onClick={() => setDisablePending(true)}
            disabled={busy}
            className="px-4 py-2 bg-red-50 text-red-600 border border-red-200 rounded text-sm font-medium hover:bg-red-100 disabled:opacity-50"
          >
            {busy ? t('settings:mfa.disabling') : t('settings:mfa.disable')}
          </button>
        </div>
      )}

      {disablePending && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-sm">
            <h3 className="font-semibold text-lg mb-2">{t('settings:mfa.confirmDisableTitle')}</h3>
            <p className="text-sm text-slate-600 mb-4">{t('settings:mfa.confirmDisableMsg')}</p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setDisablePending(false)} className="px-4 py-2 rounded bg-slate-200 hover:bg-slate-300 text-sm">
                {t('settings:mfa.cancel')}
              </button>
              <button onClick={handleDisable} className="px-4 py-2 rounded bg-red-600 text-white hover:bg-red-700 text-sm">
                {t('settings:mfa.confirmDisable')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
