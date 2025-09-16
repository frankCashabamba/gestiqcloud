import React, { useMemo, useState } from 'react'
import VistaPreviaTabla from './components/VistaPreviaTabla'
import MapeoCampos from './components/MapeoCampos'
import ValidacionFilas from './components/ValidacionFilas'
import ResumenImportacion from './components/ResumenImportacion'
import { getAliasSugeridos } from './utils/aliasCampos'
import { autoMapeoColumnas } from './services/autoMapeoColumnas'
import { detectarTipoDocumento } from './utils/detectarTipoDocumento'
import { normalizarDocumento } from './utils/normalizarDocumento'
import { useAuth } from '../../auth/AuthContext'
import { guardarPendiente, type DatosImportadosCreate } from './services'

type Row = Record<string, string>
type Step = 'upload' | 'preview' | 'mapping' | 'validate' | 'summary'
type DocType = 'generico' | 'factura' | 'recibo' | 'transferencia'

function parseCSV(text: string): { headers: string[]; rows: Row[] } {
  const lines = text.split(/\r?\n/).filter(Boolean)
  if (lines.length === 0) return { headers: [], rows: [] }
  const headers = lines[0].split(',').map(h => h.trim())
  const rows = lines.slice(1).map(line => {
    const cols = line.split(',')
    const row: Row = {}
    headers.forEach((h, i) => (row[h] = (cols[i] ?? '').trim()))
    return row
  })
  return { headers, rows }
}

const CAMPOS_OBJETIVO = ['fecha', 'concepto', 'monto'] as const
type CampoObjetivo = typeof CAMPOS_OBJETIVO[number]

export default function ImportadorWizard() {
  const [step, setStep] = useState<Step>('upload')
  const [fileName, setFileName] = useState('')
  const [headers, setHeaders] = useState<string[]>([])
  const [rows, setRows] = useState<Row[]>([])
  const [mapa, setMapa] = useState<Partial<Record<CampoObjetivo, string>>>({})
  const [errores, setErrores] = useState<string[]>([])
  const [docType, setDocType] = useState<DocType>('generico')
  const { token } = useAuth() as { token: string | null }
  const [saving, setSaving] = useState(false)
  const [savedCount, setSavedCount] = useState<number>(0)
  const [saveError, setSaveError] = useState<string | null>(null)

  const onFile: React.ChangeEventHandler<HTMLInputElement> = async (e) => {
    const f = e.target.files?.[0]
    if (!f) return
    setFileName(f.name)
    const text = await f.text()
    const { headers: hs, rows: rs } = parseCSV(text)
    setHeaders(hs)
    setRows(rs)
    const sugeridos = autoMapeoColumnas(hs, getAliasSugeridos())
    setMapa(sugeridos as any)
    // deteccion simple de tipo
    setDocType(detectarTipoDocumento(hs))
    setStep('preview')
  }

  const previewHeaders = useMemo(() => headers, [headers])
  const previewRows = useMemo(() => rows.slice(0, 50), [rows])

  const continuar = () => {
    if (step === 'preview') setStep('mapping')
    else if (step === 'mapping') setStep('validate')
    else if (step === 'validate') setStep('summary')
  }
  const volver = () => {
    if (step === 'summary') setStep('validate')
    else if (step === 'validate') setStep('mapping')
    else if (step === 'mapping') setStep('preview')
    else if (step === 'preview') setStep('upload')
  }

  const runValidation = () => {
    const errs: string[] = []
    // Minimo: campos requeridos mapeados
    CAMPOS_OBJETIVO.forEach((c) => { if (!mapa[c]) errs.push(`Falta mapear: ${c}`) })
    // Reglas simples
    if (rows.length === 0) errs.push('El archivo no contiene filas')
    setErrores(errs)
  }

  async function onImportClick() {
    setSaveError(null)
    setSaving(true)
    try {
      const norm = normalizarDocumento(rows.slice(0, 1), mapa as any)[0] || { fecha: '', concepto: '', monto: 0 }
      const payload: DatosImportadosCreate = { tipo: 'documento', origen: 'excel', datos: { ...norm, documentoTipo: docType } }
      await guardarPendiente(payload, token || undefined)
      setSavedCount(1)
    } catch (e: any) {
      setSaveError(e?.message || 'Error al guardar')
    } finally {
      setSaving(false)
    }
  }

  async function onImportAll() {
    setSaveError(null)
    setSavedCount(0)
    setSaving(true)
    try {
      const docs = normalizarDocumento(rows, mapa as any)
      let count = 0
      for (const d of docs) {
        const payload: DatosImportadosCreate = { tipo: 'documento', origen: 'excel', datos: { ...d, documentoTipo: docType } }
        await guardarPendiente(payload, token || undefined)
        count++
      }
      setSavedCount(count)
    } catch (e: any) {
      setSaveError(e?.message || 'Error al guardar')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="p-4">
      <h2 className="text-lg font-semibold mb-4">Asistente de Importacion</h2>

      {step === 'upload' && (
        <div className="space-y-3 max-w-xl">
          <p className="text-sm text-gray-600">Selecciona un archivo CSV (separado por comas) para comenzar.</p>
          <input type="file" accept=".csv" onChange={onFile} />
        </div>
      )}

      {step === 'preview' && (
        <div>
          <div className="mb-3 text-sm text-gray-600">Archivo: {fileName} · Filas: {rows.length}</div>
          <VistaPreviaTabla headers={previewHeaders} rows={previewRows} />
          <div className="mt-3 flex gap-2">
            <button className="bg-gray-200 px-3 py-1 rounded" onClick={volver}>Volver</button>
            <button className="bg-blue-600 text-white px-3 py-1 rounded" onClick={continuar}>Continuar</button>
          </div>
        </div>
      )}

      {step === 'mapping' && (
        <div className="space-y-3">
          <div>
            <label className="block text-sm mb-1">Tipo de documento</label>
            <select value={docType} onChange={(e)=> setDocType(e.target.value as DocType)} className="border px-2 py-1 rounded text-sm">
              <option value="generico">Generico</option>
              <option value="factura">Factura</option>
              <option value="recibo">Recibo</option>
              <option value="transferencia">Transferencia</option>
            </select>
          </div>
          <MapeoCampos headers={headers} mapa={mapa} onChange={setMapa} camposObjetivo={CAMPOS_OBJETIVO as unknown as string[]} />
          <div className="mt-3 flex gap-2">
            <button className="bg-gray-200 px-3 py-1 rounded" onClick={volver}>Volver</button>
            <button className="bg-blue-600 text-white px-3 py-1 rounded" onClick={()=> { runValidation(); setStep('validate') }}>Continuar</button>
          </div>
        </div>
      )}

      {step === 'validate' && (
        <div className="space-y-3">
          <ValidacionFilas errores={errores} />
          <div className="mt-3 flex gap-2">
            <button className="bg-gray-200 px-3 py-1 rounded" onClick={volver}>Volver</button>
            <button className="bg-blue-600 text-white px-3 py-1 rounded" onClick={continuar} disabled={errores.length>0}>Continuar</button>
          </div>
        </div>
      )}

      {step === 'summary' && (
        <div className="space-y-3">
          <ResumenImportacion total={rows.length} onBack={volver} onImport={onImportClick} />
          <div className="mt-2 flex gap-2">
            <button className="bg-blue-600 text-white px-3 py-1 rounded" onClick={onImportAll} disabled={saving}>Guardar todos</button>
          </div>
          {saving && <div className="text-sm text-gray-600">Guardando...</div>}
          {!saving && savedCount > 0 && <div className="text-sm text-green-700">Guardados {savedCount} registros en pendientes.</div>}
          {saveError && <div className="text-sm text-red-700">{saveError}</div>}
          <div className="text-xs text-gray-500">
            Vista previa normalizada (primeras 5 filas):
            <pre className="bg-gray-50 p-2 rounded border overflow-auto">
{JSON.stringify(normalizarDocumento(rows.slice(0,5), mapa as any), null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  )
}

