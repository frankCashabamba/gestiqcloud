import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useToast } from '../../shared/toast'
import { listCountryPacks, deleteCountryPack, CountryPack } from './services'

export default function CountryPacksList() {
  const { success, error: showError } = useToast()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [packs, setPacks] = useState<CountryPack[]>([])
  const [showForm, setShowForm] = useState(false)

  useEffect(() => {
    loadPacks()
  }, [])

  const loadPacks = async () => {
    setLoading(true)
    try {
      const data = await listCountryPacks()
      setPacks(data)
    } catch {
      showError('Error loading country packs')
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (code: string) => {
    if (!window.confirm('Delete this pack?')) return
    try {
      await deleteCountryPack(code)
      success('Pack deleted')
      loadPacks()
    } catch {
      showError('Error deleting pack')
    }
  }

  if (loading) return <div className="p-6">Loading...</div>

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Paquetes de País</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          {showForm ? 'Cancel' : 'New Pack'}
        </button>
      </div>

      {showForm && (
        <CountryPackForm
          onSuccess={() => {
            setShowForm(false)
            loadPacks()
          }}
        />
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {packs.length === 0 ? (
          <div className="col-span-full text-center py-12 text-gray-500">
            No hay paquetes de país configurados
          </div>
        ) : (
          packs.map(pack => (
            <div key={pack.code} className="bg-white rounded-lg shadow p-6">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="text-lg font-semibold">{pack.name}</h3>
                  <p className="text-sm text-gray-500">{pack.code}</p>
                </div>
                {pack.active && (
                  <span className="px-2 py-1 text-xs bg-green-100 text-green-800 rounded">Active</span>
                )}
              </div>

              <div className="space-y-2 text-sm mb-4">
                <p><strong>Región:</strong> {pack.region}</p>
                {pack.currency && <p><strong>Moneda:</strong> {pack.currency}</p>}
              </div>

              <div className="flex gap-2">
                <button
                  onClick={() => navigate(`/admin/country-packs/${pack.code}`)}
                  className="flex-1 px-3 py-2 text-sm bg-gray-200 rounded hover:bg-gray-300"
                >
                  Editar
                </button>
                <button
                  onClick={() => handleDelete(pack.code || '')}
                  className="flex-1 px-3 py-2 text-sm text-red-600 bg-red-50 rounded hover:bg-red-100"
                >
                  Delete
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

function CountryPackForm({ onSuccess }: { onSuccess: () => void }) {
  const { success, error: showError } = useToast()
  const [code, setCode] = useState('')
  const [name, setName] = useState('')
  const [region, setRegion] = useState('')
  const [currency, setCurrency] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!code || !name || !region) {
      showError('Campos requeridos: Código, Nombre, Región')
      return
    }

    setLoading(true)
    try {
      const { createCountryPack } = await import('./services')
      await createCountryPack({ code, name, region, currency: currency || undefined })
      success('Paquete creado')
      onSuccess()
    } catch {
      showError('Error creando paquete')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow p-6 space-y-4 max-w-md">
      <div>
        <label className="block text-sm font-medium">Código (ej: EC, AR, CL)</label>
        <input
          type="text"
          value={code}
          onChange={e => setCode(e.target.value.toUpperCase())}
          maxLength={3}
          className="mt-1 w-full border rounded px-3 py-2"
          required
        />
      </div>
      <div>
        <label className="block text-sm font-medium">Nombre</label>
        <input
          type="text"
          value={name}
          onChange={e => setName(e.target.value)}
          placeholder="ej: Ecuador"
          className="mt-1 w-full border rounded px-3 py-2"
          required
        />
      </div>
      <div>
        <label className="block text-sm font-medium">Región</label>
        <input
          type="text"
          value={region}
          onChange={e => setRegion(e.target.value)}
          placeholder="ej: South America"
          className="mt-1 w-full border rounded px-3 py-2"
          required
        />
      </div>
      <div>
        <label className="block text-sm font-medium">Moneda (opcional)</label>
        <input
          type="text"
          value={currency}
          onChange={e => setCurrency(e.target.value.toUpperCase())}
          placeholder="ej: USD"
          maxLength={3}
          className="mt-1 w-full border rounded px-3 py-2"
        />
      </div>
      <button
        type="submit"
        disabled={loading}
        className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
      >
        {loading ? 'Creando...' : 'Crear'}
      </button>
    </form>
  )
}
