/**
 * Wizard de importación con pipeline real:
 * - createBatch + ingestBatch (productos)
 * - Resumen con toggle "Modo automático" (activa, crea almacén y aplica stock)
 * - promote del batch con flags
 */
import React, { useMemo, useState } from 'react'
import { useAuth } from '../../auth/AuthContext'

import VistaPreviaTabla from './components/VistaPreviaTabla'
import ResumenImportacion from './components/ResumenImportacion'
import { ClassificationSuggestion } from './components/ClassificationSuggestion'
import { AIProviderSettings } from './components/AIProviderSettings'
import { ImportProgressIndicator } from './components/ImportProgressIndicator'
import { useImportProgress } from './hooks/useImportProgress'
import { getAliasSugeridos } from './utils/aliasCampos'
import { autoMapeoColumnas } from './services/autoMapeoColumnas'
import { detectarTipoDocumento } from './utils/detectarTipoDocumento'
import { normalizarDocumento } from './utils/normalizarDocumento'
import { createBatch, ingestBatch } from './services/importsApi'
import { useClassifyFile } from './hooks/useClassifyFile'
import { useParserRegistry } from './hooks/useParserRegistry'

type Row = Record<string, string>
type Step = 'upload' | 'preview' | 'mapping' | 'validate' | 'summary' | 'importing'
type DocType = 'generico' | 'productos'

function parseCSV(text: string): { headers: string[]; rows: Row[] } {
    const lines = text.split(/\r?\n/).filter(Boolean)
    if (lines.length === 0) return { headers: [], rows: [] }
    const headers = lines[0].split(',').map((h) => h.trim())
    const rows = lines.slice(1).map((line) => {
        const cols = line.split(',')
        const row: Row = {}
        headers.forEach((h, i) => (row[h] = (cols[i] ?? '').trim()))
        return row
    })
    return { headers, rows }
}

const CAMPOS_OBJETIVO = ['nombre', 'precio'] as const
type CampoObjetivo = typeof CAMPOS_OBJETIVO[number]

export default function ImportadorWizard() {
    const { token } = useAuth() as { token: string | null }
    const { classify, loading: classifying, result: classificationResult, error: classificationError, confidence } = useClassifyFile()
    const { registry: parserRegistry } = useParserRegistry(token || undefined)

    // Estados del wizard
    const [step, setStep] = useState<Step>('upload')
    const [fileName, setFileName] = useState('')
    const [headers, setHeaders] = useState<string[]>([])
    const [rows, setRows] = useState<Row[]>([])
    const [mapa, setMapa] = useState<Partial<Record<CampoObjetivo, string>>>({})
    const [errores, setErrores] = useState<string[]>([])
    const [docType, setDocType] = useState<DocType>('productos')
    const [currentFile, setCurrentFile] = useState<File | null>(null)

    const [saving, setSaving] = useState(false)
    const [savedCount, setSavedCount] = useState<number>(0)
    const [saveError, setSaveError] = useState<string | null>(null)
    const [batchId, setBatchId] = useState<string | null>(null)
    const [savedSummary, setSavedSummary] = useState<{ saved: number; errors: number; lastBatchId?: string } | null>(null)

    // Modo automático
    const [autoMode, setAutoMode] = useState(true)
    const [targetWarehouse, setTargetWarehouse] = useState('ALM-1')

    // Sprint 2: Override manual del parser
    const [selectedParser, setSelectedParser] = useState<string | null>(null)

    // Sprint 3: WebSocket progress
    const { progress, progressPercent, isConnected, error: wsError } = useImportProgress({
        batchId: batchId || undefined,
        token: token || undefined
    })

    // Upload handler with AI classification
    const onFile: React.ChangeEventHandler<HTMLInputElement> = async (e) => {
        const f = e.target.files?.[0]
        if (!f) return
        setFileName(f.name)
        setCurrentFile(f)

        // Parse CSV
        const text = await f.text()
        const { headers: hs, rows: rs } = parseCSV(text)
        setHeaders(hs)
        setRows(rs)

        // Auto-mapeo inicial y tipo
        const sugeridos = autoMapeoColumnas(hs, getAliasSugeridos())
        setMapa(sugeridos as any)
        setDocType(detectarTipoDocumento(hs) as DocType || 'productos')

        // Clasificar archivo con IA
        try {
            await classify(f)
        } catch (err) {
            console.warn('IA classification failed, using heuristic:', err)
        }

        setStep('preview')
    }

    const previewHeaders = useMemo(() => headers, [headers])
    const previewRows = useMemo(() => rows.slice(0, 50), [rows])

    const continuar = () => {
        if (step === 'upload') setStep('preview')
        else if (step === 'preview') setStep('mapping')
        else if (step === 'mapping') { runValidation(); setStep('validate') }
        else if (step === 'validate') setStep('summary')
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
        CAMPOS_OBJETIVO.forEach((c) => { if (!mapa[c]) errs.push(`Falta mapear: ${c}`) })
        if (rows.length === 0) errs.push('El archivo no contiene filas')
        if (rows.length > 10000) errs.push('Máximo 10,000 filas por importación')
        setErrores(errs)
    }

    async function onImportAll() {
        setSaveError(null)
        setSavedCount(0)
        setSaving(true)
        setStep('importing')
        try {
            const docs = normalizarDocumento(rows, mapa as any)
            // 1) Crear batch real con clasificación
            const batchPayload: any = {
                source_type: 'productos',
                origin: 'excel_ui'
            }
            // Incluir campos de clasificación si están disponibles
             if (classificationResult) {
                 // Sprint 2: usar override manual si existe, sino usar sugerencia
                 batchPayload.suggested_parser = selectedParser || classificationResult.suggested_parser
                 batchPayload.classification_confidence = classificationResult.confidence
                 batchPayload.ai_enhanced = classificationResult.enhanced_by_ai
                 batchPayload.ai_provider = classificationResult.ai_provider
             }
            const batch = await createBatch(batchPayload, token || undefined)
            setBatchId(batch.id)
            // 2) Ingestar filas
            await ingestBatch(batch.id, { rows: docs }, token || undefined, null)
            setSavedCount(docs.length)
            // 3) Promover con flags automáticos
            try {
                const url = new URL(`/api/v1/imports/batches/${batch.id}/promote`, window.location.origin)
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
            } catch { /* ignore */ }
        } catch (e: any) {
            setSaveError(e?.message || 'Error al importar')
        } finally {
            setSaving(false)
        }
    }

    const resetWizard = () => {
        setStep('upload'); setFileName(''); setHeaders([]); setRows([]); setMapa({}); setErrores([])
        setSavedCount(0); setSaveError(null); setBatchId(null); setSavedSummary(null)
        setSelectedParser(null) // Sprint 2: reset parser override
    }

    return (
        <div className="p-4 max-w-6xl mx-auto">
            {/* Pasos */}
            <div className="mb-6">
                <div className="flex items-center justify-between text-sm">
                    {[
                        { key: 'upload', label: '1. Upload' },
                        { key: 'preview', label: '2. Preview' },
                        { key: 'mapping', label: '3. Mapeo' },
                        { key: 'validate', label: '4. Validación' },
                        { key: 'summary', label: '5. Resumen' },
                        { key: 'importing', label: '6. Importando' },
                    ].map((s, idx) => (
                        <React.Fragment key={s.key}>
                            <div className={`flex items-center gap-2 ${step === s.key ? 'text-blue-600 font-semibold' : idx < ['upload', 'preview', 'mapping', 'validate', 'summary', 'importing'].indexOf(step) ? 'text-green-600' : 'text-gray-400'}`}>
                                <div className={`w-8 h-8 rounded-full flex items-center justify-center border-2 ${step === s.key ? 'border-blue-600 bg-blue-50' : idx < ['upload', 'preview', 'mapping', 'validate', 'summary', 'importing'].indexOf(step) ? 'border-green-600 bg-green-50' : 'border-gray-300'}`}>
                                    {idx < ['upload', 'preview', 'mapping', 'validate', 'summary', 'importing'].indexOf(step) ? '✔' : idx + 1}
                                </div>
                                <span className="hidden sm:inline">{s.label}</span>
                            </div>
                            {idx < 5 && <div className="flex-1 h-0.5 bg-gray-300" />}
                        </React.Fragment>
                    ))}
                </div>
            </div>

            <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-bold">Asistente de Importación</h2>
                <AIProviderSettings />
            </div>

            {/* Upload */}
            {step === 'upload' && (
                <div className="space-y-4 max-w-xl">
                    <p className="text-gray-600">Selecciona un archivo CSV (o exporta Excel como CSV) para comenzar.</p>
                    <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-blue-500 transition">
                        <input type="file" accept=".csv" onChange={onFile} className="hidden" id="file-upload" />
                        <label htmlFor="file-upload" className="cursor-pointer block">
                            <div className="text-4xl mb-2">📥</div>
                            <div className="text-blue-600 font-medium">Haz clic para seleccionar archivo</div>
                            <div className="text-sm text-gray-500 mt-1">Formato: CSV (coma)</div>
                        </label>
                    </div>
                </div>
            )}

            {/* Preview */}
            {step === 'preview' && (
                <div className="space-y-4">
                    <div className="bg-blue-50 border border-blue-200 px-4 py-3 rounded">
                        Archivo: <strong>{fileName}</strong> • {rows.length.toLocaleString()} filas • {headers.length} columnas
                    </div>

                    {/* AI Classification Suggestion */}
                    <ClassificationSuggestion
                        result={classificationResult}
                        loading={classifying}
                        error={classificationError}
                        confidence={confidence}
                    />

                    <VistaPreviaTabla headers={previewHeaders} rows={previewRows} />
                    <div className="flex gap-2">
                        <button className="bg-gray-200 hover:bg-gray-300 px-4 py-2 rounded" onClick={volver}>← Volver</button>
                        <button className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded" onClick={continuar}>Continuar</button>
                    </div>
                </div>
            )}

            {/* Mapping/Validate: placeholders rápidos */}
            {step === 'mapping' && (
                <div className="space-y-4">
                    <div className="bg-neutral-50 border px-4 py-3 rounded text-neutral-700 text-sm">Mapea columnas si es necesario (automapeo aplicado).</div>

                    {/* Sprint 2: Parser override selector */}
                    {classificationResult && parserRegistry && (
                        <div className="border-2 border-blue-300 rounded-lg p-4 bg-blue-50">
                            <label className="block text-sm font-semibold text-gray-700 mb-3">
                                🔄 Parser seleccionado
                            </label>
                            <div className="flex gap-3 items-start mb-3">
                                <select
                                    value={selectedParser || classificationResult.suggested_parser || ''}
                                    onChange={(e) => setSelectedParser(e.target.value || null)}
                                    className="flex-1 border border-gray-300 rounded px-3 py-2 text-sm font-medium"
                                >
                                    <option value="">— Usar sugerencia: <strong>{classificationResult.suggested_parser}</strong> —</option>
                                    {Object.entries(parserRegistry.parsers).map(([id, parser]) => (
                                        <option key={id} value={id}>
                                            {id} ({parser.doc_type})
                                        </option>
                                    ))}
                                </select>
                                {selectedParser && (
                                    <span className="text-xs bg-amber-100 text-amber-800 px-3 py-2 rounded font-bold whitespace-nowrap">
                                        ⚠️ OVERRIDE
                                    </span>
                                )}
                            </div>

                            {/* Info adicional */}
                            {selectedParser && parserRegistry.parsers[selectedParser] && (
                                <div className="bg-white border border-blue-200 rounded p-3 mb-2 text-xs">
                                    <strong>Seleccionado:</strong> {selectedParser}<br/>
                                    <strong>Tipo:</strong> {parserRegistry.parsers[selectedParser].doc_type}<br/>
                                    {parserRegistry.parsers[selectedParser].description && (
                                        <><strong>Descripción:</strong> {parserRegistry.parsers[selectedParser].description}</>
                                    )}
                                </div>
                            )}

                            <div className="text-xs text-gray-600 bg-white rounded p-2 border border-gray-200">
                                <strong>Sugerencia:</strong> {Math.round(classificationResult.confidence * 100)}% confianza •
                                Proveedor: {classificationResult.enhanced_by_ai ? classificationResult.ai_provider || 'IA' : 'Heurística'}
                            </div>
                        </div>
                    )}

                    <div className="flex gap-2">
                        <button className="bg-gray-200 hover:bg-gray-300 px-4 py-2 rounded" onClick={volver}>← Volver</button>
                        <button className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded" onClick={continuar}>Validar</button>
                    </div>
                </div>
            )}

            {step === 'validate' && (
                <div className="space-y-4">
                    {errores.length > 0 ? (
                        <div className="bg-rose-50 border border-rose-200 text-rose-800 p-4 rounded">
                            <div className="font-semibold mb-2">Corrige antes de continuar:</div>
                            <ul className="list-disc ml-6 text-sm">
                                {errores.map((e, i) => (<li key={i}>{e}</li>))}
                            </ul>
                        </div>
                    ) : (
                        <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 p-4 rounded">Validación correcta.</div>
                    )}
                    <div className="flex gap-2">
                        <button className="bg-gray-200 hover:bg-gray-300 px-4 py-2 rounded" onClick={volver}>← Volver</button>
                        <button className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded" onClick={continuar} disabled={errores.length > 0}>Continuar</button>
                    </div>
                </div>
            )}

            {step === 'summary' && (
                <div className="space-y-4">
                    <ResumenImportacion
                        total={rows.length}
                        onBack={volver}
                        onImport={() => { }}
                        classificationResult={classificationResult}
                        selectedParser={selectedParser}
                    />
                    <div className="flex items-center gap-3 p-3 border rounded bg-neutral-50">
                        <label className="flex items-center gap-2 text-sm text-neutral-700">
                            <input type="checkbox" checked={autoMode} onChange={(e) => setAutoMode(e.target.checked)} />
                            Modo automático (recomendado)
                        </label>
                        <span className="text-xs text-neutral-500">Activa productos, crea ALM-1 si falta y aplica stock inicial.</span>
                        <div className="flex items-center gap-2 ml-auto">
                            <label className="text-sm text-neutral-700">Almacén destino:</label>
                            <input value={targetWarehouse} onChange={(e) => setTargetWarehouse(e.target.value)} className="border rounded px-2 py-1 text-sm w-28" placeholder="ALM-1" />
                        </div>
                    </div>
                    <div className="flex gap-2">
                        <button className="bg-gray-200 hover:bg-gray-300 px-4 py-2 rounded" onClick={volver}>← Volver</button>
                        <button className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded" onClick={onImportAll}>Importar ahora</button>
                    </div>
                    {savedSummary && (
                        <div className="mt-3 text-sm text-neutral-800">
                            <div>Promovidos: {savedSummary.saved} | Errores: {savedSummary.errors}</div>
                            <div className="mt-1">
                                <a href="/productos" className="text-blue-600 hover:underline">Ir a Productos</a>
                                <span className="mx-2">•</span>
                                <a href="/inventario" className="text-blue-600 hover:underline">Ir a Inventario</a>
                            </div>
                        </div>
                    )}
                </div>
            )}

            {step === 'importing' && (
                <div className="space-y-4">
                    {/* Sprint 3: WebSocket progress indicator */}
                    <ImportProgressIndicator
                        progress={progress}
                        progressPercent={progressPercent}
                        isConnected={isConnected}
                        error={wsError || saveError}
                    />

                    {saveError && (
                        <div className="bg-rose-50 border border-rose-200 text-rose-800 p-4 rounded">
                            <strong>Error:</strong> {saveError}
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}
