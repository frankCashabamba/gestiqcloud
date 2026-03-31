import React from 'react'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import VentasRoutes from './Routes'

vi.mock('../../auth/ProtectedRoute', () => ({
  default: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

vi.mock('../../components/PermissionDenied', () => ({
  default: () => <div>Permission denied</div>,
}))

vi.mock('./List', () => ({
  default: () => <div>Sales list</div>,
}))

vi.mock('./Form', () => ({
  default: () => <div>Sales form</div>,
}))

vi.mock('./Detail', () => ({
  default: () => <div>Sales detail</div>,
}))

describe('VentasRoutes', () => {
  it('renders promotions placeholder instead of treating promotions as a sale id', () => {
    render(
      <MemoryRouter initialEntries={['/acme/sales/promotions']}>
        <Routes>
          <Route path="/:empresa/sales/*" element={<VentasRoutes />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByRole('heading', { name: 'Promotions' })).toBeInTheDocument()
    expect(screen.queryByText('Sales detail')).not.toBeInTheDocument()
  })
})
