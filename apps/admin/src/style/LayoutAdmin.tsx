import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

export interface LayoutProps {
  title?: string;
  children: React.ReactNode;
  empresaNombre?: string;
  logoUrl?: string;
  colorPrimario?: string;
  showBackButton?: boolean;
}

export const LayoutAdmin: React.FC<LayoutProps> = ({
  title = 'GestiqCloud',
  children,
  empresaNombre,
  logoUrl,
  colorPrimario = '#2563eb',
  showBackButton = true,
}) => {
  const navigate = useNavigate();
  const { profile, logout, brand } = useAuth();
  const isAdmin = !!profile?.is_superadmin;

  // Título del documento (sustituye a Helmet)
  useEffect(() => {
    if (title) document.title = title;
  }, [title]);

  const handleBack = () => {
    if (window.history.length > 1) {
      navigate(-1);
    } else {
      navigate('/'); // ruta segura en tu app
    }
  };

  const handleLogout = async () => {
    try {
      await logout();              // usa tu AuthContext (no borres localStorage a mano)
    } finally {
      navigate('/login', { replace: true });
    }
  };

  const primary = colorPrimario;
  const empresa = empresaNombre || brand || 'GestiqCloud';

  return (
    <div style={{ minHeight: '100vh', background: '#f6f7fb', color: '#111', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <header
        style={{
          background: '#fff',
          borderBottom: `2px solid ${primary}`,
          boxShadow: '0 2px 8px rgba(0,0,0,.04)',
        }}
      >
        <div style={{ maxWidth: 1200, margin: '0 auto', padding: '12px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            {logoUrl ? (
              <img src={logoUrl} alt={empresa} width={40} height={40} style={{ borderRadius: 999, background: '#f1f5f9', objectFit: 'cover' }} />
            ) : (
              <div style={{ width: 40, height: 40, borderRadius: 999, background: '#e2e8f0', display: 'grid', placeItems: 'center' }}>🌐</div>
            )}
            <span style={{ fontWeight: 800, fontSize: 18, color: primary }}>{empresa}</span>
          </div>

          <nav style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            {isAdmin && (
              <button
                onClick={() => navigate('/')}
                style={{
                  padding: '8px 12px',
                  borderRadius: 10,
                  background: '#fff',
                  border: '1px solid #cbd5e1',
                  fontWeight: 600,
                }}
              >
                Panel Admin
              </button>
            )}
            <button
              onClick={handleLogout}
              style={{
                padding: '8px 12px',
                borderRadius: 10,
                background: '#fff',
                border: '1px solid #fecaca',
                color: '#b91c1c',
                fontWeight: 600,
              }}
            >
              Cerrar sesión
            </button>
          </nav>
        </div>
      </header>

      {/* Contenido */}
      <main style={{ flex: 1, width: '100%', maxWidth: 1200, margin: '0 auto', padding: '24px 16px' }}>
        {showBackButton && (
          <button
            onClick={handleBack}
            style={{
              marginBottom: 16,
              background: 'transparent',
              border: 0,
              color: primary,
              textDecoration: 'underline',
              cursor: 'pointer',
            }}
          >
            ← Volver
          </button>
        )}

        {children}
      </main>

      {/* Footer */}
      <footer style={{ textAlign: 'center', fontSize: 12, color: '#64748b', padding: '24px 12px' }}>
        &copy; {new Date().getFullYear()} GestiqCloud. Todos los derechos reservados.
      </footer>
    </div>
  );
};
