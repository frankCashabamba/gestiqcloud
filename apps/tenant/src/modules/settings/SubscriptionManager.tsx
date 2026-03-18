import React, { useEffect, useState } from 'react'
import tenantApi from '../../shared/api/client'
import { useToast } from '../../shared/toast'

interface Plan {
  id: string
  name: string
  display_name: string | null
  price_monthly: number
  price_yearly: number | null
  max_users: number
  max_branches: number
  included_modules: string[]
  features: Record<string, any>
}

interface Subscription {
  id: string
  plan: Plan | null
  status: string
  billing_cycle: string
  current_period_start: string | null
  current_period_end: string | null
  trial_ends_at: string | null
  canceled_at: string | null
}

export default function SubscriptionManager() {
  const { success, error: showError } = useToast()
  const [plans, setPlans] = useState<Plan[]>([])
  const [subscription, setSubscription] = useState<Subscription | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      tenantApi.get('/api/v1/tenant/billing/plans').then(r => r.data).catch(() => []),
      tenantApi.get('/api/v1/tenant/billing/subscription').then(r => r.data).catch(() => null),
    ]).then(([p, s]) => {
      setPlans(p)
      setSubscription(s)
    }).finally(() => setLoading(false))
  }, [])

  const handleSubscribe = async (planId: string) => {
    try {
      await tenantApi.post('/api/v1/tenant/billing/subscribe', { plan_id: planId, billing_cycle: 'monthly' })
      success('Suscripción activada')
      window.location.reload()
    } catch {
      showError('Error al suscribirse')
    }
  }

  const handleChangePlan = async (planId: string) => {
    try {
      await tenantApi.post('/api/v1/tenant/billing/change-plan', { new_plan_id: planId })
      success('Plan actualizado')
      window.location.reload()
    } catch {
      showError('Error al cambiar plan')
    }
  }

  const handleCancel = async () => {
    if (!confirm('¿Cancelar suscripción? Podrás seguir usando el sistema hasta fin del período.')) return
    try {
      await tenantApi.post('/api/v1/tenant/billing/cancel')
      success('Suscripción cancelada')
      window.location.reload()
    } catch {
      showError('Error al cancelar')
    }
  }

  if (loading) return <div className="p-6">Cargando...</div>

  const currentPlanId = subscription?.plan?.id

  const statusBadge: Record<string, string> = {
    active: 'bg-green-100 text-green-800',
    trialing: 'bg-blue-100 text-blue-800',
    canceled: 'bg-red-100 text-red-800',
    past_due: 'bg-yellow-100 text-yellow-800',
  }

  return (
    <div className="p-6 space-y-6">
      <h2 className="text-2xl font-bold">💳 Suscripción y Planes</h2>

      {subscription && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex justify-between items-start">
            <div>
              <h3 className="text-lg font-semibold">Plan actual: {subscription.plan?.display_name || subscription.plan?.name || 'Sin plan'}</h3>
              <span className={`inline-block mt-1 px-2 py-0.5 rounded-full text-xs font-medium ${statusBadge[subscription.status] || 'bg-gray-100'}`}>
                {subscription.status}
              </span>
              <p className="text-sm text-gray-500 mt-2">
                Ciclo: {subscription.billing_cycle === 'yearly' ? 'Anual' : 'Mensual'}
              </p>
              {subscription.current_period_end && (
                <p className="text-sm text-gray-500">
                  Próxima renovación: {new Date(subscription.current_period_end).toLocaleDateString()}
                </p>
              )}
              {subscription.trial_ends_at && (
                <p className="text-sm text-blue-600">
                  Prueba hasta: {new Date(subscription.trial_ends_at).toLocaleDateString()}
                </p>
              )}
            </div>
            {subscription.status !== 'canceled' && (
              <button onClick={handleCancel} className="text-sm text-red-600 hover:underline">
                Cancelar suscripción
              </button>
            )}
          </div>
          {subscription.plan && (
            <div className="mt-4 text-sm text-gray-600">
              <p>Usuarios máx: {subscription.plan.max_users} | Sucursales máx: {subscription.plan.max_branches}</p>
              <p>Módulos: {subscription.plan.included_modules.join(', ') || 'Todos'}</p>
            </div>
          )}
        </div>
      )}

      <h3 className="text-xl font-semibold">Planes disponibles</h3>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {plans.map(plan => {
          const isCurrent = plan.id === currentPlanId
          return (
            <div key={plan.id} className={`bg-white rounded-lg shadow p-6 border-2 ${isCurrent ? 'border-blue-500' : 'border-transparent'}`}>
              <h4 className="text-lg font-bold">{plan.display_name || plan.name}</h4>
              <p className="text-3xl font-bold mt-2">
                ${plan.price_monthly}<span className="text-sm font-normal text-gray-500">/mes</span>
              </p>
              {plan.price_yearly && (
                <p className="text-sm text-gray-500">${plan.price_yearly}/año</p>
              )}
              <div className="mt-4 space-y-2 text-sm">
                <p>👤 Hasta {plan.max_users} usuarios</p>
                <p>🏢 Hasta {plan.max_branches} sucursales</p>
                {plan.included_modules.length > 0 && (
                  <div>
                    <p className="font-medium">Módulos incluidos:</p>
                    <ul className="list-disc list-inside text-gray-600">
                      {plan.included_modules.map(m => <li key={m}>{m}</li>)}
                    </ul>
                  </div>
                )}
              </div>
              <div className="mt-6">
                {isCurrent ? (
                  <span className="block text-center py-2 bg-blue-100 text-blue-800 rounded font-medium">Plan actual</span>
                ) : subscription ? (
                  <button
                    onClick={() => handleChangePlan(plan.id)}
                    className="w-full py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                  >
                    Cambiar a este plan
                  </button>
                ) : (
                  <button
                    onClick={() => handleSubscribe(plan.id)}
                    className="w-full py-2 bg-green-600 text-white rounded hover:bg-green-700"
                  >
                    Suscribirse
                  </button>
                )}
              </div>
            </div>
          )
        })}
        {plans.length === 0 && (
          <p className="col-span-3 text-center text-gray-500 py-8">No hay planes disponibles</p>
        )}
      </div>
    </div>
  )
}
