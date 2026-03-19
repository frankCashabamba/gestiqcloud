import { useCallback, useState } from 'react'
import {
  bulkPatchStagingLines,
  createReviewSession,
  fetchFieldAnalysis,
  fetchIterations,
  fetchStagingLines,
  fetchStagingSummary,
  patchStagingLine,
  runIteration,
  runReviewSession,
  type FieldAnalysis,
  type IterationRecord,
  type IterationResult,
  type IterationScope,
  type ReviewSession,
  type StagingLine,
  type StagingLineSummary,
} from '../services'

interface ReprocessState {
  summary: StagingLineSummary | null
  lines: StagingLine[]
  iterations: IterationRecord[]
  fieldAnalysis: FieldAnalysis | null
  activeSession: ReviewSession | null
  lastResult: IterationResult | null
  isRunning: boolean
  isLoading: boolean
  error: string | null
}

const EMPTY_SUMMARY: StagingLineSummary = {
  pending: 0, valid: 0, imported: 0,
  invalid: 0, review: 0, skipped: 0, reprocess: 0,
}

export function useImportReprocess(documentoId: string) {
  const [state, setState] = useState<ReprocessState>({
    summary: null,
    lines: [],
    iterations: [],
    fieldAnalysis: null,
    activeSession: null,
    lastResult: null,
    isRunning: false,
    isLoading: false,
    error: null,
  })

  const setError = (error: string | null) => setState(s => ({ ...s, error }))
  const setLoading = (isLoading: boolean) => setState(s => ({ ...s, isLoading }))

  const refreshSummary = useCallback(async () => {
    const summary = await fetchStagingSummary(documentoId)
    setState(s => ({ ...s, summary }))
    return summary
  }, [documentoId])

  const loadLines = useCallback(async (params: Parameters<typeof fetchStagingLines>[1] = {}) => {
    setLoading(true)
    try {
      const lines = await fetchStagingLines(documentoId, params)
      setState(s => ({ ...s, lines }))
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }, [documentoId])

  /**
   * Paso 1: Inspección de campos ANTES de elegir qué reprocesar.
   * Muestra qué campos tienen problemas en las líneas seleccionadas.
   * Sin esto, el usuario elegiría campos a ciegas.
   */
  const inspectFields = useCallback(async (
    estados: string[] = ['INVALID', 'PENDING', 'REVIEW'],
    errorCodes: string[] = [],
    sheet?: string,
  ) => {
    setLoading(true)
    try {
      const analysis = await fetchFieldAnalysis(documentoId, {
        estados,
        error_codes: errorCodes,
        sheet,
      })
      setState(s => ({ ...s, fieldAnalysis: analysis }))
      return analysis
    } catch (e) {
      setError(String(e))
      return null
    } finally {
      setLoading(false)
    }
  }, [documentoId])

  const loadIterations = useCallback(async () => {
    const iterations = await fetchIterations(documentoId)
    setState(s => ({ ...s, iterations }))
    return iterations
  }, [documentoId])

  /**
   * Paso 2: Crear sesión de revisión con los campos elegidos por el usuario.
   * Retorna preview_count: cuántas líneas se verán afectadas.
   * El usuario confirma antes de ejecutar.
   */
  const buildReviewSession = useCallback(async (filters: {
    filter_estados?: string[]
    filter_error_codes?: string[]
    filter_campos?: string[]       // ← los campos que el usuario eligió en la inspección
    filter_lines?: number[]
    filter_sheet?: string | null
  }) => {
    setLoading(true)
    try {
      const session = await createReviewSession(documentoId, filters)
      setState(s => ({ ...s, activeSession: session }))
      return session
    } catch (e) {
      setError(String(e))
      return null
    } finally {
      setLoading(false)
    }
  }, [documentoId])

  /**
   * Paso 3: Ejecutar la sesión confirmada por el usuario.
   * Solo procesa los campos elegidos. Preserva todo lo demás.
   */
  const executeSession = useCallback(async (sessionId: string) => {
    setState(s => ({ ...s, isRunning: true, error: null }))
    try {
      const result = await runReviewSession(documentoId, sessionId)
      setState(s => ({
        ...s,
        lastResult: result,
        activeSession: null,
        isRunning: false,
      }))
      await refreshSummary()
      await loadIterations()
      return result
    } catch (e) {
      setState(s => ({ ...s, isRunning: false }))
      setError(String(e))
      return null
    }
  }, [documentoId, refreshSummary, loadIterations])

  /** Iteración directa sin sesión — para "reprocesar todo pendiente" */
  const iterate = useCallback(async (scope: Partial<IterationScope> = {}) => {
    setState(s => ({ ...s, isRunning: true, error: null }))
    try {
      const result = await runIteration(documentoId, scope)
      setState(s => ({ ...s, lastResult: result, isRunning: false }))
      await refreshSummary()
      await loadIterations()
      return result
    } catch (e) {
      setState(s => ({ ...s, isRunning: false }))
      setError(String(e))
      return null
    }
  }, [documentoId, refreshSummary, loadIterations])

  /** Marcar líneas individuales para reprocesar campos concretos */
  const markForReprocess = useCallback(async (
    lineIds: string[],
    campos?: string[],
  ) => {
    await bulkPatchStagingLines(documentoId, lineIds, 'REPROCESS', campos)
    await refreshSummary()
  }, [documentoId, refreshSummary])

  /** Corregir una línea manualmente y marcarla para reprocesar */
  const correctLine = useCallback(async (
    lineId: string,
    normalizedData: Record<string, unknown>,
    campos?: string[],
  ) => {
    const updated = await patchStagingLine(documentoId, lineId, {
      estado: 'REPROCESS',
      normalized_data: normalizedData,
      campos_revision: campos ?? null,
    })
    setState(s => ({
      ...s,
      lines: s.lines.map(l => l.id === lineId ? updated : l),
    }))
    await refreshSummary()
    return updated
  }, [documentoId, refreshSummary])

  const totalResolvable = (state.summary ?? EMPTY_SUMMARY).pending
    + (state.summary ?? EMPTY_SUMMARY).invalid
    + (state.summary ?? EMPTY_SUMMARY).review
    + (state.summary ?? EMPTY_SUMMARY).reprocess

  return {
    ...state,
    totalResolvable,
    refreshSummary,
    loadLines,
    inspectFields,      // Paso 1: ver campos reales
    buildReviewSession, // Paso 2: definir scope con campos elegidos
    executeSession,     // Paso 3: ejecutar
    iterate,
    markForReprocess,
    correctLine,
    loadIterations,
  }
}
