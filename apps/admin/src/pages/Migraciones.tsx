import React, { useEffect, useState } from 'react'
import { runMigrations, getMigrationStatus, type MigrationState } from '../services/ops'

export default function Migraciones() {
  const [loading, setLoading] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)
  const [state, setState] = useState<MigrationState | null>(null)

  async function onRun() {
    setLoading(true)
    setMsg(null)
    try {
      const res = await runMigrations()
      setMsg(res?.ok ? 'Migraciones disparadas correctamente' : 'No se pudo disparar el job')
      // empieza a refrescar estado si inline
      try { const s = await getMigrationStatus(); setState(s) } catch {}
    } catch (e: any) {
      setMsg(`Error al ejecutar migraciones: ${e?.message || 'desconocido'}`)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let timer: any
    async function tick() {
      try {
        const s = await getMigrationStatus()
        setState(s)
        if (s.running) {
          timer = setTimeout(tick, 3000)
        }
      } catch {
        timer = setTimeout(tick, 5000)
      }
    }
    tick()
    return () => { if (timer) clearTimeout(timer) }
  }, [])

  return (
    <div className="p-4">
      <h2 className="text-lg font-semibold mb-3">Migraciones de base de datos</h2>
      <p className="text-sm text-slate-600 mb-4">Este botón solicita al backend que dispare el Job de Render configurado (RENDER_MIGRATE_JOB_ID). Úsalo tras cambios de esquema.</p>
      <button
        disabled={loading}
        onClick={onRun}
        className={`inline-flex items-center rounded-lg px-4 py-2 text-sm font-semibold text-white shadow-sm ${loading ? 'bg-slate-400' : 'bg-indigo-600 hover:bg-indigo-700'}`}
      >
        {loading ? 'Ejecutando…' : 'Ejecutar migraciones'}
      </button>
      {msg && <div className="mt-3 text-sm text-slate-700">{msg}</div>}
      {state && (
        <div className="mt-3 text-sm text-slate-700">
          <div>Estado: {state.running ? 'En ejecución' : (state.ok === true ? 'Completado' : state.ok === false ? 'Error' : 'Desconocido')}</div>
          <div>Modo: {state.mode || 'n/d'}</div>
          {state.started_at && <div>Inicio: {new Date(state.started_at).toLocaleString()}</div>}
          {state.finished_at && <div>Fin: {new Date(state.finished_at).toLocaleString()}</div>}
          {state.error && <div className="text-red-600">Error: {state.error}</div>}
        </div>
      )}
    </div>
  )
}
