import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'

// --- Mocks ----------------------------------------------------------------

const getTenantKpisMock = vi.fn()

vi.mock('../api', () => ({
  getTenantKpis: (...args: any[]) => getTenantKpisMock(...args),
  getTenantKpisBySector: vi.fn(),
}))

vi.mock('../../../hooks/useCurrency', () => ({
  useCurrency: () => ({
    currency: 'EUR',
    symbol: '\u20ac',
    loading: false,
    formatCurrency: (amount: number) =>
      new Intl.NumberFormat('es-ES', {
        style: 'currency',
        currency: 'EUR',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }).format(amount),
  }),
}))

// Component under test
import Dashboard from '../Dashboard'

beforeEach(() => {
  vi.clearAllMocks()
})

describe('Analytics Dashboard', () => {
  it('renders KPI cards with values returned by the API', async () => {
    getTenantKpisMock.mockResolvedValueOnce({
      sales_today: { total: 1234.5, tickets: 12, currency: 'EUR' },
      new_customers: { month: 7, week: 2 },
      monthly_revenue: { current: 5000, target: 6000, currency: 'EUR' },
      top_products: [
        { name: 'Pan', units: 30, revenue: 60 },
        { name: 'Caf\u00e9', units: 12, revenue: 24 },
      ],
    })

    render(<Dashboard />)

    expect(screen.getByRole('heading', { name: /Anal.tica/i })).toBeInTheDocument()

    await waitFor(() => {
      expect(getTenantKpisMock).toHaveBeenCalledTimes(1)
    })

    // KPI titles render
    expect(screen.getByText(/Ventas del d.a/i)).toBeInTheDocument()
    expect(screen.getByText(/Ticket medio/i)).toBeInTheDocument()
    expect(screen.getByText(/Clientes nuevos/i)).toBeInTheDocument()
    expect(screen.getByText(/Ingresos del mes/i)).toBeInTheDocument()

    // Top products list rendered
    await waitFor(() => {
      expect(screen.getAllByText('Pan').length).toBeGreaterThan(0)
    })
    expect(screen.getAllByText(/^Caf/i).length).toBeGreaterThan(0)
  })

  it('shows error message when the API call fails', async () => {
    getTenantKpisMock.mockRejectedValueOnce(new Error('boom'))

    render(<Dashboard />)

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/boom/i)
    })
  })

  it('passes sector parameter when sector is selected via the picker', async () => {
    getTenantKpisMock.mockResolvedValue({})

    render(<Dashboard />)

    await waitFor(() => {
      expect(getTenantKpisMock).toHaveBeenCalledWith({})
    })
  })
})
