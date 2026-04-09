import { beforeEach, describe, expect, it, vi } from 'vitest'

const { api } = vi.hoisted(() => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

vi.mock('../../shared/api/client', () => ({
  default: api,
}))

import {
  createRoutingProfile,
  getImportadorRoutingOverview,
  listRuntimeConfig,
  listRoutingProfiles,
  listRoutingPreviewDocuments,
  listRoutingRules,
  previewRouting,
  resetRuntimeConfigModule,
  upsertRuntimeConfigEntry,
  updateRoutingRule,
} from './importador-routing'

describe('importador-routing service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('normalizes profile responses from admin api', async () => {
    api.get.mockResolvedValueOnce({
      data: [
        {
          id: 'p1',
          code: 'supplier_invoice',
          document_type: 'supplier_invoice',
          suggested_destination: 'supplier_invoice',
          required_groups: [['issue_date'], ['total_amount']],
          support_fields: ['vendor'],
          explanation_fields: ['issue_date', 'total_amount'],
          blocked: false,
          confidence_threshold: '0.91',
          active: true,
        },
      ],
    })

    const result = await listRoutingProfiles()

    expect(api.get).toHaveBeenCalledWith('/v1/admin/importador/routing/profiles')
    expect(result).toEqual([
      {
        id: 'p1',
        code: 'supplier_invoice',
        document_type: 'supplier_invoice',
        description: null,
        suggested_destination: 'supplier_invoice',
        required_groups: [['issue_date'], ['total_amount']],
        support_fields: ['vendor'],
        explanation_fields: ['issue_date', 'total_amount'],
        blocked: false,
        confidence_threshold: 0.91,
        active: true,
      },
    ])
  })

  it('passes the scope filter when listing rules', async () => {
    api.get.mockResolvedValueOnce({ data: [] })

    await listRoutingRules('tenant')

    expect(api.get).toHaveBeenCalledWith('/v1/admin/importador/routing/rules?scope_kind=tenant')
  })

  it('unwraps item responses for create and update operations', async () => {
    api.post.mockResolvedValueOnce({
      data: {
        ok: true,
        item: {
          id: 'p2',
          code: 'expense',
          document_type: 'expense',
          description: 'Gastos generales',
          suggested_destination: 'expense',
          required_groups: [['issue_date']],
          support_fields: [],
          explanation_fields: [],
          blocked: false,
          confidence_threshold: 0.8,
          active: true,
        },
      },
    })
    api.put.mockResolvedValueOnce({
      data: {
        ok: true,
        item: {
          id: 'r1',
          scope_kind: 'system',
          tenant_id: null,
          sector: null,
          source_kind: 'doc_type',
          source_key: 'INVOICE',
          profile_code: 'expense',
          priority: 5,
          active: true,
        },
      },
    })

    const created = await createRoutingProfile({
      code: 'expense',
      document_type: 'expense',
      description: 'Gastos generales',
      suggested_destination: 'expense',
      required_groups: [['issue_date']],
      support_fields: [],
      explanation_fields: [],
      blocked: false,
      confidence_threshold: 0.8,
      active: true,
    })
    const updated = await updateRoutingRule('r1', {
      scope_kind: 'system',
      tenant_id: null,
      sector: null,
      source_kind: 'doc_type',
      source_key: 'INVOICE',
      profile_code: 'expense',
      priority: 5,
      active: true,
    })

    expect(created.id).toBe('p2')
    expect(updated.id).toBe('r1')
    expect(api.post).toHaveBeenCalled()
    expect(api.put).toHaveBeenCalledWith('/v1/admin/importador/routing/rules/r1', expect.any(Object))
  })

  it('normalizes routing preview responses', async () => {
    api.post.mockResolvedValueOnce({
      data: {
        decision: {
          document_type: 'expense',
          confidence: '0.88',
          required_fields_ok: true,
          missing_fields: [],
          suggested_destination: 'expense',
          reason: 'Contiene proveedor, fecha y total.',
          needs_human_review: false,
          source_doc_type: 'INVOICE',
          source_category: 'invoice',
        },
        profile_code: 'expense',
        matched_by: 'doc_type:invoice',
        matched_scope: 'tenant',
        rule_source_kind: 'doc_type',
        rule_source_key: 'INVOICE',
        resolved_sector: 'panaderia',
        document_id: 'doc-1',
        document_name: 'factura-demo.pdf',
        tenant_id: 'tenant-1',
      },
    })

    const result = await previewRouting({
      document_id: null,
      scope_kind: 'tenant',
      tenant_id: 'tenant-1',
      sector: null,
      source_doc_type: 'INVOICE',
      source_category: null,
      ai_confidence: 0.91,
      extracted_data: { total_amount: 42 },
      canonical_fields: {},
      requires_review: false,
      destination_override: null,
    })

    expect(api.post).toHaveBeenCalledWith('/v1/admin/importador/routing/preview', expect.any(Object))
    expect(result.decision.confidence).toBe(0.88)
    expect(result.matched_scope).toBe('tenant')
    expect(result.rule_source_key).toBe('INVOICE')
    expect(result.document_name).toBe('factura-demo.pdf')
  })

  it('lists recent preview documents for a tenant', async () => {
    api.get.mockResolvedValueOnce({
      data: [
        {
          id: 'doc-1',
          tenant_id: 'tenant-1',
          nombre_archivo: 'factura-demo.pdf',
          tipo_documento_detectado: 'INVOICE',
          estado: 'REVIEW',
          created_at: '2026-03-27T10:00:00Z',
          proveedor_detectado: 'Proveedor Real',
          monto_total: '199.5',
        },
      ],
    })

    const result = await listRoutingPreviewDocuments('tenant-1', 'factura')

    expect(api.get).toHaveBeenCalledWith('/v1/admin/importador/routing/documents?tenant_id=tenant-1&q=factura')
    expect(result[0].monto_total).toBe(199.5)
  })

  it('loads routing overview for a tenant', async () => {
    api.get.mockResolvedValueOnce({
      data: {
        tenant_id: 'tenant-1',
        tenant_name: 'Demo',
        dashboard: { total: 10, pendientes: 2, en_revision: 1, confirmados: 6, fallidos: 1 },
        recent_batches: [],
        recent_documents: [],
        reprocess_queue: [],
        learning_insights: [],
      },
    })

    const result = await getImportadorRoutingOverview('tenant-1', 6)

    expect(api.get).toHaveBeenCalledWith('/v1/admin/importador/routing/overview?tenant_id=tenant-1&limit=6')
    expect(result.dashboard.confirmados).toBe(6)
    expect(result.tenant_name).toBe('Demo')
  })

  it('lists and updates runtime config entries', async () => {
    api.get.mockResolvedValueOnce({
      data: {
        modules: [
          {
            module: 'doc_categories',
            title: 'Document Categories',
            description: null,
            editable: true,
            entries: [
              {
                id: 'e1',
                module: 'doc_categories',
                key: 'invoice',
                label: 'Invoice',
                value_list: ['INVOICE'],
                value_text: null,
                value_kind: 'list',
                updated_at: '2026-04-08T10:00:00Z',
              },
            ],
          },
        ],
      },
    })
    api.put.mockResolvedValueOnce({
      data: {
        id: 'e2',
        module: 'learning',
        key: 'event_weight_save',
        label: 'Save weight',
        value_text: '4.2',
        value_list: [],
        value_kind: 'text',
        updated_at: '2026-04-08T10:00:00Z',
      },
    })
    api.post.mockResolvedValueOnce({ data: { ok: true } })

    const catalog = await listRuntimeConfig()
    const updated = await upsertRuntimeConfigEntry('learning', 'event_weight_save', {
      label: 'Save weight',
      value_text: '4.2',
      value_list: [],
    })
    await resetRuntimeConfigModule('learning')

    expect(api.get).toHaveBeenCalledWith('/v1/admin/importador/routing/runtime-config')
    expect(catalog.modules[0].entries[0].value_kind).toBe('list')
    expect(updated.module).toBe('learning')
    expect(api.put).toHaveBeenCalledWith(
      '/v1/admin/importador/routing/runtime-config/learning/event_weight_save',
      expect.any(Object)
    )
    expect(api.post).toHaveBeenCalledWith('/v1/admin/importador/routing/runtime-config/learning/reset')
  })
})
