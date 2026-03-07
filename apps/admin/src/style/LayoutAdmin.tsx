import React from 'react'

import { useNavigate, Link } from 'react-router-dom'

import { useAuth } from '../auth/AuthContext'

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
    <div className="admin-shell-root">
      <header className="admin-topbar">
        <div className="admin-topbar__inner">
          <div className="admin-topbar__brand">
            {logoUrl ? (
              <img
                src={logoUrl}
                alt={empresa}
                className="admin-topbar__logo admin-topbar__logo--img"
              />
            ) : (
              <div className="admin-topbar__logo">GC</div>
            )}
            <div className="admin-topbar__brand-text">
              <span className="admin-topbar__brand-name">{empresa}</span>
              <span className="admin-topbar__brand-sub">Admin Panel</span>
            </div>
          </div>

          <nav className="admin-topbar__nav">
            {isAdmin && (
              <Link to="/admin" className="admin-topbar__btn">
                Panel Admin
              </Link>
            )}
            <button onClick={handleLogout} className="admin-topbar__btn admin-topbar__btn--logout">
              Cerrar sesión
            </button>
          </nav>
        </div>
      </header>

      <main className="admin-main-content">
        {showBackButton && (
          <button onClick={handleBack} className="admin-back-btn">
            ← Volver
          </button>
        )}
        {children}
      </main>

      <footer className="admin-footer">
        © {new Date().getFullYear()} GestiqCloud. Todos los derechos reservados.
      </footer>
    </div>
  )
}
