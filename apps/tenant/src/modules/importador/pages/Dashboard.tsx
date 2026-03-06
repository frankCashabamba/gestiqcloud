import React, { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchDashboard, type DashboardStats, fetchRecipes, fetchSnapshots, runImport, type Recipe, type RecipeSnapshot, type RunResult } from '../services'

export default function Dashboard() {
  const navigate = useNavigate()
  const [stats, setStats] = useState<DashboardStats>({ total: 0, pendientes: 0, en_revision: 0, confirmados: 0, fallidos: 0 })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchDashboard().then(setStats).catch(() => {}).finally(() => setLoading(false))
  }, [])

  return (
    <div style={{ padding: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h2>📥 Importador Contable Universal</h2>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button onClick={() => navigate('documents')} style={btn}>📋 Ver Todos</button>
          <button onClick={() => navigate('recipes')} style={btn}>📋 Recetas</button>
        </div>
      </div>
      <p style={{ color: '#6b7280', marginBottom: '1.5rem' }}>Sube facturas, recibos, boletas en PDF, imagen, Excel, CSV, XML o TXT. El sistema clasifica y extrae datos automáticamente.</p>
      {loading ? <p>Cargando...</p> : (
        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
          <StatCard label="Total Documentos" value={stats.total} color="#374151" />
          <StatCard label="Pendientes" value={stats.pendientes} color="#F59E0B" />
          <StatCard label="En Revisión" value={stats.en_revision} color="#3B82F6" onClick={() => navigate('documents?estado=REVIEW')} />
          <StatCard label="Confirmados" value={stats.confirmados} color="#10B981" />
          <StatCard label="Fallidos" value={stats.fallidos} color="#EF4444" />
        </div>
      )}
      <div style={{ marginTop: '2rem' }}>
        <InlineUploader onImported={() => fetchDashboard().then(setStats).catch(() => {})} />
      </div>
    </div>
  )
}

function StatCard({ label, value, color, onClick }: { label: string; value: number; color: string; onClick?: () => void }) {
  return (
    <div onClick={onClick} style={{ border: '1px solid #e5e7eb', borderRadius: 12, padding: '1.25rem', background: '#fff', minWidth: 160, flex: 1, cursor: onClick ? 'pointer' : 'default', borderLeft: `4px solid ${color}` }}>
      <div style={{ fontSize: 28, fontWeight: 700, color }}>{value}</div>
      <div style={{ fontSize: 13, color: '#6b7280', marginTop: 4 }}>{label}</div>
    </div>
  )
}

const btn: React.CSSProperties = { padding: '0.5rem 1rem', border: '1px solid #d1d5db', borderRadius: 6, cursor: 'pointer', background: '#fff', fontSize: 14 }

// Inline uploader (reutiliza lógica principal de UploadPage, simplificada)
type ImportMode = 'files' | 'folder'
type FileEntry = { file: File; status: 'pending' | 'done' | 'error'; result?: RunResult }
type DirectoryInputProps = React.InputHTMLAttributes<HTMLInputElement> & { webkitdirectory?: string }
const ACCEPTED = '.pdf,.jpg,.jpeg,.png,.tiff,.bmp,.xlsx,.xls,.csv,.xml,.txt'
const ACCEPTED_EXTENSIONS = new Set(['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.xlsx', '.xls', '.csv', '.xml', '.txt'])

function InlineUploader({ onImported }: { onImported?: () => void }) {
  const navigate = useNavigate()
  const fileRef = React.useRef<HTMLInputElement>(null)
  const folderRef = React.useRef<HTMLInputElement>(null)
  const [mode, setMode] = useState<ImportMode>('files')
  const [dragging, setDragging] = useState(false)
  const [entries, setEntries] = useState<FileEntry[]>([])
  const [processing, setProcessing] = useState(false)
  const [error, setError] = useState('')
  const [results, setResults] = useState<RunResult[]>([])
  const [forceReprocess, setForceReprocess] = useState(false)

  // recipes
  const [recipes, setRecipes] = useState<Recipe[]>([])
  const [snapshots, setSnapshots] = useState<RecipeSnapshot[]>([])
  const [selectedRecipeId, setSelectedRecipeId] = useState('')
  const [selectedSnapshotId, setSelectedSnapshotId] = useState('')
  const directoryInputProps: DirectoryInputProps = { webkitdirectory: 'true' }

  useEffect(() => { fetchRecipes().then(setRecipes).catch(() => {}) }, [])
  useEffect(() => {
    if (!selectedRecipeId) { setSnapshots([]); setSelectedSnapshotId(''); return }
    fetchSnapshots(selectedRecipeId).then(snaps => {
      setSnapshots(snaps); setSelectedSnapshotId(snaps[0]?.id || '')
    }).catch(() => setSnapshots([]))
  }, [selectedRecipeId])

  const addFiles = useCallback((fileList: FileList | File[]) => {
    const incoming = Array.from(fileList || []).filter(f => {
      if (!f || f.size < 0) return false
      const ext = '.' + f.name.split('.').pop()?.toLowerCase()
      return ACCEPTED_EXTENSIONS.has(ext)
    })
    if (!incoming.length) return
    setEntries(prev => {
      const existing = new Set(prev.map(e => `${e.file.name}-${e.file.size}`))
      const merged = [...prev]
      incoming.forEach(f => {
        const key = `${f.name}-${f.size}`
        if (!existing.has(key)) merged.push({ file: f, status: 'pending' })
      })
      return merged
    })
  }, [])

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setDragging(false); addFiles(e.dataTransfer.files)
  }, [addFiles])

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.length) addFiles(e.target.files); e.target.value = ''
  }
  const onFolderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.length) addFiles(e.target.files); e.target.value = ''
  }

  const handleRun = async () => {
    const pending = entries.filter(e => e.status === 'pending')
    if (!pending.length) return
    setProcessing(true); setError(''); setResults([])
    const opts = {
      ...(selectedSnapshotId ? { recipe_snapshot_id: selectedSnapshotId } : {}),
      force: forceReprocess,
    }
    try {
      const res = await runImport(pending.map(e => e.file), opts)
      setEntries(prev => prev.map((e, idx) => {
        const match = pending.find(p => p.file === e.file)
        if (!match) return e
        const rr = res[pending.indexOf(match)]
        return { ...e, status: rr?.estado === 'FAILED' ? 'error' : 'done', result: rr }
      }))
      setResults(res)
      onImported?.()
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Error al procesar')
      setEntries(prev => prev.map(e => e.status === 'pending' ? { ...e, status: 'error' } : e))
    } finally {
      setProcessing(false)
    }
  }

  const pendingCount = entries.filter(e => e.status === 'pending').length

  return (
    <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 12, padding: '1rem' }}>
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
        {(['files', 'folder'] as ImportMode[]).map(m => (
          <button key={m} onClick={() => setMode(m)} style={{
            padding: '0.4rem 1rem', borderRadius: 6, border: '1px solid #d1d5db', cursor: 'pointer', fontSize: 13,
            background: mode === m ? '#6366F1' : '#fff', color: mode === m ? '#fff' : '#374151', fontWeight: mode === m ? 600 : 400,
          }}>
            {m === 'files' ? 'Archivos individuales' : 'Seleccionar carpeta'}
          </button>
        ))}
      </div>

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

      {mode === 'folder' && (
        <div
          onClick={() => folderRef.current?.click()}
          style={{
            border: '2px dashed #d1d5db', borderRadius: 12, padding: '2rem', textAlign: 'center',
            cursor: 'pointer', background: '#f9fafb', transition: 'all 0.2s',
          }}
        >
          <div style={{ fontSize: 40, marginBottom: '0.5rem' }}>🗂️</div>
          <p style={{ fontSize: 15, fontWeight: 600, margin: '0 0 4px' }}>Seleccionar carpeta</p>
          <p style={{ fontSize: 13, color: '#6b7280', margin: 0 }}>Procesa todos los archivos soportados dentro</p>
          <input ref={folderRef} type="file" multiple onChange={onFolderChange} style={{ display: 'none' }} {...directoryInputProps} />
        </div>
      )}

      {/* Plantilla */}
      <div style={{ marginTop: '1rem', display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
        <div>
          <div style={{ fontSize: 13, color: '#374151', marginBottom: 4 }}>Plantilla / Receta <span style={{ color: '#9CA3AF' }}>opcional</span></div>
          <select
            value={selectedRecipeId}
            onChange={e => setSelectedRecipeId(e.target.value)}
            style={{ padding: '0.4rem 0.5rem', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 13, minWidth: 200 }}
          >
            <option value="">Auto-detectar (recomendado)</option>
            {recipes.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
          </select>
        </div>
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
      </div>

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
            (omite dedupe y sirve para volver a procesar un archivo que ya habias importado hace tiempo)
          </span>
        </span>
      </label>

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
          ? 'Procesando...'
          : pendingCount > 0 ? `Importar ${pendingCount} documento${pendingCount > 1 ? 's' : ''}` : 'Importar documentos'}
      </button>

      {results.length > 0 && (
        <div style={{ marginTop: '1rem' }}>
          <h4 style={{ marginBottom: 8 }}>Resultados del lote</h4>
          {results.map((r, i) => (
            <div key={r.id || i} style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: '0.6rem', marginBottom: 6, background: r.estado === 'FAILED' ? '#FEF2F2' : '#F8FAFF' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap' }}>
                <div style={{ fontWeight: 600 }}>{r.tipo_documento_detectado || '—'}</div>
                <div style={{ fontSize: 12, color: r.estado === 'FAILED' ? '#EF4444' : '#10B981', fontWeight: 600 }}>{r.estado}</div>
              </div>
              {r.confianza_clasificacion != null && (
                <div style={{ fontSize: 12, color: '#6b7280' }}>Confianza: {Math.round((r.confianza_clasificacion || 0) * 100)}%</div>
              )}
              {r.recipe_used && <div style={{ fontSize: 12, color: '#6b7280' }}>Modo receta: {r.recipe_used}</div>}
              {r.auto_recipe_created && r.auto_recipe_name && (
                <div style={{ fontSize: 12, color: '#166534' }}>Plantilla auto: {r.auto_recipe_name}</div>
              )}
              {r.estado !== 'FAILED' && r.id && (
                <div style={{ marginTop: 8 }}>
                  <button
                    onClick={() => navigate(`documents/${r.id}`)}
                    style={{ padding: '4px 10px', borderRadius: 6, border: '1px solid #6366F1', background: '#fff', color: '#6366F1', cursor: 'pointer', fontSize: 12 }}
                  >
                    Revisar
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {error && (
        <div style={{ marginTop: '0.75rem', padding: '0.75rem', background: '#FEF2F2', border: '1px solid #FECACA', borderRadius: 8, color: '#991B1B', fontSize: 14 }}>
          {error}
        </div>
      )}
    </div>
  )
}
