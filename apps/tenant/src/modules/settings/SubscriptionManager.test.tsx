import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { TENANT_BILLING } from '@shared/endpoints'
import SubscriptionManager from './SubscriptionManager'

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const messages: Record<string, string> = {
        'subscription.title': 'Suscripción',
        'subscription.cycle': 'Ciclo de facturación',
        'subscription.monthly': 'Mensual',
        'subscription.yearly': 'Anual',
        'subscription.availablePlans': 'Planes disponibles',
        'subscription.perMonth': '/mes',
        'subscription.perYear': '/año',
        'subscription.maxUsersInfo': 'Usuarios',
        'subscription.maxBranchesInfo': 'Sucursales',
        'subscription.includedModulesLabel': 'Módulos incluidos',
        'subscription.subscribe': 'Suscribirse',
      }
      const shortKey = key.includes(':') ? key.split(':').slice(1).join(':') : key
      return messages[shortKey] ?? key
    },
  }),
}))

const getMock = vi.fn()
const postMock = vi.fn()
const successMock = vi.fn()
const errorMock = vi.fn()
const reloadMock = vi.fn()

vi.mock('../../shared/api/client', () => ({
  default: {
    get: (...args: unknown[]) => getMock(...args),
    post: (...args: unknown[]) => postMock(...args),
  },
}))

vi.mock('../../shared/toast', () => ({
  useToast: () => ({
    success: successMock,
    error: errorMock,
  }),
}))

describe('SubscriptionManager', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getMock.mockImplementation((url: string) => {
      if (url === TENANT_BILLING.plans) {
        return Promise.resolve({
          data: [
            {
              id: 'plan-pro',
              name: 'pro',
              display_name: 'Pro',
              price_monthly: 29,
              price_yearly: 290,
              max_users: 10,
              max_branches: 3,
              included_modules: ['sales'],
              features: {},
            },
          ],
        })
      }
      if (url === TENANT_BILLING.subscription) {
        return Promise.resolve({ data: null })
      }
      return Promise.reject(new Error(`Unexpected GET ${url}`))
    })

    Object.defineProperty(window, 'location', {
      writable: true,
      value: {
        href: 'http://localhost:5173/settings/subscription',
        reload: reloadMock,
      },
    })
  })

  it('redirects to Stripe checkout when subscribe returns checkout_url', async () => {
    postMock.mockResolvedValue({
      data: {
        mode: 'stripe_checkout',
        checkout_url: 'https://checkout.example/session',
      },
    })

    render(<SubscriptionManager />)

    await screen.findByText('Planes disponibles')
    await userEvent.click(screen.getByRole('button', { name: 'Anual' }))
    await userEvent.click(screen.getByRole('button', { name: 'Suscribirse' }))

    await waitFor(() => {
      expect(postMock).toHaveBeenCalledWith(
        TENANT_BILLING.subscribe,
        expect.objectContaining({
          plan_id: 'plan-pro',
          billing_cycle: 'yearly',
          return_url: 'http://localhost:5173/settings/subscription',
        }),
      )
    })
    expect(window.location.href).toBe('https://checkout.example/session')
    expect(reloadMock).not.toHaveBeenCalled()
  })
})
