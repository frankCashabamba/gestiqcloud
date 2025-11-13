import React, { useEffect, useRef, useState } from 'react'

export default function OfflineReadyToast() {
  const [visible, setVisible] = useState(false)
  const timer = useRef<number | null>(null)
  const buildId = (typeof __APP_BUILD_ID__ !== 'undefined' ? __APP_BUILD_ID__ : 'dev') as string
  const KEY = `pwa_offline_ready_seen_${buildId}`

  useEffect(() => {
    const onReady = () => {
      try {
        if (localStorage.getItem(KEY)) return
        localStorage.setItem(KEY, '1')
      } catch {}
      setVisible(true)
      if (timer.current) window.clearTimeout(timer.current)
      timer.current = window.setTimeout(() => setVisible(false), 3500)
    }
    window.addEventListener('pwa:offline-ready', onReady)
    return () => {
      window.removeEventListener('pwa:offline-ready', onReady)
      if (timer.current) window.clearTimeout(timer.current)
    }
  }, [])

  if (!visible) return null

  return (
    <div style={{ position: 'fixed', left: 12, right: 12, bottom: 100, zIndex: 1002 }}>
      <div style={{ background: '#0b3d2e', color: 'white', padding: '10px 12px', borderRadius: 8, border: '1px solid #16a34a', boxShadow: '0 6px 18px rgba(0,0,0,.18)', fontSize: 14, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span>Listo para usar sin conexión.</span>
        <button onClick={() => setVisible(false)} style={{ background: 'transparent', color: '#cbd5e1', border: '1px solid #475569', padding: '6px 10px', borderRadius: 6 }}>Ok</button>
      </div>
    </div>
  )
}
