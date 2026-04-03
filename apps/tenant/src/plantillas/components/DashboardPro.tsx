/**
 * Dashboard Pro - reusable base component for sector dashboards
 */
import React, { useState, useEffect, useRef, ReactNode, useMemo } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useMisModulos } from '../../hooks/useMisModulos'
import { usePermission } from '../../hooks/usePermission'
import { fetchCompanyTheme, type ThemeResponse } from '../../services/theme'
import tenantApi from '../../shared/api/client'

interface DashboardProProps {
  sectorName: string
  sectorIcon: string
  children: ReactNode
  customLinks?: Array<{ label: string; href: string; icon: string }>
  darkModeDefault?: boolean
  hideSidebar?: boolean
}

const getModuleIcon = (slug: string): string => {
  const nrm = (v: string) =>
    v.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/\s+/g, '')

  const icons: Record<string, string> = {
    ventas: '💰', sales: '💰',
    clientes: '👤', clients: '👤', customers: '👤',
    products: '📦', productos: '📦',
    inventario: '🗄️', inventory: '🗄️',
    facturacion: '🧾', invoicing: '🧾', billing: '🧾', facturacion_es: '🧾',
    facturaelectronica: '🧾', factura: '🧾',
    compras: '🛒', purchases: '🛒',
    proveedores: '🏭', suppliers: '🏭',
    gastos: '💸', expenses: '💸',
    finanzas: '📊', finance: '📊', finances: '📊',
    contabilidad: '📚', accounting: '📚',
    pos: '🖥️', tpv: '🖥️', puntodventa: '🖥️', puntoventa: '🖥️',
    rrhh: '👥', hr: '👥',
    configuracion: '⚙️', settings: '⚙️', configuration: '⚙️', config: '⚙️',
    usuarios: '🔐', users: '🔐', user: '🔐', useradmin: '🔐',
    reconciliation: '🏦', conciliacion: '🏦', conciliacionbancaria: '🏦',
    produccion: '🏗️', production: '🏗️',
    recetas: '📋', recipes: '📋',
    restaurant: '🍽️', restaurante: '🍽️',
    crm: '🤝',
    notifications: '🔔', notificaciones: '🔔',
    templates: '📄', webhooks: '🔗',
    imports: '📥', importaciones: '📥',
    reports: '📈', reportes: '📈',
  }

  return icons[nrm(slug)] || '🔷'
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

// ── Clasificación de módulos ──────────────────────────────────────────────────

const nrm = (v: string) =>
  v.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/\s+/g, '')

/** Nunca se muestran en la UI */
const HIDDEN_SLUGS = new Set([
  'templates', 'webhooks', 'reports',
])

/** Van al menú de usuario del topbar, no al sidebar */
const SETTINGS_SLUGS = new Set([
  'configuracion', 'settings', 'configuration', 'config',
  'usuarios', 'users', 'user', 'useradmin',
])
const SETTINGS_NAMES = new Set([
  'configuracion', 'configuración', 'settings', 'configuration',
  'usuarios', 'users', 'gestiondeusuarios', 'usermanagement',
  'ajustes', 'parametros', 'parametrización',
])
/** Filtra por slug O nombre normalizado */
const isSettingsModule = (m: any) =>
  SETTINGS_SLUGS.has(nrm(m.slug || '')) || SETTINGS_NAMES.has(nrm(m.name || ''))

/** Back-office: módulos financieros — sección colapsable al fondo del sidebar */
const BACKOFFICE_SLUGS = new Set([
  'facturacion', 'invoicing', 'billing', 'facturacion_es',
  'finanzas', 'finance', 'finances',
  'contabilidad', 'accounting',
  'conciliacion', 'reconciliation', 'conciliacionbancaria',
  'rrhh', 'hr',
  'imports', 'importer', 'importaciones',
])

// ─────────────────────────────────────────────────────────────────────────────

const DashboardPro: React.FC<DashboardProProps> = ({
  sectorName,
  sectorIcon,
  children,
  customLinks = [],
  darkModeDefault = false,
  hideSidebar = false,
}) => {
  const { t } = useTranslation()
  const can = usePermission()
  const { empresa } = useParams()
  const [_theme, setTheme] = useState<ThemeResponse | null>(null)
  const [darkMode, setDarkMode] = useState(darkModeDefault)
  const [branches, setBranches] = useState<Array<{ id: string; name: string; is_main: boolean }>>([])
  const [selectedBranch, setSelectedBranch] = useState<string>('')
  const {
    sidebarModules,
    backofficeModules,
    userMenuModules,
    loading: modulosLoading,
  } = useMisModulos()
  const [isMobileView, setIsMobileView] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false
    return window.innerWidth <= 1024
  })
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const [moduleSearch, setModuleSearch] = useState('')
  const userMenuRef = useRef<HTMLDivElement>(null)

  // Cierra el menú de usuario al hacer clic fuera
  useEffect(() => {
    if (!userMenuOpen) return
    const handleClick = (e: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setUserMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [userMenuOpen])

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
        document.documentElement.classList.add('light-theme')
      } catch (err) {
        console.error('Error loading theme:', err)
      }
    }
    loadTheme()
  }, [empresa])

  useEffect(() => {
    tenantApi.get('/api/v1/tenant/branches')
      .then(r => {
        const data: Array<{ id: string; name: string; is_main: boolean }> = r.data
        setBranches(data)
        const main = data.find(b => b.is_main)
        if (main) setSelectedBranch(main.id)
        else if (data.length > 0) setSelectedBranch(data[0].id)
      })
      .catch(() => { /* silencioso: no bloquear el dashboard */ })
  }, [])

  useEffect(() => {
    const handleResize = () => setIsMobileView(window.innerWidth <= 1024)
    handleResize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  const settingsModules = useMemo(() => {
    const items = [...userMenuModules]
    const hasSettingsEntry = items.some((modulo) => nrm(modulo.slug || modulo.name || '') === 'settings')
    if (can('settings:read') && !hasSettingsEntry) {
      items.unshift({
        id: 'settings-shortcut',
        name: t('nav.settings'),
        slug: 'settings',
        active: true,
        nav_group: 'user_menu',
      } as any)
    }
    return items
  }, [can, t, userMenuModules])

  const filteredModules = useMemo(() => {
    const term = moduleSearch.trim().toLowerCase()
    const visible = [...sidebarModules, ...backofficeModules]
    if (!term) return visible
    return visible.filter((m) =>
      (m.name || '').toLowerCase().includes(term) || (m.slug || '').toLowerCase().includes(term)
    )
  }, [sidebarModules, backofficeModules, moduleSearch])

  const primaryModules = useMemo(
    () => filteredModules.filter((m) => (m.nav_group || 'sidebar') === 'sidebar'),
    [filteredModules]
  )

  const backOfficeModules = useMemo(
    () => filteredModules.filter((m) => m.nav_group === 'backoffice'),
    [filteredModules]
  )

  // Agrupa por categoría, ignorando categorías de tipo admin/settings que se filaron de la DB
  const SETTINGS_CATEGORIES = new Set([
    'configuracion', 'configuración', 'settings', 'back office', 'backoffice',
    'admin', 'administracion', 'administración',
  ])

  const groupedModules = useMemo(() => {
    return primaryModules.reduce((acc: Record<string, typeof primaryModules>, modulo: any) => {
      const rawCat = (modulo.categoria || modulo.category || 'General').toString()
      // Si la categoría es de tipo settings, se ignoró el módulo en el paso anterior;
      // pero por si acaso, los reagrupamos en General
      const category = SETTINGS_CATEGORIES.has(nrm(rawCat)) ? 'General' : rawCat
      if (!acc[category]) acc[category] = []
      acc[category].push(modulo)
      return acc
    }, {})
  }, [primaryModules])

  const toggleTheme = () => {
    setDarkMode((prev) => {
      const next = !prev
      document.documentElement.classList.toggle('dark-theme', next)
      if (!next) document.documentElement.classList.add('light-theme')
      else document.documentElement.classList.remove('light-theme')
      return next
    })
  }

  const renderNavModules = (onLinkClick?: () => void) => (
    <>
      {modulosLoading ? (
        <li className="sidebar-loading">{t('dashboardPro.loadingModules')}</li>
      ) : (
        Object.entries(groupedModules)
          .sort(([a], [b]) => a.localeCompare(b))
          .map(([categoria, mods]) => (
            <React.Fragment key={categoria}>
              {categoria !== 'General' && (
                <li className="sidebar-divider">{categoria}</li>
              )}
              {mods
                .sort((a, b) => (a.name || '').localeCompare(b.name || ''))
                .map((modulo) => {
                  const slug = modulo.slug || (modulo.name || '').toLowerCase()
                  const icon = getModuleIcon(slug)
                  const to = `/${empresa}/${slug}`
                  return (
                    <li key={modulo.id}>
                      <Link to={to} onClick={onLinkClick}>
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
              <a href={link.href} onClick={onLinkClick}>
                {link.icon} {link.label}
              </a>
            </li>
          ))}
        </>
      )}
    </>
  )

  return (
    <div className={`dashboard-pro-app ${darkMode ? 'dark' : 'light'}${hideSidebar ? ' dashboard-pro-app--no-sidebar' : ''}`}>

      {/* ── Topbar ── */}
      <header className="topbar">
        {isMobileView && !hideSidebar && (
          <button className="icon-btn" onClick={() => setIsMenuOpen(true)} aria-label={t('dashboardPro.openMenu')}>
            <span className="menu-bars" aria-hidden />
          </button>
        )}

        <div className="brand">
          <div className="brand__logo" />
          <span>{sectorIcon} {sectorName}</span>
        </div>

        <div className="search">
          <input placeholder="Buscar productos, clientes o documentos" aria-label="Buscar en el dashboard" />
          <span>/</span>
        </div>

        <div className="topbar-right">
          {branches.length > 0 && (
            <select
              aria-label="Seleccionar sucursal"
              value={selectedBranch}
              onChange={e => setSelectedBranch(e.target.value)}
            >
              {branches.map(b => (
                <option key={b.id} value={b.id}>{b.name}</option>
              ))}
            </select>
          )}

          {/* Menú de usuario — configuración, tema */}
          <div className="user-menu" ref={userMenuRef}>
            <button
              className="user-menu__trigger"
              onClick={() => setUserMenuOpen((v) => !v)}
              aria-label="Opciones de usuario"
              aria-expanded={userMenuOpen}
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                <circle cx="12" cy="7" r="4"/>
              </svg>
            </button>

            {userMenuOpen && (
              <div className="user-menu__dropdown">
                {settingsModules.length > 0 && (
                  <>
                    {settingsModules.map((modulo) => {
                      const slug = modulo.slug || (modulo.name || '').toLowerCase()
                      return (
                        <Link
                          key={modulo.id}
                          to={`/${empresa}/${slug}`}
                          className="user-menu__item"
                          onClick={() => setUserMenuOpen(false)}
                        >
                          <span className="user-menu__item-icon">{getModuleIcon(slug)}</span>
                          {modulo.name}
                        </Link>
                      )
                    })}
                    <div className="user-menu__sep" />
                  </>
                )}
                <button className="user-menu__item" onClick={() => { toggleTheme(); setUserMenuOpen(false) }}>
                  <span className="user-menu__item-icon">{darkMode ? '☀️' : '🌙'}</span>
                  {darkMode ? t('dashboardPro.lightMode') : t('dashboardPro.darkMode')}
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* ── Sidebar ── */}
      {!hideSidebar && <aside className="sidebar">
        <nav>
          <ul>
            <li>
              <Link to={`/${empresa}`} className="active">
                <span className="sidebar-icon">🏠</span>
                <span>{t('nav.dashboard')}</span>
              </Link>
            </li>
            {renderNavModules()}
          </ul>
        </nav>

        {backOfficeModules.length > 0 && (
          <details className="sidebar-backoffice">
            <summary className="sidebar-backoffice__toggle">
              <span>Back office</span>
              <span className="sidebar-backoffice__count">{backOfficeModules.length}</span>
            </summary>
            <ul className="sidebar-backoffice__list">
              {backOfficeModules
                .sort((a, b) => (a.name || '').localeCompare(b.name || ''))
                .map((modulo) => {
                  const slug = modulo.slug || (modulo.name || '').toLowerCase()
                  return (
                    <li key={`bo-${modulo.id}`}>
                      <Link to={`/${empresa}/${slug}`}>
                        <span className="sidebar-icon">{getModuleIcon(slug)}</span>
                        <span>{modulo.name}</span>
                      </Link>
                    </li>
                  )
                })}
            </ul>
          </details>
        )}

        <div className="sidebar-hint">
          <small>{t('dashboardPro.shortcuts')}</small>
        </div>
      </aside>}

      {/* ── Mobile drawer ── */}
      {isMobileView && !hideSidebar && (
        <>
          <div className={`mobile-drawer ${isMenuOpen ? 'open' : ''}`}>
            <div className="mobile-drawer__header">
              <span className="brand-inline">
                <span className="brand__logo" />
                {sectorIcon} {sectorName}
              </span>
              <button className="icon-btn" onClick={() => setIsMenuOpen(false)} aria-label={t('dashboardPro.closeMenu')}>
                ✕
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
                    <span className="sidebar-icon">🏠</span>
                    <span>{t('nav.dashboard')}</span>
                  </Link>
                </li>
                {renderNavModules(() => setIsMenuOpen(false))}
              </ul>
            </nav>

            {backOfficeModules.length > 0 && (
              <div className="mobile-drawer__backoffice">
                <div className="mobile-drawer__backoffice-title">
                  Back office
                  <span className="sidebar-backoffice__count">{backOfficeModules.length}</span>
                </div>
                <nav>
                  <ul>
                    {backOfficeModules
                      .sort((a, b) => (a.name || '').localeCompare(b.name || ''))
                      .map((modulo) => {
                        const slug = modulo.slug || (modulo.name || '').toLowerCase()
                        return (
                          <li key={`mob-bo-${modulo.id}`}>
                            <Link to={`/${empresa}/${slug}`} onClick={() => setIsMenuOpen(false)}>
                              <span className="sidebar-icon">{getModuleIcon(slug)}</span>
                              <span>{modulo.name}</span>
                            </Link>
                          </li>
                        )
                      })}
                  </ul>
                </nav>
              </div>
            )}

            <div className="mobile-drawer__footer">
              {settingsModules.map((modulo) => {
                const slug = modulo.slug || (modulo.name || '').toLowerCase()
                return (
                  <Link
                    key={`ms-${modulo.id}`}
                    to={`/${empresa}/${slug}`}
                    className="mobile-drawer__footer-link"
                    onClick={() => setIsMenuOpen(false)}
                  >
                    <span>{getModuleIcon(slug)}</span>
                    {modulo.name}
                  </Link>
                )
              })}
              <button
                className="mobile-drawer__footer-link"
                onClick={() => { toggleTheme(); setIsMenuOpen(false) }}
              >
                <span>{darkMode ? '☀️' : '🌙'}</span>
                {darkMode ? t('dashboardPro.lightMode') : t('dashboardPro.darkMode')}
              </button>
            </div>
          </div>
          {isMenuOpen && <div className="mobile-drawer__overlay" onClick={() => setIsMenuOpen(false)} />}
        </>
      )}

      <main className="main-content">{children}</main>
    </div>
  )
}

export default DashboardPro
