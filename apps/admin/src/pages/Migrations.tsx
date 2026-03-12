import React, { useEffect, useState } from 'react'

import {
  runMigrations,
  getMigrationConfig,
  getMigrationStatus,
  getMigrationHistory,
  refreshMigrations,
  type MigrationConfig,
  type MigrationHistoryItem,
  type MigrationState,
} from '../services/ops'

function formatMigrationMessage(message?: string | null) {
  if (!message) return null
  if (message === 'inline_migrations_disabled') {
    return 'Las migraciones inline estan deshabilitadas en este entorno.'
  }
  if (message.startsWith('migration_script_missing:')) {
    const path = message.replace('migration_script_missing:', '')
    return `No se encontro el runner de migraciones en el servidor: ${path}`
  }
  return message
}

export default function Migraciones() {
  const [loading, setLoading] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)
  const [config, setConfig] = useState<MigrationConfig | null>(null)
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
        setMsg(res?.ok ? 'Migraciones iniciadas correctamente' : 'No se pudo ejecutar el runner')
      }
      try {
        const s = await getMigrationStatus()
        setState(s)
      } catch {}
    } catch (e: any) {
      if (e?.status === 409) {
        setMsg('Ya hay una migracion en curso')
      } else {
        const detail = formatMigrationMessage(e?.message || 'desconocido')
        setMsg(`Error al ejecutar migraciones: ${detail}`)
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | undefined

    async function tick() {
      try {
        try {
          await refreshMigrations()
        } catch {}
        try {
          const cfg = await getMigrationConfig()
          setConfig(cfg)
        } catch {}
        const s = await getMigrationStatus()
        setState(s)
        if (s.running) {
          timer = setTimeout(tick, 3000)
        } else {
          try {
            const r = await getMigrationHistory(20)
            if (r?.ok && Array.isArray(r.items)) setHistory(r.items)
          } catch {}
        }
      } catch {
        timer = setTimeout(tick, 5000)
      }
    }

    void tick()
    void getMigrationHistory(20)
      .then((r) => {
        if (r?.ok && Array.isArray(r.items)) setHistory(r.items)
      })
      .catch(() => {})

    return () => {
      if (timer) clearTimeout(timer)
    }
  }, [])

  async function onRefresh() {
    try {
      await refreshMigrations()
    } catch {}
    try {
      const cfg = await getMigrationConfig()
      setConfig(cfg)
    } catch {}
    try {
      const s = await getMigrationStatus()
      setState(s)
    } catch {}
    try {
      const r = await getMigrationHistory(20)
      if (r?.ok && Array.isArray(r.items)) setHistory(r.items)
    } catch {}
  }

  return (
    <div className="p-4">
      <h2 className="text-lg font-semibold mb-3">Migraciones de base de datos</h2>
      <p className="text-sm text-slate-600 mb-2">
        Este boton ejecuta en el backend el runner SQL idempotente <code>ops/scripts/migrate_all_migrations_idempotent.py</code> y registra el resultado en el historial.
      </p>
      <div className="mb-4 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-amber-800 text-sm">
        Nota: el runner registra en <code>_migrations</code> las migraciones ya aplicadas y solo deja pendientes las que faltan por procesar.
      </div>
      {config && !config.inline_enabled && (
        <div className="mb-4 rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-rose-800 text-sm">
          {formatMigrationMessage(config.reason) || 'Las migraciones inline no estan disponibles en este entorno.'}
        </div>
      )}

      <button
        disabled={loading || (state?.running ?? false) || (config ? !config.inline_enabled : false)}
        onClick={onRun}
        className={`inline-flex items-center rounded-lg px-4 py-2 text-sm font-semibold text-white shadow-sm ${loading ? 'bg-slate-400' : 'bg-indigo-600 hover:bg-indigo-700'}`}
      >
        {loading ? 'Ejecutando...' : 'Ejecutar migraciones'}
      </button>
      <button
        onClick={onRefresh}
        className="ml-2 inline-flex items-center rounded-lg border border-indigo-300 px-3 py-2 text-sm font-semibold text-indigo-700"
      >
        Refrescar estado
      </button>

      {msg && <div className="mt-3 text-sm text-slate-700">{msg}</div>}
      {state && (
        <div className="mt-3 text-sm text-slate-700">
          <div>
            Estado: {state.running ? 'En ejecucion' : state.ok === true ? 'Completado' : state.ok === false ? 'Error' : 'Desconocido'}
          </div>
          <div>Modo: {state.mode || 'n/d'}</div>
          {state.started_at && <div>Inicio: {new Date(state.started_at).toLocaleString()}</div>}
          {state.finished_at && <div>Fin: {new Date(state.finished_at).toLocaleString()}</div>}
          {state.error && (
            <div className="text-red-600">Error: {formatMigrationMessage(state.error) || state.error}</div>
          )}
        </div>
      )}
      <div className="mt-6">
        <h3 className="mb-2 text-base font-semibold">Historial</h3>
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
                <tr>
                  <td className="px-2 py-2 text-slate-500" colSpan={6}>
                    Sin registros
                  </td>
                </tr>
              )}
              {history.map((h) => (
                <tr key={h.id} className="border-t border-slate-200">
                  <td className="px-2 py-1">{new Date(h.started_at).toLocaleString()}</td>
                  <td className="px-2 py-1">{h.finished_at ? new Date(h.finished_at).toLocaleString() : '-'}</td>
                  <td className="px-2 py-1">{h.mode}</td>
                  <td className="px-2 py-1">{h.ok === true ? 'OK' : h.ok === false ? 'X' : '-'}</td>
                  <td className="px-2 py-1">{h.job_id || '-'}</td>
                  <td className="px-2 py-1 text-red-600">{formatMigrationMessage(h.error) || h.error || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
