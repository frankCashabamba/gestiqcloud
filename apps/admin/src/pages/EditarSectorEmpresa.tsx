import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import api from '../utils/axios'
import SectorPlantillaSelector from '../components/SectorPlantillaSelector'

interface Empresa {
  id: string
  name: string
  sector_plantilla_actual?: number | null
  config_json?: any
}

export const EditarSectorEmpresa: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  
  const [empresa, setEmpresa] = useState<Empresa | null>(null)
  const [selectedSector, setSelectedSector] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [applying, setApplying] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    const fetchEmpresa = async () => {
      try {
        setLoading(true)
        const response = await api.get(`/v1/admin/empresas/${id}`)
        setEmpresa(response.data)
        setSelectedSector(response.data.sector_plantilla_actual || null)
      } catch (err: any) {
        setError('Error cargando datos de la empresa')
      } finally {
        setLoading(false)
      }
    }

    if (id) {
      fetchEmpresa()
    }
  }, [id])

  const handleApply = async () => {
    if (!selectedSector || !empresa) {
      setError('Debes seleccionar una plantilla de sector')
      return
    }

    try {
      setApplying(true)
      setError(null)
      setSuccess(null)

      await api.post('/v1/sectors/apply', {
        tenant_id: empresa.id,
        sector_plantilla_id: selectedSector,
        override_existing: true
      })

      setSuccess('¡Plantilla aplicada exitosamente! La configuración de la empresa ha sido actualizada.')
      
      setTimeout(() => {
        navigate('/admin/empresas')
      }, 2000)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error aplicando la plantilla')
    } finally {
      setApplying(false)
    }
  }

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="text-center py-12">
          <div className="spinner"></div>
          <p className="mt-4 text-slate-600">Cargando datos de la empresa...</p>
        </div>
      </div>
    )
  }

  if (!empresa) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          Empresa no encontrada
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="bg-white rounded-3xl shadow-sm border border-slate-200">
        {/* Header */}
        <header className="px-6 py-5 border-b border-slate-200">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-semibold text-slate-900">
                Cambiar Sector de Empresa
              </h1>
              <p className="text-slate-500 text-sm mt-1">
                Empresa: <strong>{empresa.name}</strong>
              </p>
            </div>
            <button
              onClick={() => navigate('/admin/empresas')}
              className="text-slate-600 hover:text-slate-900"
            >
              ← Volver
            </button>
          </div>
        </header>

        {/* Content */}
        <div className="px-6 py-6">
          {/* Alerts */}
          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
              ⚠️ {error}
            </div>
          )}

          {success && (
            <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg text-green-700">
              ✓ {success}
            </div>
          )}

          {/* Warning */}
          <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
            <h3 className="font-semibold text-yellow-900 mb-2">
              ⚠️ Importante
            </h3>
            <p className="text-sm text-yellow-800">
              Al cambiar el sector de la empresa se aplicará la siguiente configuración:
            </p>
            <ul className="mt-2 text-sm text-yellow-800 list-disc list-inside space-y-1">
              <li>Se actualizará el branding (color primario, plantilla dashboard)</li>
              <li>Se habilitarán/deshabilitarán módulos según la plantilla</li>
              <li>Se crearán nuevas categorías predefinidas</li>
              <li>Se actualizará la configuración de POS e inventario</li>
            </ul>
            <p className="mt-2 text-sm text-yellow-800 font-semibold">
              Esta acción sobrescribirá la configuración actual.
            </p>
          </div>

          {/* Selector */}
          <SectorPlantillaSelector
            value={selectedSector}
            onChange={setSelectedSector}
            disabled={applying}
          />

          {/* Actions */}
          <div className="mt-8 flex gap-4 justify-end">
            <button
              onClick={() => navigate('/admin/empresas')}
              disabled={applying}
              className="px-6 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            >
              Cancelar
            </button>
            <button
              onClick={handleApply}
              disabled={!selectedSector || applying}
              className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {applying ? 'Aplicando...' : 'Aplicar Cambios'}
            </button>
          </div>
        </div>
      </div>

      <style>{`
        .spinner {
          width: 40px;
          height: 40px;
          margin: 0 auto;
          border: 4px solid #f3f4f6;
          border-top-color: #3b82f6;
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}

export default EditarSectorEmpresa
