import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { fetchDocument, confirmDocument, editDocumentFields, rejectDocument, syncAllRecipes, syncRecipe, type Documento, type LogCambio, type SyncRecipeResult, type SyncRecipesResult } from '../services'

export default function DocumentDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [doc, setDoc] = useState<Documento | null>(null)
  const [loading, setLoading] = useState(true)
  const [editMode, setEditMode] = useState(false)
  const [editFields, setEditFields] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [syncingAll, setSyncingAll] = useState(false)
  const [error, setError] = useState('')
  const [rawSyncResult, setSyncResult] = useState<SyncRecipeResult | null>(null)
  const [batchSyncResult, setBatchSyncResult] = useState<SyncRecipesResult | null>(null)
  const syncResult = rawSyncResult
    ? {
        ...rawSyncResult,
        total_cost: Number(rawSyncResult.total_cost ?? 0),
        ingredients_count: Number(rawSyncResult.ingredients_count ?? 0),
      }
    : null
  const [activeSheet, setActiveSheet] = useState<string | null>(null)

  const load = async () => {
    if (!id) return
    setLoading(true)
    try { setDoc(await fetchDocument(id)) } catch { setError('Error cargando') }
    setLoading(false)
  }

  useEffect(() => { load() }, [id])

  useEffect(() => {
    const reloadOnFocus = () => { void load() }
    const reloadOnVisibility = () => {
      if (!document.hidden) void load()
    }
    window.addEventListener('focus', reloadOnFocus)
    document.addEventListener('visibilitychange', reloadOnVisibility)
    return () => {
      window.removeEventListener('focus', reloadOnFocus)
      document.removeEventListener('visibilitychange', reloadOnVisibility)
    }
  }, [id])

  // Selección automática de hoja cuando llega un documento nuevo
  useEffect(() => {
    const datos = (doc?.datos_extraidos || {}) as Record<string, unknown>
    const sheetMap = datos?.filas_por_hoja && typeof datos.filas_por_hoja === 'object'
      ? Object.keys(datos.filas_por_hoja as Record<string, unknown>)
      : []
    if (sheetMap.length > 0) {
      const preferred = (datos.sheet_usada as string) || sheetMap[0]
      setActiveSheet(preferred)
    } else {
      setActiveSheet(null)
    }
  }, [doc?.id])

  const handleConfirm = async () => {
    if (!id || !doc) return
    setSaving(true)
    try {
      await confirmDocument(id, doc.datos_extraidos || {})
      load()
    } catch { setError('Error confirmando') }
    setSaving(false)
  }

  const handleSyncSheet = async () => {
    if (!id) return
    if (activeSheetIsSynced) {
      setError(`La hoja ${activeSheet || ''} ya fue sincronizada.`.trim())
      return
    }
    setSyncing(true)
    setError('')
    setSyncResult(null)
    setBatchSyncResult(null)
    try {
      const result = await syncRecipe(id, activeSheet || undefined)
      setSyncResult({
        ...result,
        total_cost: Number(result.total_cost ?? 0),
        ingredients_count: Number(result.ingredients_count ?? 0),
      })
      load()
    } catch (e: any) {
      const msg = e?.response?.data?.detail || 'Error sincronizando receta'
      setError(msg)
    }
    setSyncing(false)
  }

  const handleSyncAll = async () => {
    if (!id || !hasMultiSheetDocument || unsyncedSheets.length === 0) return
    setSyncingAll(true)
    setError('')
    setSyncResult(null)
    setBatchSyncResult(null)
    try {
      const result = await syncAllRecipes(id)
      setBatchSyncResult(result)
      load()
    } catch (e: any) {
      const msg = e?.response?.data?.detail || 'Error sincronizando hojas'
      setError(msg)
    }
    setSyncingAll(false)
  }

  const handleReject = async () => {
    if (!id || !confirm('¿Rechazar este documento?')) return
    try { await rejectDocument(id); load() } catch { setError('Error rechazando') }
  }

  const startEdit = () => {
    const data = (doc?.datos_extraidos || {}) as Record<string, unknown>
    // No editar tablas (tipo inventario/nomina) — solo campos escalares
    if (data.filas && Array.isArray(data.filas)) return
    const flat: Record<string, string> = {}
    Object.entries(data).forEach(([k, v]) => {
      if (!k.startsWith('_') && (typeof v !== 'object' || v === null)) flat[k] = String(v ?? '')
    })
    setEditFields(flat)
    setEditMode(true)
  }

  const saveEdit = async () => {
    if (!id) return
    setSaving(true)
    try {
      await editDocumentFields(id, editFields)
      setEditMode(false)
      load()
    } catch { setError('Error guardando') }
    setSaving(false)
  }

  if (loading) return <div style={{ padding: '1.5rem' }}>Cargando...</div>
  if (!doc) return <div style={{ padding: '1.5rem' }}>Documento no encontrado</div>

  const datos = (doc.datos_extraidos || {}) as Record<string, unknown>
  const filasPorHoja = (datos.filas_por_hoja || {}) as Record<string, Record<string, unknown>[]>
  const sheets = Object.keys(filasPorHoja || {})
  const sheetCounts = (datos.filas_por_hoja_count || {}) as Record<string, number>
  const confPct = doc.confianza_clasificacion != null ? Math.round(doc.confianza_clasificacion * 100) : null
  const syncedSheets = Object.entries(doc.synced_sheets || {}).reduce<Record<string, { recipeId?: string; recipeName?: string; createdAt?: string }>>((acc, [sheetName, value]) => {
    const recipeId = typeof value?.recipe_id === 'string' ? value.recipe_id.trim() : ''
    if (!sheetName || !recipeId) return acc
    acc[sheetName] = {
      recipeId,
      recipeName: typeof value?.recipe_name === 'string' ? value.recipe_name : undefined,
      createdAt: typeof value?.created_at === 'string' ? value.created_at : undefined,
    }
    return acc
  }, {})
  const syncedSheetNames = Object.keys(syncedSheets)
  const syncedCount = syncedSheetNames.length
  const activeSheetSync = activeSheet ? syncedSheets[activeSheet] : undefined
  const activeSheetIsSynced = Boolean(activeSheet && activeSheetSync?.recipeId)
  const hasMultiSheetDocument = sheets.length > 0
  const unsyncedSheets = sheets.filter(sheet => !syncedSheets[sheet]?.recipeId)
  const syncedRecipeId = activeSheetSync?.recipeId || doc.synced_recipe_id
  const isSynced = syncedCount > 0

  return (
    <div style={{ padding: '1.5rem' }}>
      <div style={{ position: 'sticky', top: 0, zIndex: 5, background: '#f9fafb', paddingBottom: '0.75rem' }}>
        <button
          onClick={() => navigate(-1)}
          style={{
            cursor: 'pointer',
            border: '1px solid #e5e7eb',
            background: '#fff',
            fontSize: 14,
            color: '#111827',
            padding: '0.45rem 0.75rem',
            borderRadius: 10,
            boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
          }}
        >
          ← Volver
        </button>
      </div>
      {error && <div style={{ color: 'red', marginBottom: '0.5rem' }}>{error}</div>}

      {syncResult && (
        <div style={{ padding: '0.75rem', background: syncResult.was_new ? '#F0FDF4' : '#EFF6FF', border: '1px solid ' + (syncResult.was_new ? '#BBF7D0' : '#BFDBFE'), borderRadius: 8, marginBottom: '0.75rem', fontSize: 14, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>
            {syncResult.was_new ? '✅ Receta creada' : '🔄 Receta actualizada'}: <strong>{syncResult.recipe_name}</strong>
            {' · '}{syncResult.ingredients_count} ingredientes · Costo total: <strong>${syncResult.total_cost.toFixed(4)}</strong>
          </span>
          <button onClick={() => setSyncResult(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 16, color: '#6b7280' }}>×</button>
        </div>
      )}

      {batchSyncResult && (
        <div style={{ padding: '0.75rem', background: '#EFF6FF', border: '1px solid #BFDBFE', borderRadius: 8, marginBottom: '0.75rem', fontSize: 14 }}>
          <div style={{ fontWeight: 600, color: '#1d4ed8', marginBottom: 6 }}>
            Lote sincronizado: {batchSyncResult.processed_count} creadas/actualizadas, {batchSyncResult.skipped_count} omitidas
          </div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {batchSyncResult.results.map(result => (
              <span
                key={result.sheet_name}
                style={{
                  padding: '4px 8px',
                  borderRadius: 999,
                  fontSize: 12,
                  background: result.status === 'skipped' ? '#E5E7EB' : result.status === 'error' ? '#FEE2E2' : '#DBEAFE',
                  color: result.status === 'error' ? '#B91C1C' : '#1F2937',
                }}
              >
                {result.sheet_name}: {result.status === 'skipped' ? 'sincronizada' : result.status === 'error' ? 'error' : 'ok'}
              </span>
            ))}
          </div>
        </div>
      )}

      {isSynced && !syncResult && !batchSyncResult && (
        <div style={{ padding: '0.6rem 0.9rem', background: '#EFF6FF', border: '1px solid #BFDBFE', borderRadius: 8, marginBottom: '0.75rem', fontSize: 13, color: '#1e40af' }}>
          {syncedCount > 1 ? `${syncedCount} hojas sincronizadas con produccion.` : 'Receta ya sincronizada con produccion.'}
          {syncedRecipeId ? ` ID: ${syncedRecipeId.substring(0, 8)}...` : ''}
        </div>
      )}

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
        <div>
          <h2 style={{ marginBottom: 4 }}>📄 {doc.nombre_archivo}</h2>
          <div style={{ display: 'flex', gap: '0.75rem', fontSize: 13, color: '#6b7280' }}>
            <span>{doc.tipo_archivo}</span>
            <span>{Math.round(Number(doc.tamanio_bytes ?? 0) / 1024)} KB</span>
            <span>{new Date(doc.created_at).toLocaleString()}</span>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          {doc.estado === 'REVIEW' && (
            <>
              {!((doc.datos_extraidos as any)?.filas) && (
                <button onClick={startEdit} style={{ ...actionBtn, background: '#F59E0B' }}>Editar</button>
              )}
              <button onClick={handleReject} style={{ ...actionBtn, background: '#EF4444' }}>Rechazar</button>
              <button onClick={handleConfirm} disabled={saving} style={{ ...actionBtn, background: '#10B981' }}>{saving ? '...' : 'Confirmar'}</button>
            </>
          )}
          {isSynced && syncedRecipeId && (
            <a
              href={`../../produccion/recetas`}
              style={{ ...actionBtn, background: '#059669', textDecoration: 'none', display: 'inline-flex', alignItems: 'center' }}
              title="Ver receta en módulo de Producción"
            >
              Ver receta
            </a>
          )}
          {hasMultiSheetDocument && (
            <button
              onClick={handleSyncAll}
              disabled={syncingAll || syncing || unsyncedSheets.length === 0}
              style={{ ...actionBtn, background: unsyncedSheets.length === 0 ? '#94a3b8' : '#0f766e' }}
              title="Crea recetas para todas las hojas pendientes"
            >
              {syncingAll ? '...' : unsyncedSheets.length === 0 ? 'Todo sincronizado' : `Guardar ${unsyncedSheets.length} hojas`}
            </button>
          )}
          <button
            onClick={handleSyncSheet}
            disabled={syncingAll || syncing || activeSheetIsSynced}
            style={{ ...actionBtn, background: activeSheetIsSynced ? '#94a3b8' : '#2563eb' }}
            title="Sincroniza con Producción (recetas) usando la hoja activa"
          >
            {syncing ? '...' : activeSheetIsSynced ? 'Sincronizado' : 'Guardar hoja'}
          </button>
          <button
            onClick={() => navigate('../upload')}
            title="Ir a importación → marcar 'Reimportar aunque ya exista' → subir el archivo de nuevo"
            style={{ ...actionBtn, background: '#6366F1', opacity: 0.85 }}
          >
            Reimportar
          </button>
        </div>
      </div>

      {/* Confidence warning */}
      {doc.requiere_revision && confPct != null && confPct < 85 && (
        <div style={{ padding: '0.75rem', background: '#FFFBEB', border: '1px solid #FDE68A', borderRadius: 8, marginBottom: '1rem', fontSize: 14 }}>
          ⚠️ <strong>Revisión obligatoria</strong> — Confianza de clasificación: <strong style={{ color: confPct < 50 ? '#EF4444' : '#F59E0B' }}>{confPct}%</strong>. Verifique los datos extraídos antes de confirmar.
        </div>
      )}

      {/* Status badge */}
      <div style={{ marginBottom: '1rem' }}>
        <span style={{ ...statusBadge, background: statusColor[doc.estado] || '#9CA3AF' }}>{doc.estado}</span>
        {doc.tipo_documento_detectado && <span style={{ marginLeft: 8, background: '#e0e7ff', padding: '3px 10px', borderRadius: 6, fontSize: 13 }}>{doc.tipo_documento_detectado}</span>}
        {confPct != null && <span style={{ marginLeft: 8, fontSize: 13, color: confPct >= 85 ? '#10B981' : '#F59E0B' }}>Confianza: {confPct}%</span>}
      </div>

      {/* Split view */}
      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
        {/* Left: Document info */}
        <div style={{ flex: 1, minWidth: 300 }}>
          <div style={section}>
            <h3 style={{ marginTop: 0 }}>📊 Datos Detectados</h3>
            {doc.proveedor_detectado && <p><strong>Proveedor:</strong> {doc.proveedor_detectado}</p>}
            {doc.ruc_detectado && <p><strong>RUC:</strong> {doc.ruc_detectado}</p>}
            {doc.monto_total != null && <p><strong>Monto:</strong> {doc.moneda || '$'} {doc.monto_total.toFixed(2)}</p>}
            {doc.fecha_documento && <p><strong>Fecha:</strong> {doc.fecha_documento}</p>}
          </div>
          {doc.error_detalle && (
            <div style={{ ...section, background: '#FEF2F2', border: '1px solid #FECACA' }}>
              <h3 style={{ marginTop: 0, color: '#991B1B' }}>❌ Error</h3>
              <pre style={{ whiteSpace: 'pre-wrap', fontSize: 13 }}>{doc.error_detalle}</pre>
            </div>
          )}
        </div>

        {/* Right: Extracted fields / Table rows */}
        <div style={{ flex: 1, minWidth: 300 }}>
          <div style={section}>
            {datos.filas && Array.isArray(datos.filas) ? (
              // Vista de tabla para INVENTARIO, NOMINA, COSTEO, etc.
              (() => {
                const pickRows = () => {
                  if (activeSheet && filasPorHoja[activeSheet]) return filasPorHoja[activeSheet]
                  return datos.filas as Record<string, unknown>[]
                }
                const allRows = pickRows()

                // columnas_norm = claves reales de los dicts de filas (ej: "precio_unitario_venta")
                // columnas      = nombres display para la UI (ej: "PRECIO UNITARIO VENTA")
                const normKeys: string[] = (() => {
                  if (activeSheet && activeSheet === (datos.sheet_usada as string) && Array.isArray(datos.columnas_norm) && (datos.columnas_norm as string[]).length > 0) {
                    return datos.columnas_norm as string[]
                  }
                  return allRows.length > 0 ? Object.keys(allRows[0]).filter(k => k !== '_sheet') : []
                })()
                const displayNames: string[] = (() => {
                  if (activeSheet && activeSheet === (datos.sheet_usada as string) && Array.isArray(datos.columnas)) return datos.columnas as string[]
                  return normKeys
                })()
                // Filtrar columnas que no tienen ningún dato real en las primeras 30 filas
                const visibleIdxs = normKeys.reduce<number[]>((acc, key, i) => {
                  const vals = allRows.slice(0, 30).map(r => r[key])
                  if (vals.some(v => v !== null && v !== undefined && v !== '' && v !== 0)) acc.push(i)
                  return acc
                }, [])
                const totalFilasSheet = activeSheet && sheetCounts[activeSheet] ? sheetCounts[activeSheet] : (datos.total_filas as number)
                return (
                  <>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.6rem', flexWrap: 'wrap', gap: '0.4rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                        <h3 style={{ margin: 0 }}>Filas del documento</h3>
                        {sheets.length > 0 && (
                          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                            {sheets.map(s => {
                              const isSheetSynced = Boolean(syncedSheets[s]?.recipeId)
                              return (
                                <button
                                  key={s}
                                  onClick={() => setActiveSheet(s)}
                                  style={{
                                    padding: '6px 10px',
                                    borderRadius: 10,
                                    border: '1px solid ' + (activeSheet === s ? '#0ea5e9' : isSheetSynced ? '#10b981' : '#e5e7eb'),
                                    background: activeSheet === s ? '#e0f2fe' : isSheetSynced ? '#ecfdf5' : '#fff',
                                    color: '#0f172a',
                                    fontSize: 12,
                                    cursor: 'pointer',
                                  }}
                                >
                                  {s} <span style={{ color: '#64748b' }}>({sheetCounts[s] ?? '-'})</span>
                                  {isSheetSynced && <span style={{ marginLeft: 6, color: '#047857', fontWeight: 600 }}>Sync</span>}
                                </button>
                              )
                            })}
                          </div>
                        )}
                      </div>
                      <span style={{ fontSize: 12, color: '#6b7280' }}>{totalFilasSheet} filas · {visibleIdxs.length} columnas</span>
                    </div>
                    <div style={{ overflowX: 'auto', maxHeight: 460, overflowY: 'auto', border: '1px solid #e5e7eb', borderRadius: 10 }}>
                      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                        <thead>
                          <tr style={{ background: '#f9fafb', borderBottom: '2px solid #e5e7eb', position: 'sticky', top: 0 }}>
                            {visibleIdxs.map(i => (
                              <th key={i} style={{ padding: '0.4rem 0.5rem', textAlign: 'left', fontWeight: 600, color: '#374151', whiteSpace: 'nowrap', background: '#f9fafb' }}>
                                {displayNames[i] ?? normKeys[i]}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {allRows.slice(0, 150).map((row, ri) => (
                            <tr key={ri} style={{ borderBottom: '1px solid #f3f4f6' }}
                              onMouseEnter={e => (e.currentTarget.style.background = '#f9fafb')}
                              onMouseLeave={e => (e.currentTarget.style.background = '')}
                            >
                              {visibleIdxs.map(i => {
                                const val = row[normKeys[i]]
                                const isNum = typeof val === 'number'
                                return (
                                  <td key={i} style={{ padding: '0.3rem 0.5rem', whiteSpace: 'nowrap', textAlign: isNum ? 'right' : 'left' }}>
                                    {val == null || val === '' ? '' : isNum ? (val as number).toLocaleString('es-ES', { maximumFractionDigits: 4 }) : String(val)}
                                  </td>
                                )
                              })}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    {totalFilasSheet > 150 && (
                      <p style={{ fontSize: 12, color: '#9ca3af', marginTop: '0.5rem', textAlign: 'center' }}>
                        Mostrando 150 de {totalFilasSheet} filas
                      </p>
                    )}
                    {datos.metadata && typeof datos.metadata === 'object' && (!activeSheet || activeSheet === (datos.sheet_usada as string)) && (
                      <div style={{ marginTop: '0.75rem', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 10, padding: '0.75rem', fontSize: 13 }}>
                        <strong style={{ color: '#0f172a' }}>Cabecera detectada</strong>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(160px,1fr))', gap: '6px 12px', marginTop: 8 }}>
                          {Object.entries(datos.metadata as Record<string, unknown>).map(([k, v]) => (
                            <div key={k} style={{ color: '#475569' }}><span style={{ fontWeight: 600 }}>{k}:</span> {String(v ?? '—')}</div>
                          ))}
                        </div>
                      </div>
                    )}
                  </>
                )
              })()
            ) : (
              // Vista de campos para FACTURA, RECIBO, etc.
              <>
                <h3 style={{ marginTop: 0 }}>Campos Extraídos</h3>
                {editMode ? (
                  <div>
                    {Object.entries(editFields).map(([key, val]) => (
                      <label key={key} style={{ display: 'flex', flexDirection: 'column', marginBottom: '0.5rem', fontSize: 13 }}>
                        <span style={{ color: '#6b7280', fontWeight: 600 }}>{key}</span>
                        <input value={val} onChange={e => setEditFields(f => ({ ...f, [key]: e.target.value }))} style={{ padding: '0.4rem', border: '1px solid #d1d5db', borderRadius: 6 }} />
                      </label>
                    ))}
                    <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.75rem' }}>
                      <button onClick={saveEdit} disabled={saving} style={{ ...actionBtn, background: '#6366F1' }}>Guardar</button>
                      <button onClick={() => setEditMode(false)} style={{ ...actionBtn, background: '#e5e7eb', color: '#374151' }}>Cancelar</button>
                    </div>
                  </div>
                ) : (
                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <tbody>
                      {Object.entries(datos).filter(([k, v]) => !k.startsWith('_') && (typeof v !== 'object' || v === null)).map(([key, val]) => (
                        <tr key={key} style={{ borderBottom: '1px solid #f3f4f6' }}>
                          <td style={{ padding: '0.4rem 0.5rem', fontSize: 13, color: '#6b7280', fontWeight: 600 }}>{key}</td>
                          <td style={{ padding: '0.4rem 0.5rem', fontSize: 14 }}>{String(val ?? '—')}</td>
                        </tr>
                      ))}
                      {Object.keys(datos).filter(k => !k.startsWith('_') && (typeof datos[k] !== 'object' || datos[k] === null)).length === 0 && (
                        <tr><td colSpan={2} style={{ padding: '1rem', textAlign: 'center', color: '#9ca3af' }}>Sin campos extraídos</td></tr>
                      )}
                    </tbody>
                  </table>
                )}
              </>
            )}
          </div>
        </div>
      </div>

      {/* CA-03/CA-05: AI Configuration used */}
      <div style={{ ...section, marginTop: '1rem' }}>
        <h3 style={{ marginTop: 0 }}>🤖 Configuración IA</h3>
        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', fontSize: 14 }}>
          <div>
            <span style={{ color: '#6b7280', fontWeight: 600 }}>Modo: </span>
            <span style={{ background: '#e0e7ff', padding: '2px 8px', borderRadius: 6 }}>
              {doc.recipe_snapshot_id ? '📌 Snapshot' : '🧠 Zero-shot'}
            </span>
          </div>
          {doc.llm_model && (
            <div>
              <span style={{ color: '#6b7280', fontWeight: 600 }}>Modelo: </span>
              <span>{doc.llm_model}</span>
            </div>
          )}
          {doc.recipe_snapshot_id && (
            <div>
              <span style={{ color: '#6b7280', fontWeight: 600 }}>Snapshot: </span>
              <span style={{ fontSize: 12, fontFamily: 'monospace' }}>{doc.recipe_snapshot_id}</span>
            </div>
          )}
        </div>
        {doc.raw_ai_json && (
          <details style={{ marginTop: '0.75rem' }}>
            <summary style={{ cursor: 'pointer', color: '#6366F1', fontSize: 13 }}>Ver prompts y respuestas AI</summary>
            <pre style={{ whiteSpace: 'pre-wrap', fontSize: 12, background: '#f9fafb', padding: '0.75rem', borderRadius: 6, marginTop: '0.5rem', maxHeight: 400, overflow: 'auto' }}>
              {JSON.stringify(doc.raw_ai_json, null, 2)}
            </pre>
          </details>
        )}
      </div>

      {/* Audit trail */}
      {doc.logs && doc.logs.length > 0 && (
        <div style={{ ...section, marginTop: '1rem' }}>
          <h3 style={{ marginTop: 0 }}>📋 Historial de Cambios</h3>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #e5e7eb' }}>
                <th style={{ textAlign: 'left', padding: 4, color: '#6b7280' }}>Acción</th>
                <th style={{ textAlign: 'left', padding: 4, color: '#6b7280' }}>Usuario</th>
                <th style={{ textAlign: 'left', padding: 4, color: '#6b7280' }}>Fecha</th>
                <th style={{ textAlign: 'left', padding: 4, color: '#6b7280' }}>Detalle</th>
              </tr>
            </thead>
            <tbody>
              {doc.logs.map((l: LogCambio) => (
                <tr key={l.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                  <td style={{ padding: 4 }}><span style={{ background: '#e0e7ff', padding: '1px 6px', borderRadius: 4 }}>{l.accion}</span></td>
                  <td style={{ padding: 4 }}>{l.usuario_id || '—'}</td>
                  <td style={{ padding: 4 }}>{new Date(l.created_at).toLocaleString()}</td>
                  <td style={{ padding: 4, maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis' }}>{l.detalle ? JSON.stringify(l.detalle).substring(0, 100) : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {doc.datos_confirmados && (
        <div style={{ ...section, marginTop: '1rem', background: '#F0FDF4', border: '1px solid #BBF7D0' }}>
          <h3 style={{ marginTop: 0, color: '#166534' }}>✅ Datos Confirmados</h3>
          <pre style={{ whiteSpace: 'pre-wrap', fontSize: 13 }}>{JSON.stringify(doc.datos_confirmados, null, 2)}</pre>
        </div>
      )}
    </div>
  )
}

const section: React.CSSProperties = { border: '1px solid #e5e7eb', borderRadius: 8, padding: '1rem', background: '#fff' }
const actionBtn: React.CSSProperties = { padding: '0.5rem 1rem', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 14, fontWeight: 600 }
const statusBadge: React.CSSProperties = { color: '#fff', padding: '3px 12px', borderRadius: 12, fontSize: 13, fontWeight: 600 }
const statusColor: Record<string, string> = { CONFIRMED: '#10B981', REVIEW: '#3B82F6', PROCESSING: '#F59E0B', PENDING: '#9CA3AF', FAILED: '#EF4444' }
