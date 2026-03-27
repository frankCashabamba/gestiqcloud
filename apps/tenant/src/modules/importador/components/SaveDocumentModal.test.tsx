import '@testing-library/jest-dom/vitest'
import React from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import SaveDocumentModal from './SaveDocumentModal'

const {
  mockListPaymentMethods,
  mockFetchSaveCapabilities,
  mockFetchDocumentLineMatchCandidates,
} = vi.hoisted(() => ({
  mockListPaymentMethods: vi.fn(),
  mockFetchSaveCapabilities: vi.fn(),
  mockFetchDocumentLineMatchCandidates: vi.fn(),
}))

vi.mock('../../accounting/services', () => ({
  listPaymentMethods: mockListPaymentMethods,
}))

vi.mock('../services', () => ({
  canSaveDocument: () => true,
  fetchDocumentLineMatchCandidates: mockFetchDocumentLineMatchCandidates,
  fetchSaveCapabilities: mockFetchSaveCapabilities,
  getDocumentData: (doc: any) => doc?.datos_confirmados || doc?.datos_extraidos || {},
  getDocumentValue: (data: Record<string, unknown>, ...keys: string[]) => {
    for (const key of keys) {
      const value = data[key]
      if (value != null && value !== '') return value
    }
    return undefined
  },
  saveDocument: vi.fn(),
  suggestSaveDestination: () => 'supplier_invoice',
}))

describe('SaveDocumentModal', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockListPaymentMethods.mockResolvedValue([])
    mockFetchSaveCapabilities.mockResolvedValue({ purchases: true, expenses: true, inventory: true })
    mockFetchDocumentLineMatchCandidates.mockResolvedValue([])
  })

  it('opens in simple mode and reveals advanced options on demand', async () => {
    const user = userEvent.setup()

    render(
      <SaveDocumentModal
        doc={{
          id: 'doc-1',
          nombre_archivo: 'factura-demo.pdf',
          monto_total: 120.5,
          moneda: 'USD',
          datos_extraidos: { total: 120.5 },
          routing_decision: {
            document_type: 'supplier_invoice',
            confidence: 0.94,
            required_fields_ok: true,
            missing_fields: [],
            suggested_destination: 'supplier_invoice',
            reason: 'Contiene proveedor, fecha y total.',
            needs_human_review: false,
            source_doc_type: 'INVOICE',
            source_category: 'invoice',
          },
        } as any}
        open={true}
        onClose={vi.fn()}
      />,
    )

    expect(screen.getByText('Guardado sugerido')).toBeInTheDocument()
    expect(screen.getByText('Factura proveedor')).toBeInTheDocument()
    expect(screen.queryByText('Estado de pago')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Cambiar destino u opciones' }))

    expect(screen.getByText('Estado de pago')).toBeInTheDocument()
    expect(screen.getByText('Guardar como')).toBeInTheDocument()
  })
})
