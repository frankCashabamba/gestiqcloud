import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useToast } from '../../shared/toast'
import { getCountryPack, updateCountryPack, type CountryPack } from './services'

function toJsonText(value: Record<string, unknown> | undefined) {
  if (!value || Object.keys(value).length === 0) return ''
  return JSON.stringify(value, null, 2)
}

function parseJsonOrEmpty(label: string, raw: string, showError: (msg: string) => void) {
  if (!raw.trim()) return undefined
  try {
    return JSON.parse(raw)
  } catch {
    showError(`${label} must be valid JSON`)
    return null
  }
}

export default function CountryPackDetail() {
  const { success, error: showError } = useToast()
  const navigate = useNavigate()
  const { code } = useParams()

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [pack, setPack] = useState<CountryPack | null>(null)
  const [name, setName] = useState('')
  const [region, setRegion] = useState('')
  const [currency, setCurrency] = useState('')
  const [active, setActive] = useState(false)
  const [validatorsJson, setValidatorsJson] = useState('')
  const [taxRulesJson, setTaxRulesJson] = useState('')

  const displayCode = useMemo(() => code || '', [code])

  useEffect(() => {
    if (!code) {
      setLoading(false)
      return
    }
    const load = async () => {
      setLoading(true)
      try {
        const data = await getCountryPack(code)
        setPack(data)
        setName(data.name || '')
        setRegion(data.region || '')
        setCurrency(data.currency || '')
        setActive(Boolean(data.active))
        setValidatorsJson(toJsonText(data.validators))
        setTaxRulesJson(toJsonText(data.tax_rules))
      } catch {
        showError('Error loading pack')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [code, showError])

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!code) return

    const validators = parseJsonOrEmpty('Validators', validatorsJson, showError)
    if (validators === null) return
    const taxRules = parseJsonOrEmpty('Tax rules', taxRulesJson, showError)
    if (taxRules === null) return

    setSaving(true)
    try {
      const updated = await updateCountryPack(code, {
        name,
        region,
        currency: currency || undefined,
        active,
        validators,
        tax_rules: taxRules,
      })
      setPack(updated)
      success('Paquete actualizado')
    } catch {
      showError('Error updating pack')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div className="p-6">Loading...</div>
  if (!pack) return <div className="p-6">Paquete no encontrado</div>

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Country Pack: {displayCode}</h1>
          <p className="text-sm text-gray-500">ID: {pack.id || '-'}</p>
        </div>
        <button
          onClick={() => navigate('/admin/country-packs')}
          className="px-4 py-2 bg-gray-200 rounded hover:bg-gray-300"
        >
          Volver
        </button>
      </div>

      <form onSubmit={handleSave} className="bg-white rounded-lg shadow p-6 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium">Nombre</label>
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              className="mt-1 w-full border rounded px-3 py-2"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium">Region</label>
            <input
              type="text"
              value={region}
              onChange={e => setRegion(e.target.value)}
              className="mt-1 w-full border rounded px-3 py-2"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium">Moneda</label>
            <input
              type="text"
              value={currency}
              onChange={e => setCurrency(e.target.value.toUpperCase())}
              className="mt-1 w-full border rounded px-3 py-2"
              maxLength={3}
            />
          </div>
          <div className="flex items-center gap-2 pt-6">
            <input
              id="active"
              type="checkbox"
              checked={active}
              onChange={e => setActive(e.target.checked)}
              className="h-4 w-4"
            />
            <label htmlFor="active" className="text-sm font-medium">
              Active
            </label>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium">Validadores (JSON)</label>
          <textarea
            value={validatorsJson}
            onChange={e => setValidatorsJson(e.target.value)}
            className="mt-1 w-full border rounded px-3 py-2 font-mono text-sm h-40"
            placeholder="{ }"
          />
        </div>

        <div>
          <label className="block text-sm font-medium">Reglas de impuestos (JSON)</label>
          <textarea
            value={taxRulesJson}
            onChange={e => setTaxRulesJson(e.target.value)}
            className="mt-1 w-full border rounded px-3 py-2 font-mono text-sm h-40"
            placeholder="{ }"
          />
        </div>

        <div className="flex gap-3">
          <button
            type="submit"
            disabled={saving}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? 'Guardando...' : 'Guardar'}
          </button>
        </div>
      </form>
    </div>
  )
}
