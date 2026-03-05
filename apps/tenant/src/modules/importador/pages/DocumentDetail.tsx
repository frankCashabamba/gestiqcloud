import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { fetchDocument, confirmDocument, editDocumentFields, rejectDocument, type Documento, type LogCambio } from '../services'

export default function DocumentDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [doc, setDoc] = useState<Documento | null>(null)
  const [loading, setLoading] = useState(true)
  const [editMode, setEditMode] = useState(false)
  const [editFields, setEditFields] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const load = async () => {
    if (!id) return
    setLoading(true)
    try { setDoc(await fetchDocument(id)) } catch { setError('Error cargando') }
    setLoading(false)
  }

  useEffect(() => { load() }, [id])

  const handleConfirm = async () => {
    if (!id || !doc) return
    setSaving(true)
    try {
      await confirmDocument(id, doc.datos_extraidos || {})
      load()
    } catch { setError('Error confirmando') }
    setSaving(false)
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
  const confPct = doc.confianza_clasificacion != null ? Math.round(doc.confianza_clasificacion * 100) : null

  return (
    <div style={{ padding: '1.5rem' }}>
      <button onClick={() => navigate(-1)} style={{ marginBottom: '1rem', cursor: 'pointer', border: 'none', background: 'none', fontSize: 14, color: '#6366F1' }}>← Volver</button>
      {error && <div style={{ color: 'red', marginBottom: '0.5rem' }}>{error}</div>}

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
        <div>
          <h2 style={{ marginBottom: 4 }}>📄 {doc.nombre_archivo}</h2>
          <div style={{ display: 'flex', gap: '0.75rem', fontSize: 13, color: '#6b7280' }}>
            <span>{doc.tipo_archivo}</span>
            <span>{(doc.tamanio_bytes / 1024).toFixed(0)} KB</span>
            <span>{new Date(doc.created_at).toLocaleString()}</span>
          </div>
        </div>
        {doc.estado === 'REVIEW' && (
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            {!((doc.datos_extraidos as any)?.filas) && (
              <button onClick={startEdit} style={{ ...actionBtn, background: '#F59E0B' }}>Editar</button>
            )}
            <button onClick={handleReject} style={{ ...actionBtn, background: '#EF4444' }}>Rechazar</button>
            <button onClick={handleConfirm} disabled={saving} style={{ ...actionBtn, background: '#10B981' }}>{saving ? '...' : 'Confirmar'}</button>
          </div>
        )}
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
                const allRows = datos.filas as Record<string, unknown>[]
                // columnas_norm = claves reales de los dicts de filas (ej: "precio_unitario_venta")
                // columnas      = nombres display para la UI (ej: "PRECIO UNITARIO VENTA")
                const normKeys: string[] = datos.columnas_norm && Array.isArray(datos.columnas_norm) && (datos.columnas_norm as string[]).length > 0
                  ? (datos.columnas_norm as string[])
                  : allRows.length > 0 ? Object.keys(allRows[0]).filter(k => k !== '_sheet') : []
                const displayNames: string[] = datos.columnas && Array.isArray(datos.columnas) ? (datos.columnas as string[]) : normKeys
                // Filtrar columnas que no tienen ningún dato real en las primeras 30 filas
                const visibleIdxs = normKeys.reduce<number[]>((acc, key, i) => {
                  const vals = allRows.slice(0, 30).map(r => r[key])
                  if (vals.some(v => v !== null && v !== undefined && v !== '' && v !== 0)) acc.push(i)
                  return acc
                }, [])
                return (
                  <>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                      <h3 style={{ margin: 0 }}>Filas del documento</h3>
                      <span style={{ fontSize: 12, color: '#6b7280' }}>{datos.total_filas as number} filas totales · {visibleIdxs.length} columnas</span>
                    </div>
                    <div style={{ overflowX: 'auto', maxHeight: 400, overflowY: 'auto' }}>
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
                    {(datos.total_filas as number) > 150 && (
                      <p style={{ fontSize: 12, color: '#9ca3af', marginTop: '0.5rem', textAlign: 'center' }}>
                        Mostrando 150 de {datos.total_filas as number} filas
                      </p>
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
