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
        canonicalFields: '/api/v1/importador/canonical-fields',
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
        primary_destination: 'supplier_invoice',
        candidate_destinations: [
          {
            code: 'supplier_invoice',
            label: 'Supplier invoice',
            target: 'purchases',
            target_tables: ['purchases', 'expenses'],
            save_api: 'save_document',
            score: 0.92,
            save_ready: true,
            required_fields_ok: true,
            missing_fields: [],
            needs_human_review: false,
            reason: 'Contiene proveedor, fecha y total.',
            confirmation_required: true,
            capabilities: {
              supports_update_stock: true,
              supports_line_matching: true,
              supports_partial_payment: true,
              supports_multi_record_save: true,
            },
          },
        ],
        reason: 'Contiene proveedor, fecha y total.',
        needs_human_review: false,
        source_doc_type: 'INVOICE',
        source_category: 'invoice',
      },
    }

    expect(suggestSaveDestination(doc)).toBe('supplier_invoice')
    expect(getDocCategory(doc, [])).toBe('supplier_invoice')
  })

  it('uses primary_destination when suggested_destination is missing', async () => {
    const { suggestSaveDestination } = await import('./services')
    const doc = {
      tipo_documento_detectado: 'INVOICE',
      proveedor_detectado: 'Proveedor demo',
      monto_total: 112,
      routing_decision: {
        document_type: 'supplier_invoice',
        confidence: 0.92,
        required_fields_ok: true,
        missing_fields: [],
        suggested_destination: null,
        primary_destination: 'supplier_invoice',
        candidate_destinations: [
          {
            code: 'supplier_invoice',
            label: 'Supplier invoice',
            target: 'purchases',
            target_tables: ['purchases', 'expenses'],
            save_api: 'save_document',
            score: 0.92,
            save_ready: true,
            required_fields_ok: true,
            missing_fields: [],
            needs_human_review: false,
            reason: 'Contiene proveedor, fecha y total.',
            confirmation_required: true,
            capabilities: {
              supports_update_stock: true,
              supports_line_matching: true,
              supports_partial_payment: true,
              supports_multi_record_save: true,
            },
          },
        ],
        reason: 'Contiene proveedor, fecha y total.',
        needs_human_review: false,
        source_doc_type: 'INVOICE',
        source_category: 'invoice',
      },
    }

    expect(suggestSaveDestination(doc)).toBe('supplier_invoice')
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
        primary_destination: null,
        candidate_destinations: [],
        reason: 'Documento detectado fuera del guardado automatico.',
        needs_human_review: true,
        source_doc_type: 'INVENTORY',
        source_category: 'inventory',
      },
    }

    expect(canSaveDocument(doc)).toBe(false)
    expect(getDocCategory(doc, ['Productos'])).toBe('inventory')
  })

  it('stays conservative when backend routing is missing', async () => {
    const { canSaveDocument, getDocCategory, suggestSaveDestination } = await import('./services')
    const doc = {
      tipo_documento_detectado: 'INVOICE',
      proveedor_detectado: 'Proveedor demo',
      monto_total: 112,
      routing_decision: null,
    }

    expect(getDocCategory(doc, [])).toBe('other')
    expect(suggestSaveDestination(doc)).toBe('expense')
    expect(canSaveDocument(doc)).toBe(false)
  })

  it('prefers backend canonical labels when available', async () => {
    const apiModule = await import('../../shared/api/client')
    const api = apiModule.default as { get: ReturnType<typeof vi.fn> }
    api.get.mockResolvedValueOnce({
      data: [
        { name: 'vendor', field_type: 'text', label: 'Proveedor DB', line_item_slot: null },
        { name: 'unit_price', field_type: 'numeric', label: 'Precio unitario DB', line_item_slot: 'unit_price' },
      ],
    })

    const { fetchCanonicalFields, formatFieldLabel, isLineItemFieldName } = await import('./services')
    await fetchCanonicalFields()

    expect(formatFieldLabel('vendor')).toBe('Proveedor DB')
    expect(formatFieldLabel('unit_price')).toBe('Precio unitario DB')
    expect(isLineItemFieldName('unit_price')).toBe(true)
  })

  it('sends explicit reprocess mode to the async import endpoint', async () => {
    const apiModule = await import('../../shared/api/client')
    const api = apiModule.default as { post: ReturnType<typeof vi.fn> }
    api.post.mockResolvedValueOnce({ data: [] })

    const { runImportAsync } = await import('./services')
    const files = [new File(['demo'], 'factura.pdf', { type: 'application/pdf' })]

    await runImportAsync(files, {
      force: true,
      recipeSnapshotId: 'snapshot-1',
      reprocessMode: 'deep',
    })

    expect(api.post).toHaveBeenCalledTimes(1)
    expect(api.post.mock.calls[0][1]).toBeInstanceOf(FormData)
    expect(api.post.mock.calls[0][2]).toEqual({
      params: {
        force: 'true',
        recipe_snapshot_id: 'snapshot-1',
        reprocess_mode: 'deep',
      },
    })
  })
})
