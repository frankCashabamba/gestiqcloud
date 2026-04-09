import '@testing-library/jest-dom/vitest'
import React from 'react'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        'reprocessPage.deepTitle': 'Deep review',
        'reprocessPage.fastTitle': 'Fast reprocess',
        'reprocessPage.deepDescription': 'Ignore OCR and AI caches and try to recover more data from scratch.',
        'reprocessPage.fastDescription': 'Reprocess the original file using the current fast path.',
        'reprocessPage.deepNotice': 'Deep mode takes longer and is the only path prepared for premium providers later.',
        'reprocessPage.fastNotice': 'Fast mode keeps the current flow and may return a similar result.',
      }
      return translations[key] || key
    },
  }),
}))

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

    expect(screen.getByRole('heading', { name: 'Deep review' })).toBeInTheDocument()
    expect(screen.getByText(/ignore OCR and AI caches/i)).toBeInTheDocument()

    const intake = screen.getByTestId('import-intake')
    expect(intake).toHaveAttribute('data-force', 'true')
    expect(intake).toHaveAttribute('data-mode', 'deep')
    expect(intake).toHaveAttribute('data-snapshot', 'snap-1')
    expect(intake).toHaveAttribute('data-compact', 'true')
  })

  it('redirects regular access to the document inbox', () => {
    render(
      <MemoryRouter initialEntries={['/importar']}>
        <Routes>
          <Route path="/documents" element={<div>Documents inbox</div>} />
          <Route path="/importar" element={<ImportPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByText('Documents inbox')).toBeInTheDocument()
  })
})
