import '@testing-library/jest-dom/vitest'
import { render, screen } from '@testing-library/react'
import type { ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'

import DefaultPlantilla from '../default'

vi.mock('../../hooks/useMisModulos', () => ({
  useMisModulos: () => ({
    modules: [],
    visibleModules: [],
    allowedSlugs: new Set(['sales', 'expenses', 'invoicing']),
  }),
}))

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}))

vi.mock('../components/SectorLayout', () => ({
  default: ({ kpis, children }: { kpis: ReactNode[]; children: ReactNode }) => (
    <div>
      <div>{kpis}</div>
      <div>{children}</div>
    </div>
  ),
}))

describe('DefaultPlantilla', () => {
  it('renders KPI cards for canonical sales, expenses and invoicing modules', () => {
    render(
      <MemoryRouter>
        <DefaultPlantilla />
      </MemoryRouter>,
    )

    expect(screen.getByText('defaultDashboard.kpis.sales.title')).toBeInTheDocument()
    expect(screen.getByText('defaultDashboard.kpis.expenses.title')).toBeInTheDocument()
    expect(screen.getByText('defaultDashboard.kpis.invoices.title')).toBeInTheDocument()
  })
})
