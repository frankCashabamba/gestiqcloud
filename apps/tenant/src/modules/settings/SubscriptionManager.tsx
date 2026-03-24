import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { TENANT_BILLING } from '@shared/endpoints'
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
  const { t } = useTranslation(['settings', 'common'])
  const { success, error: showError } = useToast()
  const [plans, setPlans] = useState<Plan[]>([])
  const [subscription, setSubscription] = useState<Subscription | null>(null)
  const [loading, setLoading] = useState(true)
  const [billingCycle, setBillingCycle] = useState<'monthly' | 'yearly'>('monthly')
  const [cancelPending, setCancelPending] = useState(false)

  useEffect(() => {
    Promise.all([
      tenantApi.get(TENANT_BILLING.plans).then(r => r.data).catch(() => []),
      tenantApi.get(TENANT_BILLING.subscription).then(r => r.data).catch(() => null),
    ])
      .then(([p, s]) => {
        setPlans(p)
        setSubscription(s)
        setBillingCycle(s?.billing_cycle === 'yearly' ? 'yearly' : 'monthly')
      })
      .finally(() => setLoading(false))
  }, [])

  const handleSubscribe = async (planId: string) => {
    try {
      const { data } = await tenantApi.post(TENANT_BILLING.subscribe, {
        plan_id: planId,
        billing_cycle: billingCycle,
        return_url: window.location.href,
      })
      if (data?.checkout_url) {
        window.location.href = data.checkout_url
        return
      }
      success(t('settings:subscription.activated'))
      window.location.reload()
    } catch {
      showError(t('settings:subscription.errorSubscribe'))
    }
  }

  const handleChangePlan = async (planId: string) => {
    try {
      await tenantApi.post(TENANT_BILLING.changePlan, {
        new_plan_id: planId,
        billing_cycle: billingCycle,
      })
      success(t('settings:subscription.planUpdated'))
      window.location.reload()
    } catch {
      showError(t('settings:subscription.errorChangePlan'))
    }
  }

  const handleCancel = async () => {
    try {
      await tenantApi.post(TENANT_BILLING.cancel)
      success(t('settings:subscription.canceled'))
      window.location.reload()
    } catch {
      showError(t('settings:subscription.errorCancel'))
    } finally {
      setCancelPending(false)
    }
  }

  const handleOpenPortal = async () => {
    try {
      const { data } = await tenantApi.post(TENANT_BILLING.portal, { return_url: window.location.href })
      if (data?.portal_url) {
        window.location.href = data.portal_url
        return
      }
      showError(t('settings:subscription.noPortal'))
    } catch {
      showError(t('settings:subscription.errorPortal'))
    }
  }

  if (loading) return <div className="p-6">{t('settings:subscription.loading')}</div>

  const currentPlanId = subscription?.plan?.id

  const statusBadge: Record<string, string> = {
    active: 'bg-green-100 text-green-800',
    trialing: 'bg-blue-100 text-blue-800',
    canceled: 'bg-red-100 text-red-800',
    past_due: 'bg-yellow-100 text-yellow-800',
  }

  return (
    <div className="p-6 space-y-6">
      <h2 className="text-2xl font-bold">{t('settings:subscription.title')}</h2>

      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-medium text-gray-700">{t('settings:subscription.cycle')}</span>
        <button
          onClick={() => setBillingCycle('monthly')}
          className={`rounded-full px-3 py-1 text-sm ${billingCycle === 'monthly' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700'}`}
        >
          {t('settings:subscription.monthly')}
        </button>
        <button
          onClick={() => setBillingCycle('yearly')}
          className={`rounded-full px-3 py-1 text-sm ${billingCycle === 'yearly' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700'}`}
        >
          {t('settings:subscription.yearly')}
        </button>
      </div>

      {subscription && (
        <div className="rounded-lg bg-white p-6 shadow">
          <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
            <div>
              <h3 className="text-lg font-semibold">
                {subscription.plan?.display_name || subscription.plan?.name || t('settings:subscription.noPlan')}
              </h3>
              <span className={`mt-1 inline-block rounded-full px-2 py-0.5 text-xs font-medium ${statusBadge[subscription.status] || 'bg-gray-100'}`}>
                {subscription.status}
              </span>
              <p className="mt-2 text-sm text-gray-500">
                {t('settings:subscription.cycle')} {subscription.billing_cycle === 'yearly'
                  ? t('settings:subscription.cycleYearly')
                  : t('settings:subscription.cycleMonthly')}
              </p>
              {subscription.current_period_end && (
                <p className="text-sm text-gray-500">
                  {t('settings:subscription.nextRenewal')} {new Date(subscription.current_period_end).toLocaleDateString()}
                </p>
              )}
              {subscription.trial_ends_at && (
                <p className="text-sm text-blue-600">
                  {t('settings:subscription.trialUntil')} {new Date(subscription.trial_ends_at).toLocaleDateString()}
                </p>
              )}
            </div>
            <div className="flex flex-col items-start gap-2 md:items-end">
              <button onClick={handleOpenPortal} className="text-sm text-blue-600 hover:underline">
                {t('settings:subscription.billingPortal')}
              </button>
              {subscription.status !== 'canceled' && (
                <button onClick={() => setCancelPending(true)} className="text-sm text-red-600 hover:underline">
                  {t('settings:subscription.cancelSub')}
                </button>
              )}
            </div>
          </div>
          {subscription.plan && (
            <div className="mt-4 text-sm text-gray-600">
              <p>
                {t('settings:subscription.maxUsersInfo', { count: subscription.plan.max_users })} |{' '}
                {t('settings:subscription.maxBranchesInfo', { count: subscription.plan.max_branches })}
              </p>
              <p>{t('settings:subscription.includedModulesLabel')} {subscription.plan.included_modules.join(', ') || t('settings:subscription.allModules')}</p>
            </div>
          )}
        </div>
      )}

      <h3 className="text-xl font-semibold">{t('settings:subscription.availablePlans')}</h3>
      <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
        {plans.map(plan => {
          const isCurrent = plan.id === currentPlanId
          const displayedPrice = billingCycle === 'yearly' ? (plan.price_yearly ?? plan.price_monthly) : plan.price_monthly
          return (
            <div key={plan.id} className={`rounded-lg border-2 bg-white p-6 shadow ${isCurrent ? 'border-blue-500' : 'border-transparent'}`}>
              <h4 className="text-lg font-bold">{plan.display_name || plan.name}</h4>
              <p className="mt-2 text-3xl font-bold">
                ${displayedPrice}
                <span className="text-sm font-normal text-gray-500">
                  {billingCycle === 'yearly' ? t('settings:subscription.perYear') : t('settings:subscription.perMonth')}
                </span>
              </p>
              {plan.price_yearly && (
                <p className="text-sm text-gray-500">${plan.price_yearly}{t('settings:subscription.perYear')}</p>
              )}
              <div className="mt-4 space-y-2 text-sm">
                <p>{t('settings:subscription.maxUsersInfo', { count: plan.max_users })}</p>
                <p>{t('settings:subscription.maxBranchesInfo', { count: plan.max_branches })}</p>
                {plan.included_modules.length > 0 && (
                  <div>
                    <p className="font-medium">{t('settings:subscription.includedModulesLabel')}</p>
                    <ul className="list-inside list-disc text-gray-600">
                      {plan.included_modules.map(moduleName => <li key={moduleName}>{moduleName}</li>)}
                    </ul>
                  </div>
                )}
              </div>
              <div className="mt-6">
                {isCurrent ? (
                  <span className="block rounded bg-blue-100 py-2 text-center font-medium text-blue-800">
                    {t('settings:subscription.currentPlanBadge')}
                  </span>
                ) : subscription ? (
                  <button
                    onClick={() => handleChangePlan(plan.id)}
                    className="w-full rounded bg-blue-600 py-2 text-white hover:bg-blue-700"
                  >
                    {t('settings:subscription.changePlan')}
                  </button>
                ) : (
                  <button
                    onClick={() => handleSubscribe(plan.id)}
                    className="w-full rounded bg-green-600 py-2 text-white hover:bg-green-700"
                  >
                    {t('settings:subscription.subscribe')}
                  </button>
                )}
              </div>
            </div>
          )
        })}
        {plans.length === 0 && (
          <p className="col-span-3 py-8 text-center text-gray-500">{t('settings:subscription.noPlans')}</p>
        )}
      </div>

      {cancelPending && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-sm">
            <h3 className="font-semibold text-lg mb-2">{t('settings:subscription.confirmCancelTitle')}</h3>
            <p className="text-sm text-slate-600 mb-4">{t('settings:subscription.confirmCancelMsg')}</p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setCancelPending(false)} className="px-4 py-2 rounded bg-slate-200 hover:bg-slate-300 text-sm">
                {t('settings:subscription.back')}
              </button>
              <button onClick={handleCancel} className="px-4 py-2 rounded bg-red-600 text-white hover:bg-red-700 text-sm">
                {t('settings:subscription.confirmCancel')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
