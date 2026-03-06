import React, { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { runImport, fetchRecipes, fetchSnapshots, type RunResult, type Recipe, type RecipeSnapshot } from '../services'

const ACCEPTED = '.pdf,.jpg,.jpeg,.png,.tiff,.bmp,.xlsx,.xls,.csv,.xml,.txt'
const ACCEPTED_EXTENSIONS = new Set(['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.xlsx', '.xls', '.csv', '.xml', '.txt'])

type FileEntry = { file: File; status: 'pending' | 'done' | 'error'; result?: RunResult }
type ImportMode = 'files' | 'folder'

export default function UploadPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const fileRef = useRef<HTMLInputElement>(null)
  const folderRef = useRef<HTMLInputElement>(null)
  const reimportRequested = searchParams.get('reimport') === 'clean'
  const [mode, setMode] = useState<ImportMode>('files')
  const [dragging, setDragging] = useState(false)
  const [entries, setEntries] = useState<FileEntry[]>([])
  const [processing, setProcessing] = useState(false)
  const [results, setResults] = useState<RunResult[]>([])
  const [error, setError] = useState('')
  const [forceReprocess, setForceReprocess] = useState(reimportRequested)

  // Recipe selector (RB-01: optional, never blocks)
  const [recipes, setRecipes] = useState<Recipe[]>([])
  const [snapshots, setSnapshots] = useState<RecipeSnapshot[]>([])
  const [selectedRecipeId, setSelectedRecipeId] = useState('')
  const [selectedSnapshotId, setSelectedSnapshotId] = useState('')
  const [recipesLoading, setRecipesLoading] = useState(false)

  useEffect(() => {
    setRecipesLoading(true)
    fetchRecipes().then(setRecipes).catch(() => {}).finally(() => setRecipesLoading(false))
  }, [])

  useEffect(() => {
    if (reimportRequested) setForceReprocess(true)
  }, [reimportRequested])

  useEffect(() => {
    if (!selectedRecipeId) { setSnapshots([]); setSelectedSnapshotId(''); return }
    fetchSnapshots(selectedRecipeId)
      .then(snaps => { setSnapshots(snaps); setSelectedSnapshotId(snaps[0]?.id || '') })
      .catch(() => setSnapshots([]))
  }, [selectedRecipeId])

  const addFiles = useCallback((fileList: FileList | File[]) => {
    const incoming = Array.from(fileList || []).filter(f => {
      if (!f || f.size < 0) return false
      const ext = '.' + f.name.split('.').pop()?.toLowerCase()
      return ACCEPTED_EXTENSIONS.has(ext)
    })
    if (!incoming.length) return
    setEntries(prev => {
      const existingKeys = new Set(prev.map(e => `${e.file.name}-${e.file.size}`))
      const merged = [...prev]
      incoming.forEach(f => {
        const key = `${f.name}-${f.size}`
        if (!existingKeys.has(key)) merged.push({ file: f, status: 'pending' })
      })
      return merged
    })
  }, [])

  const removeEntry = (idx: number) => setEntries(prev => prev.filter((_, i) => i !== idx))
  const clearAll = () => { setEntries([]); setResults([]) }

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    addFiles(e.dataTransfer.files)
  }, [addFiles])

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.length) addFiles(e.target.files)
    e.target.value = ''
  }

  const onFolderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.length) addFiles(e.target.files)
    e.target.value = ''
  }

  // Procesar de a lotes de 5 para mostrar progreso en tiempo real
  const handleRun = async () => {
    const pendingEntries = entries.filter(e => e.status === 'pending')
    if (!pendingEntries.length) return
    setProcessing(true)
    setError('')
    setResults([])

    const opts = {
      ...(selectedSnapshotId ? { recipe_snapshot_id: selectedSnapshotId } : {}),
      force: forceReprocess,
    }
    const allResults: RunResult[] = []
    const BATCH = 5

    for (let i = 0; i < pendingEntries.length; i += BATCH) {
      const batch = pendingEntries.slice(i, i + BATCH)
      const batchFiles = batch.map(e => e.file)
      const batchKeys = new Set(batchFiles.map(f => `${f.name}-${f.size}`))

      // Marcar como procesando
      setEntries(prev => prev.map(e =>
        batchKeys.has(`${e.file.name}-${e.file.size}`) ? { ...e, status: 'pending' } : e
      ))

      try {
        const batchResults = await runImport(batchFiles, opts)
        allResults.push(...batchResults)
        // Marcar como done
        setEntries(prev => prev.map((e, idx) => {
          const batchIdx = batch.findIndex(b => b.file === e.file)
          if (batchIdx === -1) return e
          return { ...e, status: 'done', result: batchResults[batchIdx] }
        }))
        setResults([...allResults])
      } catch (err: any) {
        setEntries(prev => prev.map(e =>
          batchKeys.has(`${e.file.name}-${e.file.size}`) ? { ...e, status: 'error' } : e
        ))
        setError(err?.response?.data?.detail || `Error en lote ${Math.floor(i / BATCH) + 1}`)
      }
    }

    setProcessing(false)
  }

  const confBadge = (conf: number | undefined) => {
    if (conf == null) return null
    const pct = Math.round(conf * 100)
    const color = pct >= 85 ? '#10B981' : pct >= 50 ? '#F59E0B' : '#EF4444'
    return <span style={{ background: color, color: '#fff', padding: '2px 8px', borderRadius: 12, fontSize: 12 }}>{pct}%</span>
  }

  const recipeLabel = (mode: string | undefined) => {
    const labels: Record<string, string> = {
      zero_shot: 'Zero-shot', snapshot: 'Snapshot', draft: 'Borrador',
      recipe_latest: 'Receta', auto_fingerprint: 'Auto-plantilla',
      auto_text_fingerprint: 'Auto-plantilla',
      force_clean: 'Reimportacion limpia',
    }
    return labels[mode || ''] || mode || ''
  }

  const pendingCount = entries.filter(e => e.status === 'pending').length
  const doneCount = entries.filter(e => e.status === 'done').length
  const errorCount = entries.filter(e => e.status === 'error').length

  return (
    <div style={{ padding: '1.5rem', maxWidth: 860 }}>
      <button onClick={() => navigate(-1)} style={{ marginBottom: '1rem', cursor: 'pointer', border: 'none', background: 'none', fontSize: 14, color: '#6366F1' }}>
        ← Volver
      </button>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
        <h2 style={{ margin: 0 }}>Importar Documentos Contables</h2>
        {entries.length > 0 && !processing && (
          <button onClick={clearAll} style={{ fontSize: 13, color: '#6b7280', border: 'none', background: 'none', cursor: 'pointer' }}>
            Limpiar todo
          </button>
        )}
      </div>

      {reimportRequested && (
        <div style={{ marginBottom: '1rem', padding: '0.75rem 1rem', background: '#EFF6FF', border: '1px solid #BFDBFE', borderRadius: 8, color: '#1d4ed8', fontSize: 13 }}>
          Reimportacion limpia activada. Vuelve a subir el archivo original; si no eliges una plantilla manual, se reprocesara con prompt generico y sin reutilizar auto-plantillas previas para sesgar la clasificacion.
        </div>
      )}

      {/* Mode toggle */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
        {(['files', 'folder'] as ImportMode[]).map(m => (
          <button
            key={m}
            onClick={() => setMode(m)}
            style={{
              padding: '0.4rem 1rem', borderRadius: 6, border: '1px solid #d1d5db', cursor: 'pointer', fontSize: 13,
              background: mode === m ? '#6366F1' : '#fff', color: mode === m ? '#fff' : '#374151', fontWeight: mode === m ? 600 : 400,
            }}
          >
            {m === 'files' ? 'Archivos individuales' : 'Seleccionar carpeta'}
          </button>
        ))}
      </div>

      {/* Drop zone — archivos individuales */}
      {mode === 'files' && (
        <div
          onDragOver={e => { e.preventDefault(); setDragging(true) }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          onClick={() => fileRef.current?.click()}
          style={{
            border: `2px dashed ${dragging ? '#6366F1' : '#d1d5db'}`, borderRadius: 12, padding: '2rem',
            textAlign: 'center', cursor: 'pointer', background: dragging ? '#EEF2FF' : '#f9fafb', transition: 'all 0.2s',
          }}
        >
          <div style={{ fontSize: 40, marginBottom: '0.5rem' }}>📎</div>
          <p style={{ fontSize: 15, fontWeight: 600, margin: '0 0 4px' }}>Arrastra archivos o haz clic para seleccionar</p>
          <p style={{ fontSize: 13, color: '#6b7280', margin: 0 }}>PDF, JPG/PNG, Excel, CSV, XML, TXT</p>
          <input ref={fileRef} type="file" multiple accept={ACCEPTED} onChange={onFileChange} style={{ display: 'none' }} />
        </div>
      )}

      {/* Selector de carpeta */}
      {mode === 'folder' && (
        <div
          onClick={() => folderRef.current?.click()}
          style={{
            border: '2px dashed #d1d5db', borderRadius: 12, padding: '2rem', textAlign: 'center',
            cursor: 'pointer', background: '#f9fafb', transition: 'all 0.2s',
          }}
        >
          <div style={{ fontSize: 40, marginBottom: '0.5rem' }}>📁</div>
          <p style={{ fontSize: 15, fontWeight: 600, margin: '0 0 4px' }}>Seleccionar carpeta</p>
          <p style={{ fontSize: 13, color: '#6b7280', margin: 0 }}>
            Se importarán todos los documentos contables de la carpeta seleccionada
          </p>
          <p style={{ fontSize: 12, color: '#9ca3af', marginTop: 8 }}>
            Formatos soportados: PDF, JPG/PNG, Excel, CSV, XML, TXT (los demás se omiten)
          </p>
          <input
            ref={folderRef}
            type="file"
            multiple
            // @ts-ignore — webkitdirectory no está en los tipos estándar
            webkitdirectory=""
            onChange={onFolderChange}
            style={{ display: 'none' }}
          />
        </div>
      )}

      {/* Lista de archivos pendientes */}
      {entries.length > 0 && (
        <div style={{ marginTop: '1rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <h4 style={{ margin: 0, fontSize: 14 }}>
              {entries.length} archivo{entries.length > 1 ? 's' : ''}
              {processing && <span style={{ color: '#6b7280', fontWeight: 400 }}>
                {' '}— procesando {doneCount + errorCount}/{entries.length}
              </span>}
            </h4>
            {doneCount > 0 && <span style={{ fontSize: 12, color: '#10B981' }}>{doneCount} completados</span>}
            {errorCount > 0 && <span style={{ fontSize: 12, color: '#EF4444' }}>{errorCount} errores</span>}
          </div>
          <div style={{ maxHeight: 240, overflowY: 'auto', border: '1px solid #e5e7eb', borderRadius: 8 }}>
            {entries.map((entry, i) => (
              <div key={i} style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '0.4rem 0.75rem', background: '#fff', borderBottom: '1px solid #f3f4f6', fontSize: 13,
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', minWidth: 0 }}>
                  <span style={{ fontSize: 16 }}>
                    {entry.status === 'done' ? '✅' : entry.status === 'error' ? '❌' : '📄'}
                  </span>
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {entry.file.name}
                  </span>
                  <span style={{ color: '#9ca3af', fontSize: 11, flexShrink: 0 }}>
                    ({(entry.file.size / 1024).toFixed(0)} KB)
                  </span>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexShrink: 0 }}>
                  {entry.result && (
                    <span style={{
                      background: '#e0e7ff', padding: '1px 6px', borderRadius: 4, fontSize: 11,
                    }}>
                      {entry.result.tipo_documento_detectado || '?'}
                    </span>
                  )}
                  {entry.status === 'pending' && !processing && (
                    <button onClick={() => removeEntry(i)} style={{ border: 'none', background: 'none', color: '#9ca3af', cursor: 'pointer', fontSize: 14, padding: 0 }}>×</button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recipe selector (RB-01: opcional) */}
      <div style={{ marginTop: '1rem', padding: '0.75rem 1rem', background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
          <span style={{ fontSize: 13, fontWeight: 600 }}>Plantilla / Receta</span>
          <span style={{ fontSize: 11, color: '#6b7280', background: '#e0e7ff', padding: '1px 8px', borderRadius: 10 }}>opcional</span>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <select
            value={selectedRecipeId}
            onChange={e => setSelectedRecipeId(e.target.value)}
            style={{ padding: '0.4rem 0.5rem', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 13, minWidth: 200 }}
          >
            <option value="">Auto-detectar (recomendado)</option>
            {recipesLoading && <option disabled>Cargando plantillas...</option>}
            {recipes.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
          </select>
          {selectedRecipeId && snapshots.length > 0 && (
            <select
              value={selectedSnapshotId}
              onChange={e => setSelectedSnapshotId(e.target.value)}
              style={{ padding: '0.4rem 0.5rem', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 13, minWidth: 180 }}
            >
              {snapshots.map(s => (
                <option key={s.id} value={s.id}>{s.version_tag || `v${new Date(s.created_at).toLocaleDateString()}`}</option>
              ))}
            </select>
          )}
          {selectedRecipeId && snapshots.length === 0 && (
            <span style={{ fontSize: 12, color: '#F59E0B', alignSelf: 'center' }}>Sin snapshots — se usará auto-detección</span>
          )}
        </div>
      </div>

      {/* Opción forzar reimportación */}
      <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.75rem', fontSize: 13, color: '#6b7280', cursor: 'pointer', userSelect: 'none' }}>
        <input
          type="checkbox"
          checked={forceReprocess}
          onChange={e => setForceReprocess(e.target.checked)}
          style={{ width: 15, height: 15, cursor: 'pointer' }}
        />
        <span>
          Reimportacion limpia
          <span style={{ color: '#9ca3af', marginLeft: 4 }}>
            (omite dedupe y, si no eliges una plantilla manual, reprocesa con prompt generico sin reutilizar auto-plantillas previas)
          </span>
        </span>
      </label>

      {/* Botón procesar */}
      <button
        onClick={handleRun}
        disabled={pendingCount === 0 || processing}
        style={{
          marginTop: '1rem', width: '100%', padding: '0.75rem',
          background: pendingCount === 0 ? '#d1d5db' : '#6366F1',
          color: '#fff', border: 'none', borderRadius: 8, fontSize: 16, fontWeight: 700,
          cursor: pendingCount === 0 ? 'not-allowed' : 'pointer',
        }}
      >
        {processing
          ? `Procesando ${doneCount + errorCount} / ${entries.length}...`
          : pendingCount > 0 ? `Importar ${pendingCount} documento${pendingCount > 1 ? 's' : ''}` : 'Importar documentos'}
      </button>

      {error && (
        <div style={{ marginTop: '0.75rem', padding: '0.75rem', background: '#FEF2F2', border: '1px solid #FECACA', borderRadius: 8, color: '#991B1B', fontSize: 14 }}>
          {error}
        </div>
      )}

      {/* Resultados */}
      {results.length > 0 && (
        <div style={{ marginTop: '1.25rem' }}>
          <h3 style={{ marginBottom: '0.75rem' }}>
            Resultados — {results.filter(r => r.estado !== 'FAILED').length}/{results.length} procesados
          </h3>
          {results.map((r, i) => (
            <div key={r.id || i} style={{
              border: `1px solid ${r.auto_recipe_created ? '#BBF7D0' : '#e5e7eb'}`,
              borderRadius: 8, padding: '0.75rem', marginBottom: '0.5rem',
              background: r.auto_recipe_created ? '#F0FDF4' : '#fff',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                  <span style={{ fontWeight: 600 }}>{r.tipo_documento_detectado || '—'}</span>
                  {confBadge(r.confianza_clasificacion)}
                  {r.requiere_revision && (
                    <span style={{ color: '#F59E0B', fontSize: 12 }}>Requiere revisión</span>
                  )}
                </div>
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                  <span style={{ fontSize: 12, color: r.estado === 'FAILED' ? '#EF4444' : '#10B981', fontWeight: 600 }}>
                    {r.estado}
                  </span>
                  {r.estado !== 'FAILED' && (
                    <button
                      onClick={() => navigate(`../documents/${r.id}`)}
                      style={{ padding: '3px 10px', border: '1px solid #6366F1', borderRadius: 6, background: '#fff', color: '#6366F1', cursor: 'pointer', fontSize: 12 }}
                    >
                      Revisar
                    </button>
                  )}
                </div>
              </div>

              {/* Plantilla auto-guardada */}
              {r.auto_recipe_created && r.auto_recipe_name && (
                <div style={{ marginTop: '0.4rem', fontSize: 12, color: '#166534', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <span>Plantilla guardada:</span>
                  <span style={{ background: '#BBF7D0', padding: '1px 8px', borderRadius: 10, fontWeight: 600 }}>{r.auto_recipe_name}</span>
                  <span style={{ color: '#6b7280' }}>— se reutilizará en futuros documentos similares</span>
                </div>
              )}

              <div style={{ marginTop: '0.4rem', display: 'flex', gap: '0.5rem', fontSize: 11, color: '#6b7280', flexWrap: 'wrap' }}>
                <span style={{ background: '#f3f4f6', padding: '1px 6px', borderRadius: 4 }}>{recipeLabel(r.recipe_used)}</span>
                {r.llm_model && <span style={{ background: '#f3f4f6', padding: '1px 6px', borderRadius: 4 }}>{r.llm_model}</span>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
