import { beforeEach, describe, expect, it, vi } from 'vitest'

describe('importador routing decision helpers', () => {
  beforeEach(() => {
    vi.resetModules()
    vi.doMock('../../shared/api/client', () => ({
      default: {
        get: vi.fn(),
        post: vi.fn(),
        patch: vi.fn(),
        delete: vi.fn(),
      },
    }))
    vi.doMock('@shared/endpoints', () => ({
      TENANT_IMPORTADOR: {
        documents: '/api/v1/importador/documents',
      },
    }))
  })

  it('uses routing_decision as preferred save suggestion', async () => {
    const { suggestSaveDestination, getDocCategory } = await import('./services')
    const doc = {
      tipo_documento_detectado: 'INVOICE',
      proveedor_detectado: 'Proveedor demo',
      monto_total: 112,
      routing_decision: {
        document_type: 'supplier_invoice',
        confidence: 0.92,
        required_fields_ok: true,
        missing_fields: [],
        suggested_destination: 'supplier_invoice',
        reason: 'Contiene proveedor, fecha y total.',
        needs_human_review: false,
        source_doc_type: 'INVOICE',
        source_category: 'invoice',
      },
    }

    expect(suggestSaveDestination(doc)).toBe('supplier_invoice')
    expect(getDocCategory(doc, [])).toBe('supplier_invoice')
  })

  it('blocks save for routing decisions classified as inventory', async () => {
    const { canSaveDocument, getDocCategory } = await import('./services')
    const doc = {
      tipo_documento_detectado: 'INVENTORY',
      proveedor_detectado: undefined,
      monto_total: undefined,
      routing_decision: {
        document_type: 'inventory',
        confidence: 0.58,
        required_fields_ok: true,
        missing_fields: [],
        suggested_destination: null,
        reason: 'Documento detectado fuera del guardado automatico.',
        needs_human_review: true,
        source_doc_type: 'INVENTORY',
        source_category: 'inventory',
      },
    }

    expect(canSaveDocument(doc)).toBe(false)
    expect(getDocCategory(doc, ['Productos'])).toBe('inventory')
  })
})
