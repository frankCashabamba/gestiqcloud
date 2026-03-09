import React, { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchDashboard, type DashboardStats, fetchRecipes, fetchSnapshots, runImportAsync, streamDocumentStatus, type Recipe, type RecipeSnapshot } from '../services'

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

// Inline uploader con progreso en tiempo real
type ImportMode = 'files' | 'folder'
type FileStatus = 'pending' | 'processing' | 'done' | 'error'
type FileEntry = { file: File; status: FileStatus; docId?: string; result?: { id: string; estado: string; tipo_documento_detectado?: string } }
type DirectoryInputProps = React.InputHTMLAttributes<HTMLInputElement> & { webkitdirectory?: string }
const ACCEPTED = '.pdf,.jpg,.jpeg,.png,.tiff,.bmp,.xlsx,.xls,.csv,.xml,.txt'
const ACCEPTED_EXTENSIONS = new Set(['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.xlsx', '.xls', '.csv', '.xml', '.txt'])

const FILE_ICONS: Record<string, string> = {
  '.pdf': '📄', '.jpg': '🖼️', '.jpeg': '🖼️', '.png': '🖼️',
  '.xlsx': '📊', '.xls': '📊', '.csv': '📋', '.xml': '📝', '.txt': '📃',
}
function fileIcon(name: string) {
  const ext = '.' + name.split('.').pop()?.toLowerCase()
  return FILE_ICONS[ext] || '📄'
}
function fmtSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function Spinner() {
  return (
    <span style={{
      display: 'inline-block', width: 14, height: 14, border: '2px solid #c7d2fe',
      borderTopColor: '#6366F1', borderRadius: '50%',
      animation: 'spin 0.7s linear infinite', flexShrink: 0,
    }} />
  )
}

function InlineUploader({ onImported }: { onImported?: () => void }) {
  const navigate = useNavigate()
  const fileRef = React.useRef<HTMLInputElement>(null)
  const folderRef = React.useRef<HTMLInputElement>(null)
  const [mode, setMode] = useState<ImportMode>('files')
  const [dragging, setDragging] = useState(false)
  const [entries, setEntries] = useState<FileEntry[]>([])
  const [processing, setProcessing] = useState(false)
  const [doneCount, setDoneCount] = useState(0)
  const [error, setError] = useState('')
  const [forceReprocess, setForceReprocess] = useState(false)
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
        if (!existing.has(`${f.name}-${f.size}`)) merged.push({ file: f, status: 'pending' })
      })
      return merged
    })
  }, [])

  const removeEntry = (idx: number) => {
    if (processing) return
    setEntries(prev => prev.filter((_, i) => i !== idx))
  }

  const clearDone = () => setEntries(prev => prev.filter(e => e.status === 'pending'))

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setDragging(false); addFiles(e.dataTransfer.files)
  }, [addFiles])
  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.length) addFiles(e.target.files); e.target.value = ''
  }
  const onFolderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.length) addFiles(e.target.files); e.target.value = ''
  }

  // Encola todos via Celery y hace polling por archivo en paralelo
  const handleRun = async () => {
    const pending = entries.filter(e => e.status === 'pending')
    if (!pending.length) return
    setProcessing(true)
    setError('')
    setDoneCount(0)

    // Marcar todos como "procesando" antes de enviar
    setEntries(prev => prev.map(e => e.status === 'pending' ? { ...e, status: 'processing' } : e))

    try {
      // Enviar todos al backend async (retorna PENDING de inmediato)
      const asyncResults = await runImportAsync(
        pending.map(e => e.file),
        { force: forceReprocess, recipe_snapshot_id: selectedSnapshotId || undefined },
      )

      // Mapear nombre → resultado
      const byName = new Map(asyncResults.map(r => [r.nombre_archivo, r]))

      // Poll cada archivo concurrentemente
      await Promise.all(pending.map(async (entry) => {
        const asyncResult = byName.get(entry.file.name)
        if (!asyncResult) {
          setEntries(prev => prev.map(e => e.file === entry.file ? { ...e, status: 'error' } : e))
          return
        }

        // Si ya estaba procesado (duplicado reutilizado)
        if (asyncResult.estado !== 'PENDING' && asyncResult.estado !== 'PROCESSING') {
          setEntries(prev => prev.map(e =>
            e.file === entry.file
              ? { ...e, status: asyncResult.estado === 'FAILED' ? 'error' : 'done', docId: asyncResult.id, result: asyncResult }
              : e
          ))
          setDoneCount(c => c + 1)
          onImported?.()
          return
        }

        // Polling hasta que el worker lo resuelva
        try {
          const finalDoc = await streamDocumentStatus(asyncResult.id)
          setEntries(prev => prev.map(e =>
            e.file === entry.file
              ? { ...e, status: finalDoc.estado === 'FAILED' ? 'error' : 'done', docId: finalDoc.id, result: finalDoc }
              : e
          ))
          setDoneCount(c => c + 1)
          onImported?.()
        } catch (err: any) {
          setEntries(prev => prev.map(e => e.file === entry.file ? { ...e, status: 'error' } : e))
          setError(prev => prev || (err?.message || `Error procesando "${entry.file.name}"`))
        }
      }))
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Error al encolar archivos')
      setEntries(prev => prev.map(e => e.status === 'processing' ? { ...e, status: 'pending' } : e))
    } finally {
      setProcessing(false)
    }
  }

  const pendingCount = entries.filter(e => e.status === 'pending').length
  const totalCount = entries.length
  const errorCount = entries.filter(e => e.status === 'error').length
  const completedCount = entries.filter(e => e.status === 'done').length
  const progressPct = totalCount > 0 ? Math.round(((completedCount + errorCount) / totalCount) * 100) : 0

  return (
    <>
      {/* Estilos para spinner */}
      <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
      <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 12, padding: '1rem' }}>

        {/* Toggle modo */}
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
          {(['files', 'folder'] as ImportMode[]).map(m => (
            <button key={m} onClick={() => setMode(m)} disabled={processing} style={{
              padding: '0.4rem 1rem', borderRadius: 6, border: '1px solid #d1d5db', cursor: processing ? 'default' : 'pointer', fontSize: 13,
              background: mode === m ? '#6366F1' : '#fff', color: mode === m ? '#fff' : '#374151', fontWeight: mode === m ? 600 : 400,
            }}>
              {m === 'files' ? 'Archivos individuales' : 'Seleccionar carpeta'}
            </button>
          ))}
        </div>

        {/* Drop zone */}
        {mode === 'files' && (
          <div
            onDragOver={e => { e.preventDefault(); if (!processing) setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            onClick={() => !processing && fileRef.current?.click()}
            style={{
              border: `2px dashed ${dragging ? '#6366F1' : '#d1d5db'}`, borderRadius: 12, padding: '1.5rem',
              textAlign: 'center', cursor: processing ? 'default' : 'pointer', background: dragging ? '#EEF2FF' : '#f9fafb', transition: 'all 0.2s',
            }}
          >
            <div style={{ fontSize: 36, marginBottom: '0.4rem' }}>📎</div>
            <p style={{ fontSize: 14, fontWeight: 600, margin: '0 0 2px' }}>Arrastra archivos o haz clic para seleccionar</p>
            <p style={{ fontSize: 12, color: '#6b7280', margin: 0 }}>PDF, JPG/PNG, Excel, CSV, XML, TXT</p>
            <input ref={fileRef} type="file" multiple accept={ACCEPTED} onChange={onFileChange} style={{ display: 'none' }} />
          </div>
        )}

        {mode === 'folder' && (
          <div
            onClick={() => !processing && folderRef.current?.click()}
            style={{ border: '2px dashed #d1d5db', borderRadius: 12, padding: '1.5rem', textAlign: 'center', cursor: processing ? 'default' : 'pointer', background: '#f9fafb' }}
          >
            <div style={{ fontSize: 36, marginBottom: '0.4rem' }}>🗂️</div>
            <p style={{ fontSize: 14, fontWeight: 600, margin: '0 0 2px' }}>Seleccionar carpeta</p>
            <p style={{ fontSize: 12, color: '#6b7280', margin: 0 }}>Procesa todos los archivos soportados dentro</p>
            <input ref={folderRef} type="file" multiple onChange={onFolderChange} style={{ display: 'none' }} {...directoryInputProps} />
          </div>
        )}

        {/* Lista de archivos */}
        {entries.length > 0 && (
          <div style={{ marginTop: '0.75rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: '#374151' }}>
                {processing
                  ? `Procesando ${completedCount + errorCount} de ${pendingCount + completedCount + errorCount}...`
                  : `${entries.length} archivo${entries.length > 1 ? 's' : ''} seleccionado${entries.length > 1 ? 's' : ''}`}
              </span>
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                {completedCount > 0 && <span style={{ fontSize: 11, color: '#10B981', fontWeight: 600 }}>✓ {completedCount} listo{completedCount > 1 ? 's' : ''}</span>}
                {errorCount > 0 && <span style={{ fontSize: 11, color: '#EF4444', fontWeight: 600 }}>✗ {errorCount} error{errorCount > 1 ? 'es' : ''}</span>}
                {!processing && completedCount > 0 && (
                  <button onClick={clearDone} style={{ fontSize: 11, color: '#6b7280', border: 'none', background: 'none', cursor: 'pointer', padding: 0 }}>
                    Limpiar completados
                  </button>
                )}
              </div>
            </div>

            {/* Barra de progreso */}
            {processing && (
              <div style={{ height: 4, background: '#e5e7eb', borderRadius: 4, marginBottom: '0.5rem', overflow: 'hidden' }}>
                <div style={{
                  height: '100%', background: '#6366F1', borderRadius: 4,
                  width: `${progressPct}%`, transition: 'width 0.3s ease',
                }} />
              </div>
            )}

            <div style={{ maxHeight: 200, overflowY: 'auto', border: '1px solid #e5e7eb', borderRadius: 8 }}>
              {entries.map((entry, i) => (
                <div key={i} style={{
                  display: 'flex', alignItems: 'center', gap: '0.5rem',
                  padding: '0.45rem 0.75rem',
                  background: entry.status === 'done' ? '#F0FDF4' : entry.status === 'error' ? '#FEF2F2' : entry.status === 'processing' ? '#EEF2FF' : '#fff',
                  borderBottom: i < entries.length - 1 ? '1px solid #f3f4f6' : 'none',
                  fontSize: 13, transition: 'background 0.2s',
                }}>
                  {/* Ícono de estado */}
                  <span style={{ flexShrink: 0, width: 18, display: 'flex', justifyContent: 'center' }}>
                    {entry.status === 'processing' ? <Spinner /> :
                     entry.status === 'done' ? <span style={{ color: '#10B981', fontWeight: 700 }}>✓</span> :
                     entry.status === 'error' ? <span style={{ color: '#EF4444', fontWeight: 700 }}>✗</span> :
                     <span style={{ fontSize: 15 }}>{fileIcon(entry.file.name)}</span>}
                  </span>

                  {/* Nombre y tamaño */}
                  <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: entry.status === 'error' ? '#991B1B' : '#374151' }}>
                    {entry.file.name}
                  </span>
                  <span style={{ color: '#9ca3af', fontSize: 11, flexShrink: 0 }}>{fmtSize(entry.file.size)}</span>

                  {/* Tipo detectado */}
                  {entry.result?.tipo_documento_detectado && (
                    <span style={{ background: '#e0e7ff', color: '#3730a3', padding: '1px 7px', borderRadius: 10, fontSize: 11, flexShrink: 0 }}>
                      {entry.result.tipo_documento_detectado}
                    </span>
                  )}

                  {/* Botón revisar */}
                  {entry.status === 'done' && (entry.docId || entry.result?.id) && (
                    <button
                      onClick={() => navigate(`documents/${entry.docId || entry.result!.id}`)}
                      style={{ padding: '2px 8px', border: '1px solid #6366F1', borderRadius: 5, background: '#fff', color: '#6366F1', cursor: 'pointer', fontSize: 11, flexShrink: 0 }}
                    >
                      Ver
                    </button>
                  )}

                  {/* Botón eliminar (solo pendientes, sin procesar) */}
                  {entry.status === 'pending' && !processing && (
                    <button onClick={() => removeEntry(i)} style={{ border: 'none', background: 'none', color: '#9ca3af', cursor: 'pointer', fontSize: 16, padding: 0, lineHeight: 1, flexShrink: 0 }}>×</button>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Plantilla / Receta */}
        <div style={{ marginTop: '0.75rem', display: 'flex', gap: '0.5rem', alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div>
            <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 3 }}>Plantilla / Receta <span style={{ color: '#d1d5db' }}>opcional</span></div>
            <select
              value={selectedRecipeId}
              onChange={e => setSelectedRecipeId(e.target.value)}
              disabled={processing}
              style={{ padding: '0.35rem 0.5rem', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 13, minWidth: 190 }}
            >
              <option value="">Auto-detectar (recomendado)</option>
              {recipes.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
            </select>
          </div>
          {selectedRecipeId && snapshots.length > 0 && (
            <select
              value={selectedSnapshotId}
              onChange={e => setSelectedSnapshotId(e.target.value)}
              disabled={processing}
              style={{ padding: '0.35rem 0.5rem', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 13, minWidth: 170 }}
            >
              {snapshots.map(s => (
                <option key={s.id} value={s.id}>{s.version_tag || `v${new Date(s.created_at).toLocaleDateString()}`}</option>
              ))}
            </select>
          )}
        </div>

        <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.6rem', fontSize: 12, color: '#6b7280', cursor: processing ? 'default' : 'pointer', userSelect: 'none' }}>
          <input type="checkbox" checked={forceReprocess} disabled={processing} onChange={e => setForceReprocess(e.target.checked)} style={{ cursor: 'pointer' }} />
          Reimportacion limpia
          <span style={{ color: '#d1d5db' }}>(omite dedupe)</span>
        </label>

        {/* Botón principal */}
        <button
          onClick={handleRun}
          disabled={pendingCount === 0 || processing}
          style={{
            marginTop: '0.75rem', width: '100%', padding: '0.7rem',
            background: pendingCount === 0 || processing ? '#e5e7eb' : '#6366F1',
            color: pendingCount === 0 || processing ? '#9ca3af' : '#fff',
            border: 'none', borderRadius: 8, fontSize: 15, fontWeight: 700,
            cursor: pendingCount === 0 || processing ? 'not-allowed' : 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem',
            transition: 'background 0.2s',
          }}
        >
          {processing ? (
            <>
              <Spinner />
              Procesando {completedCount + errorCount} / {pendingCount + completedCount + errorCount}...
            </>
          ) : pendingCount > 0
            ? `Importar ${pendingCount} documento${pendingCount > 1 ? 's' : ''}`
            : entries.length > 0
              ? `✓ Todo procesado — agrega más archivos`
              : 'Importar documentos'}
        </button>

        {error && (
          <div style={{ marginTop: '0.5rem', padding: '0.6rem 0.75rem', background: '#FEF2F2', border: '1px solid #FECACA', borderRadius: 8, color: '#991B1B', fontSize: 13 }}>
            {error}
          </div>
        )}
      </div>
    </>
  )
}
