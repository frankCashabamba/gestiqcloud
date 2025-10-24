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
  set('--color-primary', c['primary'])
  set('--color-on-primary', c['onPrimary'])
  set('--color-bg', c['bg'])
  set('--color-fg', c['fg'])
  set('--color-muted', c['muted'])
  set('--color-surface', c['surface'])
  set('--color-border', c['border'])
  set('--color-success', c['success'])
  set('--color-warning', c['warning'])
  set('--color-danger', c['danger'])
  set('--color-focus-ring', c['focusRing'])

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
}
