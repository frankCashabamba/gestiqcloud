import '@testing-library/jest-dom/vitest'
import React from 'react'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

vi.mock('../components/ImportIntake', () => ({
  default: (props: {
    initialForceReprocess?: boolean
    initialReprocessMode?: string
    initialRecipeSnapshotId?: string
    compact?: boolean
  }) => (
    <div
      data-testid="import-intake"
      data-force={String(props.initialForceReprocess)}
      data-mode={props.initialReprocessMode || ''}
      data-snapshot={props.initialRecipeSnapshotId || ''}
      data-compact={String(props.compact)}
    />
  ),
}))

import ImportPage from './ImportPage'

describe('ImportPage', () => {
  it('opens deep reprocess mode with explicit copy and props', () => {
    render(
      <MemoryRouter initialEntries={['/importar?reimport=deep&recipeSnapshotId=snap-1']}>
        <Routes>
          <Route path="/importar" element={<ImportPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByRole('heading', { name: 'Revisión profunda' })).toBeInTheDocument()
    expect(screen.getByText(/ignorar cachés/i)).toBeInTheDocument()

    const intake = screen.getByTestId('import-intake')
    expect(intake).toHaveAttribute('data-force', 'true')
    expect(intake).toHaveAttribute('data-mode', 'deep')
    expect(intake).toHaveAttribute('data-snapshot', 'snap-1')
    expect(intake).toHaveAttribute('data-compact', 'true')
  })
})
