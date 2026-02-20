export type ThemeConfig = {
  brand?: { name?: string; logoUrl?: string | null; faviconUrl?: string | null }
  colors?: Record<string, string>
  typography?: { fontFamily?: string; fontSizeBase?: string }
  radius?: { sm?: string; md?: string; lg?: string }
  shadows?: { sm?: string; md?: string }
  mode?: 'light' | 'dark' | 'auto'
  sector?: string
  components?: Record<string, any>
}

export function applyTheme(t: ThemeConfig) {
  const r = document.documentElement
  const set = (k: string, v?: string | null) => {
    if (v && typeof v === 'string') r.style.setProperty(k, v)
  }
  const c = t.colors || {}
  // Compute onPrimary if not provided to ensure readable contrast
  const hex = String(c['primary'] || '').trim()
  const computeOnPrimary = (h: string): string => {
    const m = /^#?([\da-f]{2})([\da-f]{2})([\da-f]{2})$/i.exec(h)
    if (!m) return '#ffffff'
    const r8 = parseInt(m[1], 16) / 255
    const g8 = parseInt(m[2], 16) / 255
    const b8 = parseInt(m[3], 16) / 255
    const srgb = [r8, g8, b8].map(v => (v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4)))
    const L = 0.2126 * srgb[0] + 0.7152 * srgb[1] + 0.0722 * srgb[2]
    return L > 0.5 ? '#000000' : '#ffffff'
  }

  const onPrimary = c['onPrimary'] || (hex ? computeOnPrimary(hex) : undefined)

  set('--color-primary', c['primary'])
  // Bridge to tenant CSS variables (gc-*) so tenant shell/buttons can inherit theme
  set('--gc-primary', c['primary'])
  set('--gc-primary-dark', c['primaryDark'] || c['primary'])
  set('--gc-on-primary', c['onPrimary'])
  set('--color-on-primary', c['onPrimary'])
  if (!c['onPrimary'] && onPrimary) {
    set('--color-on-primary', onPrimary)
    set('--gc-on-primary', onPrimary)
  }
  set('--color-bg', c['bg'])
  set('--color-fg', c['fg'])
  set('--color-muted', c['muted'])
  set('--color-surface', c['surface'])
  set('--color-border', c['border'])
  set('--color-success', c['success'])
  set('--color-warning', c['warning'])
  set('--color-danger', c['danger'])
  set('--color-focus-ring', c['focusRing'])

  // Map to legacy template tokens where relevant
  set('--primary', c['primary'])
  set('--topbar-bg', c['primary'])
  set('--sidebar-active', c['primary'])
  set('--btn-primary', c['primary'])

  const ty = t.typography || {}
  set('--font-family', ty.fontFamily)
  set('--font-size-base', ty.fontSizeBase)

  const radius = t.radius || {}
  set('--radius-sm', radius.sm)
  set('--radius-md', radius.md)
  set('--radius-lg', radius.lg)

  const sh = t.shadows || {}
  set('--shadow-sm', sh.sm)
  set('--shadow-md', sh.md)

  const mode = t.mode || 'light'
  r.dataset.themeMode = mode
  if (t.brand?.name) {
    // Expose a stable data attribute for theme scoping (e.g., per tenant)
    r.dataset.theme = t.brand.name
  }
  if (t.sector) {
    r.dataset.sector = t.sector
  }

  // Update meta theme-color for better mobile UX
  try {
    const metaName = 'theme-color'
    let m = document.querySelector(`meta[name="${metaName}"]`) as HTMLMetaElement | null
    if (!m) {
      m = document.createElement('meta')
      m.setAttribute('name', metaName)
      document.head.appendChild(m)
    }
    if (c['primary']) m.setAttribute('content', c['primary'])
  } catch {}

  // Mark theme as ready (avoid FOUC)
  try {
    r.classList.remove('theme-pending')
    window.dispatchEvent(new CustomEvent('theme:ready'))
  } catch {}
}
