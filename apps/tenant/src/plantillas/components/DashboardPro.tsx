/**
 * Dashboard Pro - Componente base reutilizable para todos los sectores
 * Acepta configuración específica de cada sector
 */
import React, { useState, useEffect, ReactNode } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useMisModulos } from '../../hooks/useMisModulos'
import { apiFetch } from '../../lib/http'

interface ThemeData {
  colors?: {
    primary?: string
    bg?: string
    surface?: string
    text?: string
    muted?: string
  }
}

interface DashboardProProps {
  sectorName: string
  sectorIcon: string
  children: ReactNode
  customLinks?: Array<{ label: string; href: string; icon: string }>
  darkModeDefault?: boolean
}

// Helper: Iconos por módulo
const getModuleIcon = (slug: string): string => {
  const icons: Record<string, string> = {
    'ventas': '📊',
    'clientes': '👥',
    'productos': '📦',
    'inventario': '📋',
    'facturacion': '🧾',
    'facturación': '🧾',
    'compras': '🛒',
    'proveedores': '🏭',
    'gastos': '💸',
    'finanzas': '💰',
    'contabilidad': '📚',
    'pos': '🏪',
    'tpv': '🏪',
    'imports': '📥',
    'rrhh': '👔',
    'configuracion': '⚙️',
    'configuración': '⚙️',
    'settings': '⚙️',
    'usuarios': '👤'
  }
  return icons[slug.toLowerCase()] || '📌'
}

const DashboardPro: React.FC<DashboardProProps> = ({
  sectorName,
  sectorIcon,
  children,
  customLinks = [],
  darkModeDefault = true
}) => {
  const { empresa } = useParams()
  const [theme, setTheme] = useState<ThemeData | null>(null)
  const [darkMode, setDarkMode] = useState(darkModeDefault)
  const { modules, loading: modulosLoading } = useMisModulos()

  // Cargar tema del tenant
  useEffect(() => {
    const loadTheme = async () => {
      try {
        const themeData = await apiFetch<ThemeData>(`/api/v1/tenant/settings/theme?empresa=${empresa}`)
        if (themeData?.colors) {
          setTheme(themeData)
          // Aplicar color primario a todo el tema
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
    <div className={`panaderia-app ${darkMode ? 'dark' : 'light'}`}>
      {/* Topbar */}
      <header className="topbar">
        <div className="brand">
          <div className="brand__logo" />
          <span>{sectorIcon} {sectorName}</span>
        </div>
        <div className="search">
          <input placeholder="Buscar (/) tickets, clientes, SKUs…" />
          <span>/</span>
        </div>
        <select>
          <option>Tienda Principal</option>
          <option>Sucursal 1</option>
          <option>Sucursal 2</option>
        </select>
        <input type="date" defaultValue={new Date().toISOString().split('T')[0]} />
        <button className="btn" onClick={toggleTheme}>
          {darkMode ? '☀️ Claro' : '🌙 Oscuro'}
        </button>
        <a className="btn btn--primary" href="#cierre">Cierre del día</a>
      </header>

      {/* Sidebar */}
      <aside className="sidebar">
        <nav>
          <ul>
            <li><Link to={`/${empresa}`} className="active">🏠 Dashboard</Link></li>

            {/* Módulos contratados */}
            {modulosLoading ? (
              <li className="sidebar-loading">Cargando módulos...</li>
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

            {/* Enlaces personalizados del sector */}
            {customLinks.length > 0 && (
              <>
                <li className="sidebar-divider">Gestión específica</li>
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
        <small>Atajos: / buscar • Cmd+K comandos</small>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        {children}
      </main>
    </div>
  )
}

export default DashboardPro
