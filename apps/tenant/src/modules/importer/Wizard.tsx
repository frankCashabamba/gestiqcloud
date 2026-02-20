/**
 * Import wizard with a real pipeline:
 * - createBatch + ingestBatch (products)
 * - Summary with "Auto mode" toggle (activate, create warehouse, apply stock)
 * - promote batch with flags
 */
import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../../auth/AuthContext'

import VistaPreviaTabla from './components/VistaPreviaTabla'
import ResumenImportacion from './components/ResumenImportacion'
import { ClassificationSuggestion } from './components/ClassificationSuggestion'
import { AnalysisResult } from './components/AnalysisResult'
import { AIProviderSettings } from './components/AIProviderSettings'
import { AIHealthIndicator } from './components/AIHealthIndicator'
import { AITelemetryDashboard } from './components/AITelemetryDashboard'
import { ImportProgressIndicator } from './components/ImportProgressIndicator'
import { ConfirmParserModal } from './components/ConfirmParserModal'
import ImportadorLayout from './components/ImportadorLayout'
import MapeoCampos from './components/MapeoCampos'
import { useImportProgress } from './hooks/useImportProgress'
import { getAliasSugeridos } from './utils/aliasCampos'
import { autoMapeoColumnas } from './services/autoMapeoColumnas'
import { detectarTipoDocumento, type ImportDocType } from './utils/detectarTipoDocumento'
import { normalizarDocumento } from './utils/normalizarDocumento'
import { createBatch, ingestBatch, confirmBatch, processDocument, pollOcrJob } from './services/importsApi'
import { IMPORTS } from '@endpoints/imports'
import { useClassifyFile } from './hooks/useClassifyFile'
import { useAnalyzeFile } from './hooks/useAnalyzeFile'
import { useParserRegistry } from './hooks/useParserRegistry'
import { useEntityConfig } from './hooks/useEntityConfig'
import { parseCSV } from './services/parseCSVFile'
import { parseExcelFile } from './services/parseExcelFile'

type Row = Record<string, string>
type Step = 'upload' | 'preview' | 'mapping' | 'validate' | 'summary' | 'importing'
type DocType = ImportDocType

const CAMPOS_OBJETIVO = ['nombre', 'precio'] as const
const STEP_ORDER: Step[] = ['upload', 'preview', 'mapping', 'validate', 'summary', 'importing']
const STEPS: Array<{ key: Step; labelKey: string; helperKey: string }> = [
  { key: 'upload', labelKey: 'wizard.steps.upload.label', helperKey: 'wizard.steps.upload.helper' },
  { key: 'preview', labelKey: 'wizard.steps.preview.label', helperKey: 'wizard.steps.preview.helper' },
  { key: 'mapping', labelKey: 'wizard.steps.mapping.label', helperKey: 'wizard.steps.mapping.helper' },
  { key: 'validate', labelKey: 'wizard.steps.validate.label', helperKey: 'wizard.steps.validate.helper' },
  { key: 'summary', labelKey: 'wizard.steps.summary.label', helperKey: 'wizard.steps.summary.helper' },
  { key: 'importing', labelKey: 'wizard.steps.importing.label', helperKey: 'wizard.steps.importing.helper' },
]
const MAX_ROWS = 10000
const PREVIEW_LIMIT = 50

function ImportadorWizard() {
  const { token } = useAuth() as { token: string | null }
  const { t } = useTranslation('importer')
  const navigate = useNavigate()
  const {
    classify,
    loading: classifying,
    result: classificationResult,
    error: classificationError,
    confidence,
    reset: resetClassification,
  } = useClassifyFile()
  const {
    analyze,
    loading: analyzing,
    result: analysisResult,
    error: analysisError,
    requiresConfirmation,
    reset: resetAnalysis,
  } = useAnalyzeFile()
  const { registry: parserRegistry } = useParserRegistry(token || undefined)
  const { config: entityConfig } = useEntityConfig({ module: 'products' })

  const camposObjetivo = useMemo(() => {
    return entityConfig?.fields.map((f) => f.field) ?? Array.from(CAMPOS_OBJETIVO)
  }, [entityConfig])

  // Wizard state
  const [step, setStep] = useState<Step>('upload')
  const [fileName, setFileName] = useState('')
  const [headers, setHeaders] = useState<string[]>([])
  const [rows, setRows] = useState<Row[]>([])
  const [mapa, setMapa] = useState<Partial<Record<string, string>>>({})
  const [errores, setErrores] = useState<string[]>([])
  const [docType, setDocType] = useState<DocType>('products')

  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [batchId, setBatchId] = useState<string | null>(null)
  const [savedSummary, setSavedSummary] = useState<{ saved: number; errors: number; lastBatchId?: string } | null>(null)

  // Auto mode
  const [autoMode, setAutoMode] = useState(true)
  const [targetWarehouse, setTargetWarehouse] = useState('ALM-1')

  // Sprint 2: manual parser override
  const [selectedParser, setSelectedParser] = useState<string | null>(null)

  // Confirmation modal state
  const [showConfirmModal, setShowConfirmModal] = useState(false)
  const [showTelemetry, setShowTelemetry] = useState(false)

  // Progreso por polling al endpoint /status
  const { progress, progressPercent, isConnected, error: wsError } = useImportProgress(batchId)

  // OCR state for PDFs/images
  const [ocrLoading, setOcrLoading] = useState(false)
  const [ocrError, setOcrError] = useState<string | null>(null)

  const currentStepIndex = useMemo(() => STEP_ORDER.indexOf(step), [step])

  const isPdfOrImage = (file: File) => {
    const name = file.name.toLowerCase()
    const type = file.type.toLowerCase()
    return (
      name.endsWith('.pdf') ||
      type === 'application/pdf' ||
      type.startsWith('image/') ||
      /\.(png|jpg|jpeg|tiff|bmp|gif)$/i.test(name)
    )
  }

  const isExcelFile = (file: File) => {
    const name = file.name.toLowerCase()
    const type = file.type.toLowerCase()
    return (
      name.endsWith('.xlsx') ||
      name.endsWith('.xls') ||
      type.includes('spreadsheetml') ||
      type.includes('ms-excel')
    )
  }

  const onFile: React.ChangeEventHandler<HTMLInputElement> = async (e) => {
    const f = e.target.files?.[0]
    if (!f) return

    resetClassification()
    resetAnalysis()
    setErrores([])
    setSaveError(null)
    setBatchId(null)
    setSavedSummary(null)
    setSelectedParser(null)

    setFileName(f.name)
    setOcrError(null)

    if (isPdfOrImage(f)) {
      setOcrLoading(true)
      try {
        const result = await processDocument(f, token || undefined)

        let ocrResult = result
        let attempts = 0
        const maxAttempts = 30
        while (ocrResult.status === 'pending' && attempts < maxAttempts) {
          await new Promise((r) => setTimeout(r, 2000))
          ocrResult = await pollOcrJob(ocrResult.jobId, token || undefined)
          attempts++
        }

        if (ocrResult.status === 'done' && ocrResult.payload?.documentos?.length) {
          const docs = ocrResult.payload.documentos
          const ocrRows = docs.map((doc: any, idx: number) => ({
            _idx: idx + 1,
            tipo: doc.tipo || doc.documentoTipo || 'ticket_pos',
            fecha: doc.fecha || doc.issue_date || '',
            importe: doc.importe || doc.total || 0,
            concepto: doc.concepto || doc.description || t('wizard.messages.ocrDocument'),
            invoice: doc.invoice || doc.invoice_number || '',
            categoria: doc.categoria || 'sales',
            ...doc,
          }))

          const ocrHeaders = ocrRows.length > 0 ? Object.keys(ocrRows[0]) : ['fecha', 'importe', 'concepto']
          setHeaders(ocrHeaders)
          setRows(ocrRows)
          setDocType('expenses')

          const sugeridos = autoMapeoColumnas(ocrHeaders, getAliasSugeridos(entityConfig || undefined))
          setMapa(sugeridos as any)
        } else {
          throw new Error(t('wizard.errors.ocrNoDocuments'))
        }
      } catch (err: any) {
        console.error('OCR failed:', err)
        setOcrError(err?.message || t('wizard.errors.ocrProcessFailed'))
        setHeaders([])
        setRows([])
      } finally {
        setOcrLoading(false)
      }
      setStep('preview')
      return
    }

    let parsedHeaders: string[] = []
    let parsedRows: Row[] = []
    try {
      if (isExcelFile(f)) {
        const parsed = await parseExcelFile(f, token || undefined)
        parsedHeaders = parsed.headers
        parsedRows = parsed.rows as Row[]
      } else {
        const text = await f.text()
        const { headers: hs, rows: rs } = parseCSV(text)
        parsedHeaders = hs
        parsedRows = rs
      }
    } catch (parseError: any) {
      const detail = parseError?.data?.detail || parseError?.message || t('wizard.errors.unknownError')
      if (f.name.toLowerCase().endsWith('.xls')) {
        setOcrError(t('wizard.errors.oldXlsReadFailed', { file: f.name, detail }))
      } else {
        setOcrError(t('wizard.errors.fileReadFailed', { file: f.name, detail }))
      }
      setHeaders([])
      setRows([])
      setStep('preview')
      return
    }

    setHeaders(parsedHeaders)
    setRows(parsedRows)

    const sugeridos = autoMapeoColumnas(parsedHeaders, getAliasSugeridos(entityConfig || undefined))
    setMapa(sugeridos as any)
    setDocType(detectarTipoDocumento(parsedHeaders) || 'products')

    try {
      const result = await analyze(f)
      if (result?.mapping_suggestion) {
        setMapa((prev) => ({ ...prev, ...result.mapping_suggestion }))
      }
      if (result?.suggested_doc_type) {
        setDocType(result.suggested_doc_type as DocType)
      }
    } catch (err) {
      console.warn('Analysis failed, falling back to classification:', err)
      try {
        await classify(f)
      } catch (classifyErr) {
        console.warn('Classification also failed:', classifyErr)
      }
    }

    setStep('preview')
  }

  const previewHeaders = useMemo(() => headers, [headers])
  const previewRows = useMemo(() => rows.slice(0, PREVIEW_LIMIT), [rows])

  useEffect(() => {
    if (!headers.length || !entityConfig) return
    const sugeridos = autoMapeoColumnas(headers, getAliasSugeridos(entityConfig))
    setMapa((prev) => (Object.keys(prev || {}).length ? prev : (sugeridos as any)))
  }, [headers, entityConfig])

  useEffect(() => {
    if (step !== 'validate' && step !== 'summary') return
    runValidation()
  }, [step, mapa, rows.length, camposObjetivo])

  const continuar = () => {
    if (step === 'upload') setStep('preview')
    else if (step === 'preview') setStep('mapping')
    else if (step === 'mapping') {
      runValidation()
      setStep('validate')
    } else if (step === 'validate') setStep('summary')
    else if (step === 'summary') setStep('importing')
  }

  const volver = () => {
    if (step === 'importing') setStep('summary')
    else if (step === 'summary') setStep('validate')
    else if (step === 'validate') setStep('mapping')
    else if (step === 'mapping') setStep('preview')
    else if (step === 'preview') setStep('upload')
  }

  const runValidation = () => {
    const errs: string[] = []
    camposObjetivo.forEach((c) => {
      if (!mapa[c]) errs.push(t('wizard.validation.missingMappingFor', { field: c }))
    })
    if (rows.length === 0) errs.push(t('wizard.validation.fileHasNoRows'))
    if (rows.length > MAX_ROWS) errs.push(t('wizard.validation.maxRowsPerImport', { max: MAX_ROWS.toLocaleString() }))
    setErrores(errs)
  }

  async function onImportAll() {
    const needsConfirmation = requiresConfirmation && !selectedParser
    if (needsConfirmation) {
      setShowConfirmModal(true)
      return
    }

    await executeImport()
  }

  async function executeImport(confirmedParser?: string) {
    setSaveError(null)
    setSaving(true)
    setStep('importing')
    try {
      const effectiveDocType = analysisResult?.suggested_doc_type || docType || 'products'
      const docs = normalizarDocumento(rows, mapa as any, effectiveDocType)
      const effectiveParser = confirmedParser || selectedParser
      const batchPayload: any = {
        source_type: effectiveDocType,
        origin: 'excel_ui',
      }

      if (analysisResult) {
        batchPayload.suggested_parser = effectiveParser || analysisResult.suggested_parser
        batchPayload.classification_confidence = analysisResult.confidence
        batchPayload.ai_enhanced = analysisResult.ai_enhanced
        batchPayload.ai_provider = analysisResult.ai_provider
        batchPayload.suggested_doc_type = analysisResult.suggested_doc_type
      } else if (classificationResult) {
        batchPayload.suggested_parser = effectiveParser || classificationResult.suggested_parser
        batchPayload.classification_confidence = classificationResult.confidence
        batchPayload.ai_enhanced = classificationResult.enhanced_by_ai
        batchPayload.ai_provider = classificationResult.ai_provider
      }

      const batch = await createBatch(batchPayload, token || undefined)
      setBatchId(batch.id)

      if (batch.requires_confirmation && effectiveParser) {
        await confirmBatch(batch.id, { parser_id: effectiveParser }, token || undefined)
      }

      await ingestBatch(batch.id, { rows: docs }, token || undefined, null)

      // Professional UX: for non-products, promotion should happen in Preview so the user can
      // choose paid/pending and accounting options in one place (avoid multiple promote UIs).
      if (effectiveDocType !== 'products' && effectiveDocType !== 'productos') {
        navigate(`../preview?batch_id=${encodeURIComponent(batch.id)}`)
        return
      }

      try {
        const url = new URL(IMPORTS.batches.promote(batch.id), window.location.origin)
        if (autoMode) {
          url.searchParams.set('auto', '1')
          url.searchParams.set('target_warehouse', targetWarehouse || 'ALM-1')
          url.searchParams.set('create_warehouse', '1')
          url.searchParams.set('allow_missing_price', '1')
          url.searchParams.set('activate', '1')
        }
        const res = await fetch(url.toString(), { method: 'POST', headers: { Authorization: `Bearer ${token || ''}` } })
        if (res.ok) {
          const summary = await res.json()
          setSavedSummary({ saved: summary.created || 0, errors: summary.failed || 0, lastBatchId: batch.id })
        }
      } catch {
        // ignore
      }
    } catch (e: any) {
      setSaveError(e?.message || t('wizard.errors.importError'))
    } finally {
      setSaving(false)
    }
  }

  async function handleConfirmParser(parserId: string) {
    setSelectedParser(parserId)
    setShowConfirmModal(false)
    await executeImport(parserId)
  }

  const mappedCount = useMemo(() => {
    return camposObjetivo.filter((c) => mapa[c]).length
  }, [camposObjetivo, mapa])

  return (
    <ImportadorLayout
      title={t('wizard.page.title')}
      description={t('wizard.page.description')}
      actions={
        <div className="flex items-center gap-2">
          <AIHealthIndicator showDetails={false} className="hidden md:flex" />
          <button
            type="button"
            onClick={() => setShowTelemetry((prev) => !prev)}
            className="px-3 py-2 rounded border border-gray-300 hover:border-gray-400 bg-white hover:bg-gray-50 transition text-sm"
          >
            {showTelemetry ? t('wizard.actions.hideAiTelemetry') : t('wizard.actions.showAiTelemetry')}
          </button>
          <AIProviderSettings />
        </div>
      }
    >
      {showTelemetry && (
        <div className="mb-6">
          <AITelemetryDashboard />
        </div>
      )}

      {/* Steps */}
      <div className="mb-6">
        <div className="flex items-center justify-between text-sm">
          {STEPS.map((s, idx) => {
            const isActive = step === s.key
            const isComplete = idx < currentStepIndex
            return (
              <React.Fragment key={s.key}>
                <div
                  className={`flex items-center gap-2 ${
                    isActive ? 'text-blue-600 font-semibold' : isComplete ? 'text-green-600' : 'text-gray-400'
                  }`}
                >
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center border-2 ${
                      isActive
                        ? 'border-blue-600 bg-blue-50'
                        : isComplete
                        ? 'border-green-600 bg-green-50'
                        : 'border-gray-300'
                    }`}
                  >
                    {isComplete ? t('wizard.steps.completed') : idx + 1}
                  </div>
                  <div className="hidden sm:block">
                    <div>{t(s.labelKey)}</div>
                    <div className="text-[11px] text-gray-400">{t(s.helperKey)}</div>
                  </div>
                </div>
                {idx < STEPS.length - 1 && <div className="flex-1 h-0.5 bg-gray-300" />}
              </React.Fragment>
            )
          })}
        </div>
      </div>

      {/* Upload */}
      {step === 'upload' && (
        <div className="space-y-4 max-w-xl">
          <p className="text-gray-600">{t('wizard.upload.selectFilePrompt')}</p>
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-blue-500 transition">
            <input
              type="file"
              accept=".csv,.xlsx,.xls,.pdf,.png,.jpg,.jpeg,.tiff,.bmp"
              onChange={onFile}
              className="hidden"
              id="file-upload"
              disabled={ocrLoading}
            />
            <label htmlFor="file-upload" className={`cursor-pointer block ${ocrLoading ? 'opacity-50' : ''}`}>
              {ocrLoading ? (
                <>
                  <div className="text-4xl mb-2 animate-spin">*</div>
                  <div className="text-blue-600 font-medium">{t('wizard.upload.processingWithOcr')}</div>
                  <div className="text-sm text-gray-500 mt-1">{t('wizard.upload.mayTakeMoment')}</div>
                </>
              ) : (
                <>
                  <div className="text-4xl mb-2">+</div>
                  <div className="text-blue-600 font-medium">{t('wizard.upload.clickChooseFile')}</div>
                  <div className="text-sm text-gray-500 mt-1">{t('wizard.upload.acceptedFormats')}</div>
                </>
              )}
            </label>
          </div>
          {ocrError && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">{ocrError}</div>
          )}
        </div>
      )}

      {/* Preview */}
      {step === 'preview' && (
        <div className="space-y-4">
          <div className="bg-blue-50 border border-blue-200 px-4 py-3 rounded">
            {t('wizard.preview.fileSummary', {
              file: fileName,
              rows: rows.length.toLocaleString(),
              columns: headers.length,
            })}
          </div>

          {(analysisResult || analyzing || analysisError) ? (
            <AnalysisResult
              result={analysisResult}
              loading={analyzing}
              error={analysisError}
              selectedParser={selectedParser}
              onParserChange={setSelectedParser}
              onConfirm={continuar}
            />
          ) : (
            <ClassificationSuggestion
              result={classificationResult}
              loading={classifying}
              error={classificationError}
              confidence={confidence}
            />
          )}

          <VistaPreviaTabla headers={previewHeaders} rows={previewRows} />
          <div className="flex gap-2">
            <button className="bg-gray-200 hover:bg-gray-300 px-4 py-2 rounded" onClick={volver}>
              {t('wizard.actions.back')}
            </button>
            <button className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded" onClick={continuar}>
              {t('wizard.actions.continue')}
            </button>
          </div>
        </div>
      )}

      {/* Mapping */}
      {step === 'mapping' && (
        <div className="space-y-4">
          <div className="bg-neutral-50 border px-4 py-3 rounded text-neutral-700 text-sm">
            {t('wizard.mapping.reviewAdjust')}
          </div>

          <MapeoCampos
            headers={headers}
            camposObjetivo={camposObjetivo}
            mapa={mapa}
            onChange={setMapa}
            sourceType={docType}
            previewData={rows}
            fieldConfig={entityConfig || undefined}
          />

          {classificationResult && parserRegistry && (
            <div className="border-2 border-blue-300 rounded-lg p-4 bg-blue-50">
              <label className="block text-sm font-semibold text-gray-700 mb-3">{t('wizard.mapping.parserSelection')}</label>
              <div className="flex gap-3 items-start mb-3">
                <select
                  value={selectedParser || classificationResult.suggested_parser || ''}
                  onChange={(e) => setSelectedParser(e.target.value || null)}
                  className="flex-1 border border-gray-300 rounded px-3 py-2 text-sm font-medium"
                >
                  <option value="">{t('wizard.mapping.useSuggestion', { parser: classificationResult.suggested_parser })}</option>
                  {Object.entries(parserRegistry.parsers as Record<string, { doc_type?: string; description?: string }>).map(
                    ([id, parser]) => (
                      <option key={id} value={id}>
                        {id} ({parser.doc_type})
                      </option>
                    )
                  )}
                </select>
                {selectedParser && (
                  <span className="text-xs bg-amber-100 text-amber-800 px-3 py-2 rounded font-bold whitespace-nowrap">
                    {t('wizard.mapping.override')}
                  </span>
                )}
              </div>

              {selectedParser &&
                (parserRegistry.parsers as Record<string, { doc_type?: string; description?: string }>)[selectedParser] && (
                  <div className="bg-white border border-blue-200 rounded p-3 mb-2 text-xs">
                    <strong>{t('wizard.mapping.selected')}:</strong> {selectedParser}
                    <br />
                    <strong>{t('wizard.mapping.type')}:</strong>{' '}
                    {(parserRegistry.parsers as Record<string, { doc_type?: string; description?: string }>)[selectedParser]
                      .doc_type}
                    <br />
                    {(parserRegistry.parsers as Record<string, { doc_type?: string; description?: string }>)[selectedParser]
                      .description && (
                      <>
                        <strong>{t('wizard.mapping.description')}:</strong>{' '}
                        {(parserRegistry.parsers as Record<string, { doc_type?: string; description?: string }>)[selectedParser]
                          .description}
                      </>
                    )}
                  </div>
                )}

              <div className="text-xs text-gray-600 bg-white rounded p-2 border border-gray-200">
                <strong>{t('wizard.mapping.confidence')}:</strong> {Math.round(classificationResult.confidence * 100)}% | {t('wizard.mapping.provider')}:{' '}
                {classificationResult.enhanced_by_ai ? classificationResult.ai_provider || t('wizard.mapping.aiProviderFallback') : t('wizard.mapping.heuristic')}
              </div>
            </div>
          )}

          <div className="flex gap-2">
            <button className="bg-gray-200 hover:bg-gray-300 px-4 py-2 rounded" onClick={volver}>
              {t('wizard.actions.back')}
            </button>
            <button className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded" onClick={continuar}>
              {t('wizard.actions.validate')}
            </button>
          </div>
        </div>
      )}

      {step === 'validate' && (
        <div className="space-y-4">
          {errores.length > 0 ? (
            <div className="bg-rose-50 border border-rose-200 text-rose-800 p-4 rounded">
              <div className="font-semibold mb-2">{t('wizard.validation.fixIssuesBeforeContinue')}</div>
              <ul className="list-disc ml-6 text-sm">
                {errores.map((e, i) => (
                  <li key={i}>{e}</li>
                ))}
              </ul>
            </div>
          ) : (
            <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 p-4 rounded">
              {t('wizard.validation.passed')}
            </div>
          )}
          <div className="flex gap-2">
            <button className="bg-gray-200 hover:bg-gray-300 px-4 py-2 rounded" onClick={volver}>
              {t('wizard.actions.back')}
            </button>
            <button
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded"
              onClick={continuar}
              disabled={errores.length > 0}
            >
              {t('wizard.actions.continue')}
            </button>
          </div>
        </div>
      )}

      {step === 'summary' && (
        <div className="space-y-4">
          <ResumenImportacion
            total={rows.length}
            mappedCount={mappedCount}
            fieldCount={camposObjetivo.length}
            docType={docType}
            classificationResult={classificationResult}
            selectedParser={selectedParser}
          />
          <div className="flex items-center gap-3 p-3 border rounded bg-neutral-50">
            <label className="flex items-center gap-2 text-sm text-neutral-700">
              <input type="checkbox" checked={autoMode} onChange={(e) => setAutoMode(e.target.checked)} />
              {t('wizard.summary.autoModeRecommended')}
            </label>
            <span className="text-xs text-neutral-500">
              {t('wizard.summary.autoModeHelp')}
            </span>
            <div className="flex items-center gap-2 ml-auto">
              <label className="text-sm text-neutral-700">{t('wizard.summary.targetWarehouse')}:</label>
              <input
                value={targetWarehouse}
                onChange={(e) => setTargetWarehouse(e.target.value)}
                className="border rounded px-2 py-1 text-sm w-28"
                placeholder="ALM-1"
              />
            </div>
          </div>
          <div className="flex gap-2">
            <button className="bg-gray-200 hover:bg-gray-300 px-4 py-2 rounded" onClick={volver}>
              {t('wizard.actions.back')}
            </button>
            <button className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded" onClick={onImportAll}>
              {t('wizard.actions.importNow')}
            </button>
          </div>
          {savedSummary && (
            <div className="mt-3 text-sm text-neutral-800">
              <div>{t('wizard.summary.promotedWithErrors', { promoted: savedSummary.saved, errors: savedSummary.errors })}</div>
              <div className="mt-1">
                <a href="/products" className="text-blue-600 hover:underline">
                  {t('wizard.summary.goToProducts')}
                </a>
                <span className="mx-2">|</span>
                <a href="/inventory" className="text-blue-600 hover:underline">
                  {t('wizard.summary.goToInventory')}
                </a>
              </div>
            </div>
          )}
        </div>
      )}

      {step === 'importing' && (
        <div className="space-y-4">
          <ImportProgressIndicator
            progress={progress}
            progressPercent={progressPercent}
            isConnected={isConnected}
            error={wsError || saveError}
          />

          {saveError && (
            <div className="bg-rose-50 border border-rose-200 text-rose-800 p-4 rounded">
              <strong>{t('wizard.common.error')}:</strong> {saveError}
            </div>
          )}
        </div>
      )}

      <ConfirmParserModal
        isOpen={showConfirmModal}
        onClose={() => setShowConfirmModal(false)}
        onConfirm={handleConfirmParser}
        classificationResult={analysisResult ? {
          suggested_parser: analysisResult.suggested_parser,
          confidence: analysisResult.confidence,
          reason: analysisResult.explanation,
          enhanced_by_ai: analysisResult.ai_enhanced,
          ai_provider: analysisResult.ai_provider,
          probabilities: analysisResult.probabilities ?? undefined,
          available_parsers: analysisResult.available_parsers,
        } : classificationResult ? {
          suggested_parser: classificationResult.suggested_parser,
          confidence: classificationResult.confidence,
          reason: classificationResult.reason,
          enhanced_by_ai: classificationResult.enhanced_by_ai,
          ai_provider: classificationResult.ai_provider,
          probabilities: classificationResult.probabilities ?? undefined,
          available_parsers: classificationResult.available_parsers,
        } : null}
        parserRegistry={parserRegistry}
        loading={saving}
      />
    </ImportadorLayout>
  )
}

export default ImportadorWizard
