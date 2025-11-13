import React, { useEffect, useState } from 'react'
import { sendTelemetry } from '@shared'

export default function UpdatePrompt() {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const onNeedRefresh = () => setVisible(true)
    window.addEventListener('pwa:need-refresh', onNeedRefresh)
    return () => window.removeEventListener('pwa:need-refresh', onNeedRefresh)
  }, [])

  if (!visible) return null

  const doUpdate = () => {
    sendTelemetry('pwa_update_clicked')
    try { (window as any).__updateSW?.(true) } catch {}
  }

  return (
    <div style={{ position: 'fixed', left: 12, right: 12, bottom: 56, zIndex: 1001 }}>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', justifyContent: 'space-between', background: '#1f2937', color: 'white', padding: '10px 12px', borderRadius: 8, border: '1px solid #334155', boxShadow: '0 6px 18px rgba(0,0,0,.18)', fontSize: 14 }}>
        <span>Nueva versión disponible.</span>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={() => { setVisible(false); sendTelemetry('pwa_update_dismissed') }} style={{ background: 'transparent', color: '#cbd5e1', border: '1px solid #475569', padding: '6px 10px', borderRadius: 6 }}>Luego</button>
          <button onClick={doUpdate} style={{ background: '#22c55e', color: '#0b2415', border: '1px solid #16a34a', padding: '6px 10px', borderRadius: 6, fontWeight: 600 }}>Actualizar</button>
        </div>
      </div>
    </div>
  )
}
