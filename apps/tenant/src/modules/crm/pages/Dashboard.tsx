import { useEffect, useState } from 'react'
import { TrendingUp, Users, Target, DollarSign } from 'lucide-react'
import { getDashboard } from '../services'
import { useToast, getErrorMessage } from '../../../shared/toast'
import type { CRMDashboard } from '../types'

export default function CRMDashboard() {
  const [metrics, setMetrics] = useState<CRMDashboard | null>(null)
  const [loading, setLoading] = useState(true)
  const { error } = useToast()

  useEffect(() => {
    (async () => {
      try {
        setLoading(true)
        const data = await getDashboard()
        setMetrics(data)
      } catch (e) {
        error(getErrorMessage(e))
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  if (loading) return <div className="p-4 text-gray-500">Cargando métricas...</div>

  if (!metrics) return <div className="p-4">No hay datos disponibles</div>

  const leadsByStatus = Object.entries(metrics.leads.by_status ?? {}) as Array<[string, number]>
  const opportunitiesByStage = Object.entries(metrics.opportunities.by_stage ?? {}) as Array<[string, number]>
  const wonOpportunities = metrics.opportunities.by_stage?.closed_won ?? 0
  const lostOpportunities = metrics.opportunities.by_stage?.closed_lost ?? 0

  return (
    <div className="p-4">
      <h2 className="text-2xl font-bold mb-6">CRM Dashboard</h2>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="bg-white p-4 rounded-lg shadow border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Total Leads</p>
              <p className="text-3xl font-bold text-blue-600">{metrics.leads.total}</p>
            </div>
            <Users className="text-blue-600" size={40} />
          </div>
        </div>

        <div className="bg-white p-4 rounded-lg shadow border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Oportunidades</p>
              <p className="text-3xl font-bold text-green-600">{metrics.opportunities.total}</p>
            </div>
            <Target className="text-green-600" size={40} />
          </div>
        </div>

        <div className="bg-white p-4 rounded-lg shadow border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Pipeline Value</p>
              <p className="text-3xl font-bold text-purple-600">€{metrics.opportunities.total_value.toFixed(2)}</p>
            </div>
            <DollarSign className="text-purple-600" size={40} />
          </div>
        </div>

        <div className="bg-white p-4 rounded-lg shadow border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Tasa Conversión</p>
              <p className="text-3xl font-bold text-orange-600">{metrics.opportunities.win_rate.toFixed(1)}%</p>
            </div>
            <TrendingUp className="text-orange-600" size={40} />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white p-4 rounded-lg shadow border">
          <h3 className="font-semibold mb-4">Leads por Estado</h3>
          <div className="space-y-2">
            {leadsByStatus.map(([status, count]) => (
              <div key={status} className="flex justify-between items-center">
                <span className="text-sm capitalize">{status}</span>
                <span className="font-semibold text-gray-700">{count}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white p-4 rounded-lg shadow border">
          <h3 className="font-semibold mb-4">Oportunidades por Etapa</h3>
          <div className="space-y-2">
            {opportunitiesByStage.map(([stage, count]) => (
              <div key={stage} className="flex justify-between items-center">
                <span className="text-sm capitalize">{stage.replace(/_/g, ' ')}</span>
                <span className="font-semibold text-gray-700">{count}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-green-50 p-4 rounded-lg border border-green-200">
          <p className="text-sm text-green-700">Ganadas</p>
          <p className="text-2xl font-bold text-green-800">{wonOpportunities}</p>
        </div>

        <div className="bg-red-50 p-4 rounded-lg border border-red-200">
          <p className="text-sm text-red-700">Perdidas</p>
          <p className="text-2xl font-bold text-red-800">{lostOpportunities}</p>
        </div>
      </div>
    </div>
  )
}
