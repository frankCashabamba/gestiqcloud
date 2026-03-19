import '@testing-library/jest-dom/vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

import ModuleLoader from './ModuleLoader'

const useMisModulosMock = vi.fn()

vi.mock('../hooks/useMisModulos', () => ({
  useMisModulos: () => useMisModulosMock(),
}))

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}))

describe('ModuleLoader', () => {
  it('blocks finance aliases even when the canonical module is enabled', async () => {
    useMisModulosMock.mockReturnValue({
      allowedSlugs: new Set(['finance']),
      loading: false,
    })

    render(
      <MemoryRouter initialEntries={['/m/finanzas']}>
        <Routes>
          <Route path="/m/:mod/*" element={<ModuleLoader />} />
          <Route path="/unauthorized" element={<div>Unauthorized</div>} />
        </Routes>
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('Unauthorized')).toBeInTheDocument()
    })
  })
})
