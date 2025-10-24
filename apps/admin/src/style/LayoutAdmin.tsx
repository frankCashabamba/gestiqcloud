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

  const primary = colorPrimario
  const empresa = empresaNombre || brand || 'GestiqCloud'

  return (
    <div style={{ minHeight: '100vh', background: '#f6f7fb', color: '#0f172a', display: 'flex', flexDirection: 'column' }}>
      <header style={{ background: '#ffffff', borderBottom: `1px solid ${primary}22`, boxShadow: '0 6px 24px rgba(15, 23, 42, 0.06)' }}>
        <div style={{ maxWidth: 1200, margin: '0 auto', padding: '12px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            {logoUrl ? (
              <img src={logoUrl} alt={empresa} width={40} height={40} style={{ borderRadius: 8, background: '#f1f5f9', objectFit: 'cover' }} />
            ) : (
              <div style={{ width: 40, height: 40, borderRadius: 8, background: '#e2e8f0', display: 'grid', placeItems: 'center', color: '#334155', fontWeight: 700 }}>GC</div>
            )}
            <span style={{ fontWeight: 800, fontSize: 18, color: primary }}>{empresa}</span>
          </div>

          <nav style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            {isAdmin && (
              <Link
                to="/admin"
                style={{ padding: '8px 14px', borderRadius: 10, background: '#ffffff', border: '1px solid #cbd5e1', fontWeight: 700, color: '#0f172a', textDecoration: 'none', boxShadow: '0 1px 2px rgba(15, 23, 42, 0.04)' }}
                title="Ir al panel principal"
              >
                Panel Admin
              </Link>
            )}
            <button
              onClick={handleLogout}
              style={{ padding: '8px 14px', borderRadius: 10, background: '#ffffff', border: '1px solid #fecaca', color: '#b91c1c', fontWeight: 700, boxShadow: '0 1px 2px rgba(185, 28, 28, 0.08)' }}
            >
              Cerrar sesión
            </button>
          </nav>
        </div>
      </header>

      <main style={{ flex: 1, width: '100%', maxWidth: 1200, margin: '0 auto', padding: '24px 16px' }}>
        {showBackButton && (
          <button onClick={handleBack} style={{ marginBottom: 16, background: 'transparent', border: 0, color: primary, textDecoration: 'underline', cursor: 'pointer' }}>
            ← Volver
          </button>
        )}
        {children}
      </main>

      <footer style={{ textAlign: 'center', fontSize: 12, color: '#64748b', padding: '24px 12px' }}>
        © {new Date().getFullYear()} GestiqCloud. Todos los derechos reservados.
      </footer>
    </div>
  )
}
