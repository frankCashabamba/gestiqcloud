import React from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { env } from '../env'

export interface LayoutProps {
  title?: string
  children: React.ReactNode
  empresaNombre?: string
  logoUrl?: string
  colorPrimario?: string
  showBackButton?: boolean
}

export const LayoutAdmin: React.FC<LayoutProps> = ({
  title = 'GestiqCloud',
  children,
  empresaNombre,
  logoUrl,
  colorPrimario = '#2563eb',
  showBackButton = true,
}) => {
  const navigate = useNavigate()
  const { profile, logout, brand } = useAuth()
  const isAdmin = !!profile?.is_superadmin

  React.useEffect(() => {
    if (title) document.title = title
  }, [title])

  const handleBack = () => {
    if (window.history.length > 1) navigate(-1)
    else navigate('/')
  }

  const handleLogout = async () => {
    try { await logout() } finally { navigate('/login', { replace: true }) }
  }

  const empresa = empresaNombre || brand || 'GestiqCloud'

  return (
    <div style={{ minHeight: '100vh', background: '#f6f7fb', color: '#0f172a', display: 'flex', flexDirection: 'column' }}>
      <header className="admin-header">
        <div className="admin-header__inner">
          <div className="admin-brand-wrap">
            <div className="admin-brand">
              {logoUrl ? (
                <img src={logoUrl} alt={empresa} width={40} height={40} style={{ borderRadius: 10, background: '#f1f5f9', objectFit: 'cover' }} />
              ) : (
                <div className="admin-logo">GC</div>
              )}
              <div className="admin-brand__text">
                <span className="admin-brand__name" style={{ color: colorPrimario }}>{empresa}</span>
                <span className="admin-brand__sub">Panel administrativo</span>
              </div>
            </div>
          </div>

          <div className="admin-nav-wrap">
            <nav className="admin-nav">
              {isAdmin && (
                <Link
                  to="/admin"
                  className="admin-btn"
                  title="Ir al panel principal"
                >
                  Panel Admin
                </Link>
              )}
              <button
                onClick={handleLogout}
                className="admin-btn logout"
              >
                Cerrar sesion
              </button>
            </nav>
          </div>
        </div>
      </header>

      <main className="admin-main">
        {showBackButton && (
          <button
            onClick={handleBack}
            className="admin-back"
            style={{ color: colorPrimario }}
          >
            Volver
          </button>
        )}
        {children}
      </main>

      <footer className="admin-footer">
        {new Date().getFullYear()} GestiqCloud. Todos los derechos reservados.
      </footer>
    </div>
  )
}
