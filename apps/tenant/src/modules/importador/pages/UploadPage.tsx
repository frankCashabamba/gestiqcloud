import React, { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { runImport, fetchRecipes, fetchSnapshots, type RunResult, type Recipe, type RecipeSnapshot } from '../services'

const ACCEPTED = '.pdf,.jpg,.jpeg,.png,.tiff,.bmp,.xlsx,.xls,.csv,.xml,.txt'

export default function UploadPage() {
  const navigate = useNavigate()
  const fileRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [processing, setProcessing] = useState(false)
  const [results, setResults] = useState<RunResult[]>([])
  const [error, setError] = useState('')

  // Recipe selector (optional — RB-01: never blocks processing)
  const [recipes, setRecipes] = useState<Recipe[]>([])
  const [snapshots, setSnapshots] = useState<RecipeSnapshot[]>([])
  const [selectedRecipeId, setSelectedRecipeId] = useState('')
  const [selectedSnapshotId, setSelectedSnapshotId] = useState('')
  const [recipesLoading, setRecipesLoading] = useState(false)

  useEffect(() => {
    setRecipesLoading(true)
    fetchRecipes()
      .then(setRecipes)
      .catch(() => {}) // RB-01: recipe load failure does NOT block processing
      .finally(() => setRecipesLoading(false))
  }, [])

  useEffect(() => {
    if (!selectedRecipeId) { setSnapshots([]); setSelectedSnapshotId(''); return }
    fetchSnapshots(selectedRecipeId)
      .then(snaps => { setSnapshots(snaps); setSelectedSnapshotId(snaps[0]?.id || '') })
      .catch(() => setSnapshots([]))
  }, [selectedRecipeId])

  const addFiles = useCallback((fileList: FileList | File[]) => {
    // Normalizamos a array, filtrando vacíos y duplicados por nombre+tamaño para evitar estados raros
    const incoming = Array.from(fileList || []).filter(f => f && f.size >= 0)
    if (!incoming.length) return
    setSelectedFiles(prev => {
      const existingKeys = new Set(prev.map(f => `${f.name}-${f.size}`))
      const merged = [...prev]
      incoming.forEach(f => {
        const key = `${f.name}-${f.size}`
        if (!existingKeys.has(key)) merged.push(f)
      })
      return merged
    })
  }, [])

  const removeFile = (idx: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== idx))
  }

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    addFiles(e.dataTransfer.files)
  }, [addFiles])

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files?.length) addFiles(files)
    // Permite seleccionar el mismo archivo de nuevo
    e.target.value = ''
  }

  // CA-01: Procesar ALWAYS enabled when files exist (never depends on recipe)
  const handleRun = async () => {
    if (!selectedFiles.length) return
    setProcessing(true)
    setError('')
    setResults([])
    try {
      const res = await runImport(
        selectedFiles,
        selectedSnapshotId ? { recipe_snapshot_id: selectedSnapshotId } : undefined,
      )
      setResults(res)
      setSelectedFiles([])
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Error procesando archivos')
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
      zero_shot: '🧠 Zero-shot',
      snapshot: '📌 Snapshot',
      draft: '📝 Borrador',
      recipe_latest: '📋 Última versión',
    }
    return labels[mode || ''] || mode || ''
  }

  return (
    <div style={{ padding: '1.5rem', maxWidth: 800 }}>
      <button onClick={() => navigate(-1)} style={{ marginBottom: '1rem', cursor: 'pointer', border: 'none', background: 'none', fontSize: 14, color: '#6366F1' }}>← Volver</button>
      <h2>⬆️ Procesar Documentos</h2>

      {/* Drop zone */}
      <label
        htmlFor="importador-upload-input"
        onDragOver={e => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => fileRef.current?.click()}
        onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fileRef.current?.click() } }}
        tabIndex={0}
        style={{ border: `2px dashed ${dragging ? '#6366F1' : '#d1d5db'}`, borderRadius: 12, padding: '2.5rem', textAlign: 'center', cursor: 'pointer', background: dragging ? '#EEF2FF' : '#f9fafb', transition: 'all 0.2s', display: 'block' }}
      >
        <div style={{ fontSize: 48, marginBottom: '0.5rem' }}>📎</div>
        <p style={{ fontSize: 16, fontWeight: 600 }}>Arrastra archivos aquí o haz clic para seleccionar</p>
        <p style={{ fontSize: 13, color: '#6b7280' }}>PDF, imágenes (JPG/PNG), Excel, CSV, XML, TXT</p>
        <input
          id="importador-upload-input"
          ref={fileRef}
          type="file"
          multiple
          accept={ACCEPTED}
          onChange={onFileChange}
          onInput={onFileChange}
          style={{ position: 'absolute', opacity: 0, width: 1, height: 1, pointerEvents: 'none' }}
        />
      </label>

      {/* Selected files */}
      {selectedFiles.length > 0 && (
        <div style={{ marginTop: '1rem' }}>
          <h4 style={{ marginBottom: '0.5rem' }}>Archivos seleccionados ({selectedFiles.length})</h4>
          {selectedFiles.map((f, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.4rem 0.75rem', background: '#fff', border: '1px solid #e5e7eb', borderRadius: 6, marginBottom: 4, fontSize: 14 }}>
              <span>{f.name} <span style={{ color: '#9ca3af', fontSize: 12 }}>({(f.size / 1024).toFixed(0)} KB)</span></span>
              <button onClick={() => removeFile(i)} style={{ border: 'none', background: 'none', color: '#EF4444', cursor: 'pointer', fontSize: 16 }}>×</button>
            </div>
          ))}
        </div>
      )}

      {/* Recipe selector (optional — RB-01) */}
      <div style={{ marginTop: '1rem', padding: '1rem', background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
          <span style={{ fontSize: 14, fontWeight: 600 }}>📋 Receta (opcional)</span>
          <span style={{ fontSize: 12, color: '#6b7280', background: '#e0e7ff', padding: '1px 8px', borderRadius: 10 }}>RB-01: no requerida</span>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <select
            value={selectedRecipeId}
            onChange={e => setSelectedRecipeId(e.target.value)}
            style={{ padding: '0.4rem 0.5rem', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 13, minWidth: 200 }}
          >
            <option value="">Sin receta (Zero-shot) 🧠</option>
            {recipesLoading && <option disabled>Cargando recetas...</option>}
            {recipes.map(r => (
              <option key={r.id} value={r.id}>{r.name}</option>
            ))}
          </select>
          {selectedRecipeId && snapshots.length > 0 && (
            <select
              value={selectedSnapshotId}
              onChange={e => setSelectedSnapshotId(e.target.value)}
              style={{ padding: '0.4rem 0.5rem', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 13, minWidth: 180 }}
            >
              {snapshots.map(s => (
                <option key={s.id} value={s.id}>{s.version_tag || `Snapshot ${new Date(s.created_at).toLocaleDateString()}`}</option>
              ))}
            </select>
          )}
          {selectedRecipeId && snapshots.length === 0 && (
            <span style={{ fontSize: 12, color: '#F59E0B', alignSelf: 'center' }}>⚠️ Sin snapshots — se usará Zero-shot</span>
          )}
        </div>
      </div>

      {/* Procesar button — CA-01: ALWAYS ENABLED when files exist */}
      <button
        onClick={handleRun}
        disabled={selectedFiles.length === 0 || processing}
        style={{
          marginTop: '1rem',
          width: '100%',
          padding: '0.75rem',
          background: selectedFiles.length === 0 ? '#d1d5db' : '#6366F1',
          color: '#fff',
          border: 'none',
          borderRadius: 8,
          fontSize: 16,
          fontWeight: 700,
          cursor: selectedFiles.length === 0 ? 'not-allowed' : 'pointer',
        }}
      >
        {processing ? '⏳ Procesando...' : `🚀 Procesar${selectedFiles.length ? ` (${selectedFiles.length} archivo${selectedFiles.length > 1 ? 's' : ''})` : ''}`}
      </button>

      {error && <div style={{ marginTop: '1rem', padding: '0.75rem', background: '#FEF2F2', border: '1px solid #FECACA', borderRadius: 8, color: '#991B1B' }}>{error}</div>}

      {/* Results */}
      {results.length > 0 && (
        <div style={{ marginTop: '1rem' }}>
          <h3>Resultados ({results.length} archivos)</h3>
          {results.map((r, i) => (
            <div key={r.id || i} style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: '0.75rem', marginBottom: '0.5rem', background: '#fff' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <span style={{ fontWeight: 600 }}>{r.tipo_documento_detectado || 'Procesando...'}</span>
                  {' '}{confBadge(r.confianza_clasificacion)}
                  {r.requiere_revision && <span style={{ marginLeft: 8, color: '#F59E0B', fontSize: 13 }}>⚠️ Requiere revisión</span>}
                </div>
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                  <span style={{ fontSize: 12, color: r.estado === 'FAILED' ? '#EF4444' : '#10B981' }}>{r.estado}</span>
                  {r.estado !== 'FAILED' && (
                    <button onClick={() => navigate(`../documents/${r.id}`)} style={{ padding: '4px 12px', border: '1px solid #6366F1', borderRadius: 6, background: '#fff', color: '#6366F1', cursor: 'pointer', fontSize: 13 }}>Revisar →</button>
                  )}
                </div>
              </div>
              {/* CA-03: Show config used */}
              <div style={{ marginTop: '0.5rem', display: 'flex', gap: '0.5rem', fontSize: 12, color: '#6b7280' }}>
                <span style={{ background: '#f3f4f6', padding: '1px 6px', borderRadius: 4 }}>{recipeLabel(r.recipe_used)}</span>
                {r.llm_model && <span style={{ background: '#f3f4f6', padding: '1px 6px', borderRadius: 4 }}>🤖 {r.llm_model}</span>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
