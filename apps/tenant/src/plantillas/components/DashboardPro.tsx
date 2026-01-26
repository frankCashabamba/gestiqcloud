/**
 * Dashboard Pro - reusable base component for sector dashboards
 */
import React, { useState, useEffect, ReactNode } from 'react'
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

const DashboardPro: React.FC<DashboardProProps> = ({
  sectorName,
  sectorIcon,
  children,
  customLinks = [],
  darkModeDefault = true,
}) => {
  const { t } = useTranslation()
  const { empresa } = useParams()
  const [theme, setTheme] = useState<ThemeResponse | null>(null)
  const [darkMode, setDarkMode] = useState(darkModeDefault)
  const { modules, loading: modulosLoading } = useMisModulos()

  useEffect(() => {
    const loadTheme = async () => {
      try {
        const themeData = await fetchCompanyTheme(empresa)
        if (themeData?.colors) {
          setTheme(themeData)
          const primaryColor = themeData.colors.primary || '#5B8CFF'
          document.documentElement.style.setProperty('--primary', primaryColor)
          document.documentElement.style.setProperty('--topbar-bg', primaryColor)
          document.documentElement.style.setProperty('--sidebar-active', primaryColor)
          document.documentElement.style.setProperty('--btn-primary', primaryColor)
        }
      } catch (err) {
        console.error('Error loading theme:', err)
      }
    }
    loadTheme()
  }, [empresa])

  const toggleTheme = () => {
    setDarkMode(!darkMode)
    document.documentElement.classList.toggle('light-theme')
  }

  return (
    <div className={`dashboard-pro-app ${darkMode ? 'dark' : 'light'}`}>
      <header className="topbar">
        <div className="brand">
          <div className="brand__logo" />
          <span>
            {sectorIcon} {sectorName}
          </span>
        </div>
        <div className="search">
          <input placeholder={t('dashboardPro.searchPlaceholder')} />
          <span>/</span>
        </div>
        <select>
          <option>{t('dashboardPro.stores.main')}</option>
          <option>{t('dashboardPro.stores.branch', { n: 1 })}</option>
          <option>{t('dashboardPro.stores.branch', { n: 2 })}</option>
        </select>
        <input type="date" defaultValue={new Date().toISOString().split('T')[0]} />
        <button className="btn" onClick={toggleTheme}>
          {darkMode ? t('dashboardPro.lightMode') : t('dashboardPro.darkMode')}
        </button>
        <a className="btn btn--primary" href="#close-day">
          {t('dashboardPro.closeDay')}
        </a>
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
              modules
                .sort((a, b) => (a.name || '').localeCompare(b.name || ''))
                .map((modulo) => {
                  const slug = modulo.slug || (modulo.name || '').toLowerCase()
                  const icon = getModuleIcon(slug)
                  const to = `/${empresa}/${slug}`
                  return (
                    <li key={modulo.id}>
                      <Link to={to}>
                        {icon} {modulo.name}
                      </Link>
                    </li>
                  )
                })
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

      <main className="main-content">{children}</main>
    </div>
  )
}

export default DashboardPro
