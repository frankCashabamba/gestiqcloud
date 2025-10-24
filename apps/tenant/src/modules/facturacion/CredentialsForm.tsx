/**
 * Credentials Form - Configuración de certificados e-factura
 */
import React, { useState, useEffect } from 'react'
import { getCredentials, updateCredentials, type Credentials } from './services'

export default function CredentialsForm() {
  const [country, setCountry] = useState<'ES' | 'EC'>('EC')
  const [credentials, setCredentials] = useState<Credentials | null>(null)
  const [sandbox, setSandbox] = useState(true)
  const [certFile, setCertFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadCredentials()
  }, [country])

  const loadCredentials = async () => {
    try {
      const data = await getCredentials(country)
      setCredentials(data)
      setSandbox(data.sandbox)
    } catch (err) {
      console.error(err)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    try {
      setLoading(true)
      await updateCredentials(country, sandbox, certFile || undefined)
      alert('Credenciales actualizadas')
      loadCredentials()
    } catch (err: any) {
      alert(err.message || 'Error al actualizar')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl space-y-6">
      <h2 className="text-2xl font-bold">Certificados E-Factura</h2>

      <form onSubmit={handleSubmit} className="rounded-xl border bg-white p-6 shadow-sm">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium">País</label>
            <select
              value={country}
              onChange={(e) => setCountry(e.target.value as 'ES' | 'EC')}
              className="mt-1 block w-full rounded-lg border px-3 py-2"
            >
              <option value="EC">Ecuador (SRI)</option>
              <option value="ES">España (SII)</option>
            </select>
          </div>

          {credentials && (
            <div className={`rounded-lg p-4 ${credentials.has_certificate ? 'bg-green-50' : 'bg-amber-50'}`}>
              <p className="text-sm font-medium">
                {credentials.has_certificate ? '✅ Certificado configurado' : '⚠️ Sin certificado'}
              </p>
              {credentials.last_updated && (
                <p className="mt-1 text-xs text-slate-600">
                  Actualizado: {new Date(credentials.last_updated).toLocaleString('es-ES')}
                </p>
              )}
            </div>
          )}

          <div className="flex items-center">
            <input
              type="checkbox"
              id="sandbox"
              checked={sandbox}
              onChange={(e) => setSandbox(e.target.checked)}
              className="h-4 w-4 rounded"
            />
            <label htmlFor="sandbox" className="ml-2 text-sm">
              Modo Sandbox (pruebas)
            </label>
          </div>

          <div>
            <label className="block text-sm font-medium">
              Certificado (.p12/.pfx)
            </label>
            <input
              type="file"
              accept=".p12,.pfx"
              onChange={(e) => setCertFile(e.target.files?.[0] || null)}
              className="mt-1 block w-full text-sm"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-blue-600 px-6 py-3 font-medium text-white hover:bg-blue-500 disabled:bg-slate-300"
          >
            {loading ? 'Guardando...' : 'Guardar Configuración'}
          </button>
        </div>
      </form>
    </div>
  )
}
