import React, { useEffect, useState } from 'react'

type TaxConfig = {
  enabled?: boolean
  default_rate?: number
}

type PosSettings = {
  tax?: TaxConfig
  [k: string]: any
}

async function apiGet(path: string) {
  const res = await fetch(`/api/v1/settings${path}`, { credentials: 'include' })
  if (!res.ok) throw new Error(`GET ${path} ${res.status}`)
  return res.json()
}

async function apiPut(path: string, body: any) {
  const res = await fetch(`/api/v1/settings${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`PUT ${path} ${res.status}`)
  return res.json()
}

export default function TaxSettings() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [enabled, setEnabled] = useState<boolean>(true)
  const [defaultRatePct, setDefaultRatePct] = useState<string>('')

  useEffect(() => {
    let mounted = true
    ;(async () => {
      try {
        setError(null)
        // Prefer POS settings; fall back to fiscal
        const pos: PosSettings = await apiGet('/pos').catch(() => ({} as any))
        const fiscal: { tax?: TaxConfig } = await apiGet('/fiscal').catch(() => ({} as any))
        const tax = (pos?.tax ?? fiscal?.tax) || {}
        if (!mounted) return
        setEnabled(tax.enabled ?? true)
        const rate = tax.default_rate
        if (typeof rate === 'number') {
          // show as percentage 0..100 with up to 2 decimals
          setDefaultRatePct(String(rate > 1 ? rate : +(rate * 100).toFixed(2)))
        } else {
          setDefaultRatePct('')
        }
      } catch (e: any) {
        if (!mounted) return
        setError(e?.message || 'Error cargando configuración')
      } finally {
        if (mounted) setLoading(false)
      }
    })()
    return () => {
      mounted = false
    }
  }, [])

  const onSave = async () => {
    try {
      setSaving(true)
      setError(null)
      // Normalize percent to fraction 0..1
      let rateNum: number | undefined = undefined
      if (defaultRatePct !== '') {
        const n = Number(defaultRatePct)
        if (!Number.isFinite(n) || n < 0) throw new Error('Tasa inválida')
        rateNum = n > 1 ? n : n * 100 // store as percent (0..100) or fraction? backend acepta ambos
        // Para evitar ambigüedad, guardamos como porcentaje entero 0..100
        rateNum = n
      }

      const payload: PosSettings = { tax: { enabled } }
      if (rateNum !== undefined) payload.tax!.default_rate = rateNum
      await apiPut('/pos', payload)
    } catch (e: any) {
      setError(e?.message || 'Error guardando')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="admin-shell">
      <header className="admin-header">
        <h1 className="admin-title">Impuestos (POS)</h1>
        <p style={{ color: '#4b5563', margin: 0 }}>Control global de IVA/Impuestos por tenant.</p>
      </header>

      {loading ? (
        <p>Cargando…</p>
      ) : (
        <div className="admin-section" style={{ maxWidth: 720 }}>
          {error && (
            <div style={{ background: '#fee2e2', color: '#991b1b', padding: 12, borderRadius: 6, marginBottom: 12 }}>
              {error}
            </div>
          )}
          <div style={{ display: 'grid', gap: 16 }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <input
                type="checkbox"
                checked={enabled}
                onChange={(e) => setEnabled(e.target.checked)}
              />
              <span>Impuestos habilitados</span>
            </label>

            <label style={{ display: 'grid', gap: 6 }}>
              <span>Tasa por defecto (%)</span>
              <input
                type="number"
                min={0}
                step={0.01}
                value={defaultRatePct}
                onChange={(e) => setDefaultRatePct(e.target.value)}
                placeholder="0, 10, 21"
                disabled={!enabled}
                style={{ padding: 8, border: '1px solid #e5e7eb', borderRadius: 6 }}
              />
              <small style={{ color: '#6b7280' }}>
                Deja vacío para respetar la tasa por línea. Si la defines, se forzará en todos los tickets.
              </small>
            </label>

            <div style={{ display: 'flex', gap: 12 }}>
              <button
                onClick={onSave}
                disabled={saving}
                style={{ padding: '8px 14px', background: '#0ea5e9', color: 'white', borderRadius: 6 }}
              >
                {saving ? 'Guardando…' : 'Guardar cambios'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

