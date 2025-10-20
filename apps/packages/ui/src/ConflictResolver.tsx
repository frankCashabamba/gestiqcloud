import React from 'react'

export type Conflict = {
  table?: string
  id?: string
  local?: any
  remote?: any
  conflict_details?: any
}

export interface ConflictResolverProps {
  conflicts?: Conflict[]
  onResolve?: (conflict: Conflict, resolution: 'keep_local'|'keep_remote'|'merge') => void
}

export default function ConflictResolver({ conflicts = [], onResolve }: ConflictResolverProps) {
  if (!conflicts.length) return null
  return (
    <div style={{ position: 'fixed', right: 16, bottom: 16, maxWidth: 360 }}>
      <div style={{ background: '#fff7ed', border: '1px solid #f59e0b', borderRadius: 8, padding: 12 }}>
        <div style={{ fontWeight: 600, marginBottom: 8 }}>Conflictos de sincronización</div>
        {conflicts.slice(0, 3).map((c, i) => (
          <div key={i} style={{ fontSize: 12, marginBottom: 8 }}>
            <div><b>{c.table}</b> · {c.id}</div>
            <div>Revise y seleccione una resolución.</div>
            {onResolve && (
              <div style={{ marginTop: 6, display: 'flex', gap: 6 }}>
                <button onClick={() => onResolve(c, 'keep_local')} style={{ padding: '4px 8px', background: '#e5e7eb', borderRadius: 4 }}>Mantener local</button>
                <button onClick={() => onResolve(c, 'keep_remote')} style={{ padding: '4px 8px', background: '#e5e7eb', borderRadius: 4 }}>Mantener servidor</button>
              </div>
            )}
          </div>
        ))}
        {conflicts.length > 3 && <div style={{ fontSize: 12 }}>+{conflicts.length - 3} más…</div>}
      </div>
    </div>
  )
}
