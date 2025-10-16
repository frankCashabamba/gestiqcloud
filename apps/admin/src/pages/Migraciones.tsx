import React, { useEffect, useState } from 'react'
import { runMigrations, getMigrationStatus, getMigrationHistory, refreshMigrations, type MigrationState, type MigrationHistoryItem } from '../services/ops'

export default function Migraciones() {
  const [loading, setLoading] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)
  const [state, setState] = useState<MigrationState | null>(null)
  const [history, setHistory] = useState<MigrationHistoryItem[]>([])

  async function onRun() {
    setLoading(true)
    setMsg(null)
    try {
      const res = await runMigrations()
      if (res?.ok && res?.started === false && res?.message === 'sin_migraciones_pendientes') {
        setMsg('Sin migraciones pendientes')
      } else {
        setMsg(res?.ok ? 'Migraciones disparadas correctamente' : 'No se pudo disparar el job')
      }
      // empieza a refrescar estado si inline
      try { const s = await getMigrationStatus(); setState(s) } catch {}
    } catch (e: any) {
      if (e?.status === 409) {
        setMsg('Ya hay una migracion en curso')
      } else {
        setMsg(`Error al ejecutar migraciones: ${e?.message || 'desconocido'}`)
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let timer: any
    async function tick() {
      try {
        // Intenta cerrar runs de Render consultando el backend
        try { await refreshMigrations() } catch {}
        const s = await getMigrationStatus()
        setState(s)
        if (s.running) {
          timer = setTimeout(tick, 3000)
        } else {
          // Al terminar, recarga historial
          try {
            const r = await getMigrationHistory(20)
            if (r?.ok && Array.isArray(r.items)) setHistory(r.items)
          } catch {}
        }
      } catch {
        timer = setTimeout(tick, 5000)
      }
    }
    tick()
    // carga inicial de historial
    getMigrationHistory(20)
      .then((r) => { if (r?.ok && Array.isArray(r.items)) setHistory(r.items) })
      .catch(() => {})
    return () => { if (timer) clearTimeout(timer) }
  }, [])

  async function onRefresh() {
    try { await refreshMigrations() } catch {}
    try { const s = await getMigrationStatus(); setState(s) } catch {}
    try { const r = await getMigrationHistory(20); if (r?.ok && Array.isArray(r.items)) setHistory(r.items) } catch {}
  }

  return (
    <div className="p-4">
      `<h2 className="text-lg font-semibold mb-3">Migraciones de base de datos</h2>
      <p className="text-sm text-slate-600 mb-2">Este botón solicita al backend que dispare el Job de Render configurado (RENDER_MIGRATE_JOB_ID). Úsalo tras cambios de esquema.</p>\n      <div className="mb-4 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-amber-800 text-sm">\n        Nota: Por ahora el pipeline es manual; en el futuro se activará automáticamente al detectar cambios de esquema.\n      </div>
      {state?.alembic_heads && state.alembic_heads.count -ne 1 && (
        <div className="mb-4 rounded-md border border-red-300 bg-red-50 px-3 py-2 text-red-800 text-sm">
          Advertencia: se detectaron {state.alembic_heads.count} heads de Alembic. Heads: {state.alembic_heads.heads.join(',')}
        </div>
      )}
      <div className="mb-4 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-amber-800 text-sm">
        Nota: Por ahora el pipeline es manual; en el futuro se activara automaticamente al detectar cambios de esquema.
      </div>
      {state?.alembic_heads && state.alembic_heads.count !== 1 && (
        <div className="mb-4 rounded-md border border-red-300 bg-red-50 px-3 py-2 text-red-800 text-sm">
          Advertencia: se detectaron {state.alembic_heads.count} heads de Alembic. Heads: {state.alembic_heads.heads.join(', ')}
        </div>
      )}
      <button
        disabled={loading || (state?.running ?? false)}
        onClick={onRun}
        className={`inline-flex items-center rounded-lg px-4 py-2 text-sm font-semibold text-white shadow-sm ${loading ? 'bg-slate-400' : 'bg-indigo-600 hover:bg-indigo-700'}`}
      >
        {loading ? 'Ejecutandoâ€¦' : 'Ejecutar migraciones'}
      </button>
      <button
        onClick={onRefresh}
        className="inline-flex items-center rounded-lg px-3 py-2 text-sm font-semibold text-indigo-700 border border-indigo-300 ml-2"
      >
        Refrescar estado
      </button>
      {msg && <div className="mt-3 text-sm text-slate-700">{msg}</div>}
      {state && (
        <div className="mt-3 text-sm text-slate-700">
          <div>Estado: {state.running ? 'En ejecuciÃ³n' : (state.ok === true ? 'Completado' : state.ok === false ? 'Error' : 'Desconocido')}</div>
          <div>Modo: {state.mode || 'n/d'}</div>
          {state.started_at && <div>Inicio: {new Date(state.started_at).toLocaleString()}</div>}
          {state.finished_at && <div>Fin: {new Date(state.finished_at).toLocaleString()}</div>}
          {state.error && <div className="text-red-600">Error: {state.error}</div>}
        </div>
      )}
      <div className="mt-6">
        <h3 className="text-base font-semibold mb-2">Historial</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500">
                <th className="px-2 py-1">Inicio</th>
                <th className="px-2 py-1">Fin</th>
                <th className="px-2 py-1">Modo</th>
                <th className="px-2 py-1">OK</th>
                <th className="px-2 py-1">Job</th>
                <th className="px-2 py-1">Error</th>
              </tr>
            </thead>
            <tbody>
              {history.length === 0 && (
                <tr><td className="px-2 py-2 text-slate-500" colSpan={6}>Sin registros</td></tr>
              )}
              {history.map((h) => (
                <tr key={h.id} className="border-t border-slate-200">
                  <td className="px-2 py-1">{new Date(h.started_at).toLocaleString()}</td>
                  <td className="px-2 py-1">{h.finished_at ? new Date(h.finished_at).toLocaleString() : '-'}</td>
                  <td className="px-2 py-1">{h.mode}</td>
                  <td className="px-2 py-1">{h.ok === true ? 'âœ”' : h.ok === false ? 'âœ–' : '-'}</td>
                  <td className="px-2 py-1">{h.job_id || '-'}</td>
                  <td className="px-2 py-1 text-red-600">{h.error || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}



