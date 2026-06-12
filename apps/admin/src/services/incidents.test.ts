import { beforeEach, describe, expect, it, vi } from 'vitest'

import { analyzeIncident, listIncidents } from './incidents'

describe('incidents service', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    sessionStorage.clear()
    localStorage.clear()
    sessionStorage.setItem('access_token_admin', 'admin-token')
  })

  it('lists incidents using the admin token and normalizes backend fields', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(
        JSON.stringify([
          {
            id: 'inc-1',
            tenant_id: 'tenant-1',
            type: 'warning',
            severity: 'medium',
            title: 'Importador: factura guardada con líneas sin stock',
            description: 'Quedaron líneas pendientes.',
            context: { document_id: 'doc-1' },
            status: 'open',
            auto_detected: true,
            auto_resolved: false,
            created_at: '2026-03-31T10:00:00Z',
            updated_at: '2026-03-31T10:00:00Z',
          },
        ]),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      )
    )

    const incidents = await listIncidents({ estado: 'open,in_progress' })

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/admin/incidents?status=open%2Cin_progress',
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: 'Bearer admin-token',
        }),
      })
    )
    expect(incidents).toEqual([
      expect.objectContaining({
        id: 'inc-1',
        tipo: 'warning',
        severidad: 'medium',
        titulo: 'Importador: factura guardada con líneas sin stock',
        estado: 'open',
        metadata: { document_id: 'doc-1' },
      }),
    ])
  })

  it('posts the AI analysis request and returns the refreshed incident detail', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            incident_id: 'inc-1',
            analysis: { root_cause: 'missing product linkage' },
            suggestion: 'Create the missing product.',
            confidence_score: 0.9,
            processing_time_ms: 14,
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } }
        )
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            id: 'inc-1',
            tenant_id: 'tenant-1',
            type: 'warning',
            severity: 'medium',
            title: 'Importador: factura guardada con líneas sin stock',
            description: 'Quedaron líneas pendientes.',
            context: { document_id: 'doc-1' },
            status: 'open',
            auto_detected: true,
            auto_resolved: false,
            ia_analysis: { root_cause: 'missing product linkage' },
            ia_suggestion: 'Create the missing product.',
            created_at: '2026-03-31T10:00:00Z',
            updated_at: '2026-03-31T10:01:00Z',
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } }
        )
      )

    const incident = await analyzeIncident('inc-1')

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      '/api/v1/admin/incidents/inc-1/analyze',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          use_gpt4: false,
          include_code_suggestions: true,
        }),
      })
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      '/api/v1/admin/incidents/inc-1',
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: 'Bearer admin-token',
        }),
      })
    )
    expect(incident.ia_analysis).toEqual({ root_cause: 'missing product linkage' })
    expect(incident.ia_suggestion).toBe('Create the missing product.')
  })
})
