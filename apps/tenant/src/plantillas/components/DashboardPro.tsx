/**
 * Dashboard Pro - reusable base component for sector dashboards
 */
import React, { useState, useEffect, ReactNode, useMemo } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useMisModulos } from '../../hooks/useMisModulos'
import { fetchCompanyTheme, type ThemeResponse } from '../../services/theme'

interface DashboardProProps {
  sectorName: string
  sectorIcon: string
  children: ReactNode
  customLinks?: Array<{ label: string; href: string; icon: string }>
  darkModeDefault?: boolean
}

const getModuleIcon = (slug: string): string => {
  const icons: Record<string, string> = {
    ventas: '$',
    clientes: '@',
    products: '#',
    inventario: 'I',
    facturacion: 'F',
    facturacion_es: 'F',
    compras: 'C',
    proveedores: 'P',
    gastos: 'G',
    finanzas: 'M',
    contabilidad: 'A',
    pos: 'P',
    tpv: 'P',
    imports: 'I',
    rrhh: 'H',
    configuracion: 'S',
    settings: 'S',
    usuarios: 'U',
  }
  return icons[slug.toLowerCase()] || '•'
}

const pickTextColorForBackground = (bgColor: string): string => {
  if (typeof window === 'undefined' || typeof document === 'undefined') return '#ffffff'
  const probe = document.createElement('span')
  probe.style.color = bgColor
  probe.style.display = 'none'
  document.body.appendChild(probe)
  const computed = window.getComputedStyle(probe).color
  document.body.removeChild(probe)

  const match = computed.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/i)
  if (!match) return '#ffffff'
  const r = Number(match[1]) / 255
  const g = Number(match[2]) / 255
  const b = Number(match[3]) / 255

  const toLinear = (c: number) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4)
  const luminance = 0.2126 * toLinear(r) + 0.7152 * toLinear(g) + 0.0722 * toLinear(b)

  return luminance > 0.45 ? '#0f172a' : '#ffffff'
}
const DashboardPro: React.FC<DashboardProProps> = ({
  sectorName,
  sectorIcon,
  children,
  customLinks = [],
  darkModeDefault = false,
}) => {
  const { t } = useTranslation()
  const { empresa } = useParams()
  const [theme, setTheme] = useState<ThemeResponse | null>(null)
  const [darkMode, setDarkMode] = useState(darkModeDefault)
  const { modules, loading: modulosLoading } = useMisModulos()
  const [isMobileView, setIsMobileView] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false
    return window.innerWidth <= 1024
  })
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const [moduleSearch, setModuleSearch] = useState('')

  useEffect(() => {
    const loadTheme = async () => {
      try {
        const themeData = await fetchCompanyTheme(empresa)
        if (themeData?.colors) {
          setTheme(themeData)
          const primaryColor = themeData.colors.primary || '#5B8CFF'
          const focusColor =
            themeData.colors.focus ||
            themeData.colors.accent ||
            themeData.colors.secondary ||
            primaryColor
          const onPrimaryColor = pickTextColorForBackground(primaryColor)
          document.documentElement.style.setProperty('--primary', primaryColor)
          document.documentElement.style.setProperty('--focus', focusColor)
          document.documentElement.style.setProperty('--on-primary', onPrimaryColor)
          document.documentElement.style.setProperty('--topbar-bg', primaryColor)
          document.documentElement.style.setProperty('--sidebar-active', primaryColor)
          document.documentElement.style.setProperty('--btn-primary', primaryColor)
        }
        // Arrancamos en modo claro para alinear con la referencia de retail
        document.documentElement.classList.add('light-theme')
      } catch (err) {
        console.error('Error loading theme:', err)
      }
    }
    loadTheme()
  }, [empresa])

  // Responsive behavior for drawer and layout
  useEffect(() => {
    const handleResize = () => setIsMobileView(window.innerWidth <= 1024)
    handleResize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  const filteredModules = useMemo(() => {
    const term = moduleSearch.trim().toLowerCase()
    if (!term) return modules
    return modules.filter((m) =>
      (m.name || '').toLowerCase().includes(term) || (m.slug || '').toLowerCase().includes(term)
    )
  }, [modules, moduleSearch])

  const groupedModules = useMemo(() => {
    return filteredModules.reduce((acc: Record<string, typeof modules>, modulo: any) => {
      const category = (modulo.categoria || modulo.category || 'General').toString()
      if (!acc[category]) acc[category] = []
      acc[category].push(modulo)
      return acc
    }, {})
  }, [filteredModules])

  const toggleTheme = () => {
    setDarkMode((prev) => {
      const next = !prev
      document.documentElement.classList.toggle('dark-theme', next)
      if (!next) {
        document.documentElement.classList.add('light-theme')
      } else {
        document.documentElement.classList.remove('light-theme')
      }
      return next
    })
  }

  return (
    <div className={`dashboard-pro-app ${darkMode ? 'dark' : 'light'}`}>
      <header className="topbar">
        {isMobileView && (
          <button className="icon-btn" onClick={() => setIsMenuOpen(true)} aria-label={t('dashboardPro.openMenu')}>
            <span className="menu-bars" aria-hidden />
          </button>
        )}
        <div className="brand">
          <div className="brand__logo" />
          <span>
            {sectorIcon} {sectorName}
          </span>
        </div>
        <div className="search">
          <input placeholder="Buscar productos, clientes o documentos" aria-label="Buscar en el dashboard" />
          <span>/</span>
        </div>
        <select aria-label="Seleccionar sucursal">
          <option>{t('dashboardPro.stores.main')}</option>
          <option>{t('dashboardPro.stores.branch', { n: 1 })}</option>
          <option>{t('dashboardPro.stores.branch', { n: 2 })}</option>
        </select>
        <input type="date" defaultValue={new Date().toISOString().split('T')[0]} aria-label="Seleccionar fecha" />
        <button className="btn" onClick={toggleTheme}>
          {darkMode ? t('dashboardPro.lightMode') : t('dashboardPro.darkMode')}
        </button>
      </header>

      <aside className="sidebar">
        <nav>
          <ul>
            <li>
              <Link to={`/${empresa}`} className="active">
                {t('nav.dashboard')}
              </Link>
            </li>

            {modulosLoading ? (
              <li className="sidebar-loading">{t('dashboardPro.loadingModules')}</li>
            ) : (
              Object.entries(groupedModules)
                .sort(([a], [b]) => a.localeCompare(b))
                .map(([categoria, mods]) => (
                  <React.Fragment key={categoria}>
                    <li className="sidebar-divider">{categoria}</li>
                    {mods
                      .sort((a, b) => (a.name || '').localeCompare(b.name || ''))
                      .map((modulo) => {
                        const slug = modulo.slug || (modulo.name || '').toLowerCase()
                        const icon = getModuleIcon(slug)
                        const to = `/${empresa}/${slug}`
                        return (
                          <li key={modulo.id}>
                            <Link to={to}>
                              <span className="sidebar-icon">{icon}</span>
                              <span>{modulo.name}</span>
                            </Link>
                          </li>
                        )
                      })}
                  </React.Fragment>
                ))
            )}

            {customLinks.length > 0 && (
              <>
                <li className="sidebar-divider">{t('dashboardPro.sectorTools')}</li>
                {customLinks.map((link, i) => (
                  <li key={i}>
                    <a href={link.href}>
                      {link.icon} {link.label}
                    </a>
                  </li>
                ))}
              </>
            )}
          </ul>
        </nav>
        <small>{t('dashboardPro.shortcuts')}</small>
      </aside>

      {isMobileView && (
        <>
          <div className={`mobile-drawer ${isMenuOpen ? 'open' : ''}`}>
            <div className="mobile-drawer__header">
              <span className="brand-inline">
                <span className="brand__logo" />
                {sectorIcon} {sectorName}
              </span>
              <button className="icon-btn" onClick={() => setIsMenuOpen(false)} aria-label={t('dashboardPro.closeMenu')}>
                X
              </button>
            </div>
            <div className="mobile-drawer__search">
              <input
                placeholder={t('dashboardPro.searchModules') || 'Buscar módulo o acción'}
                value={moduleSearch}
                onChange={(e) => setModuleSearch(e.target.value)}
              />
            </div>
            <nav className="mobile-drawer__nav">
              <ul>
                <li>
                  <Link to={`/${empresa}`} onClick={() => setIsMenuOpen(false)} className="active">
                    {t('nav.dashboard')}
                  </Link>
                </li>
                {modulosLoading ? (
                  <li className="sidebar-loading">{t('dashboardPro.loadingModules')}</li>
                ) : (
                  Object.entries(groupedModules)
                    .sort(([a], [b]) => a.localeCompare(b))
                    .map(([categoria, mods]) => (
                      <React.Fragment key={`m-${categoria}`}>
                        <li className="sidebar-divider">{categoria}</li>
                        {mods
                          .sort((a, b) => (a.name || '').localeCompare(b.name || ''))
                          .map((modulo) => {
                            const slug = modulo.slug || (modulo.name || '').toLowerCase()
                            const icon = getModuleIcon(slug)
                            const to = `/${empresa}/${slug}`
                            return (
                              <li key={`m-${modulo.id}`}>
                                <Link to={to} onClick={() => setIsMenuOpen(false)}>
                                  <span className="sidebar-icon">{icon}</span>
                                  <span>{modulo.name}</span>
                                </Link>
                              </li>
                            )
                          })}
                      </React.Fragment>
                    ))
                )}

                {customLinks.length > 0 && (
                  <>
                    <li className="sidebar-divider">{t('dashboardPro.sectorTools')}</li>
                    {customLinks.map((link, i) => (
                      <li key={`mcl-${i}`}>
                        <a href={link.href} onClick={() => setIsMenuOpen(false)}>
                          {link.icon} {link.label}
                        </a>
                      </li>
                    ))}
                  </>
                )}
              </ul>
            </nav>
          </div>
          {isMenuOpen && <div className="mobile-drawer__overlay" onClick={() => setIsMenuOpen(false)} />}
        </>
      )}

      <main className="main-content">{children}</main>
    </div>
  )
}

export default DashboardPro
