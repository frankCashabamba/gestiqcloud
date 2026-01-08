/**
 * ExpiryWarnings
 *
 * Componente que muestra alertas de productos próximos a caducar
 * Solo visible si features.inventory_expiry_tracking === true
 */
import React, { useEffect, useState } from 'react'
import { useCompanyFeatures, useCompanySector } from '../contexts/CompanyConfigContext'
import { apiFetch } from '../lib/http'

interface ExpiringProduct {
  id: string
  name: string
  sku: string
  expires_at: string
  days_until_expiry: number
  qty_on_hand: number
  location?: string
}

interface ExpiryWarningsProps {
  /** Días de anticipación para la alerta (default: 3) */
  warningDays?: number
  /** Máximo de productos a mostrar (default: 5) */
  maxItems?: number
  /** Callback cuando se hace click en un producto */
  onProductClick?: (productId: string) => void
}

export function ExpiryWarnings({
  warningDays = 3,
  maxItems = 5,
  onProductClick
}: ExpiryWarningsProps) {
  const features = useCompanyFeatures()
  const sector = useCompanySector()

  const [products, setProducts] = useState<ExpiringProduct[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [collapsed, setCollapsed] = useState(false)

  // Solo cargar si el feature está habilitado
  if (!features.inventory_expiry_tracking) {
    return null
  }

  useEffect(() => {
    loadExpiringProducts()
  }, [warningDays])

  const loadExpiringProducts = async () => {
    try {
      setLoading(true)
      setError(null)

      const response = await apiFetch(
        `/api/v1/inventory/expiring-soon?days=${warningDays}&limit=${maxItems}`
      ) as { items?: any[] }

      setProducts(response.items || [])
    } catch (err: any) {
      console.error('Error loading expiring products:', err)
      setError(err.message || 'Error cargando productos próximos a caducar')
    } finally {
      setLoading(false)
    }
  }

  const getUrgencyLevel = (days: number): 'critical' | 'warning' | 'info' => {
    if (days <= 1) return 'critical'
    if (days <= 2) return 'warning'
    return 'info'
  }

  const getUrgencyLabel = (days: number): string => {
    if (days === 0) return '¡HOY!'
    if (days === 1) return 'Mañana'
    return `${days} días`
  }

  if (loading) {
    return (
      <div className="expiry-warnings loading" role="status" aria-label="Cargando alertas de caducidad">
        <div className="loading-spinner"></div>
        <span>Verificando fechas de caducidad...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="expiry-warnings error" role="alert">
        <span className="icon">⚠️</span>
        <span>{error}</span>
        <button
          onClick={loadExpiringProducts}
          className="retry-btn"
          aria-label="Reintentar carga"
        >
          Reintentar
        </button>
      </div>
    )
  }

  if (products.length === 0) {
    return null // No mostrar nada si no hay productos próximos a caducar
  }

  return (
    <div className="expiry-warnings" role="region" aria-label="Productos próximos a caducar">
      {/* Header */}
      <div className="warnings-header" onClick={() => setCollapsed(!collapsed)}>
        <div className="header-left">
          <span className="icon" aria-hidden="true">
            📦
          </span>
          <h3 className="title">
            Productos Próximos a Caducar
            <span className="count-badge" aria-label={`${products.length} productos`}>
              {products.length}
            </span>
          </h3>
        </div>
        <button
          className="collapse-btn"
          aria-label={collapsed ? 'Expandir' : 'Contraer'}
          aria-expanded={!collapsed}
        >
          {collapsed ? '▼' : '▲'}
        </button>
      </div>

      {/* Lista de productos */}
      {!collapsed && (
        <div className="warnings-list">
          {products.map((product) => {
            const urgency = getUrgencyLevel(product.days_until_expiry)
            const urgencyLabel = getUrgencyLabel(product.days_until_expiry)

            return (
              <div
                key={product.id}
                className={`warning-item urgency-${urgency}`}
                onClick={() => onProductClick?.(product.id)}
                role="button"
                tabIndex={0}
                aria-label={`${product.name} - Caduca en ${urgencyLabel}`}
              >
                <div className="item-left">
                  <div className="urgency-badge" aria-label={`Urgencia: ${urgency}`}>
                    {urgencyLabel}
                  </div>
                  <div className="item-info">
                    <div className="product-name">{product.name}</div>
                    <div className="product-meta">
                      <span className="sku">{product.sku}</span>
                      {product.location && (
                        <>
                          <span className="separator">•</span>
                          <span className="location">📍 {product.location}</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                <div className="item-right">
                   <div className="qty-badge" aria-label={`Cantidad: ${product.qty_on_hand}`}>
                     {product.qty_on_hand} unidades
                   </div>
                  <div className="expiry-date">
                    {new Date(product.expires_at).toLocaleDateString('es-ES', {
                      day: '2-digit',
                      month: 'short'
                    })}
                  </div>
                </div>
              </div>
            )
          })}

          {/* Botón ver todos */}
          {products.length === maxItems && (
            <button
              className="view-all-btn"
              onClick={() => window.location.href = '/inventory/expiring'}
              aria-label="Ver todos los productos próximos a caducar"
            >
              Ver todos los productos próximos a caducar →
            </button>
          )}
        </div>
      )}

      <style>{`
        .expiry-warnings {
          background: #fff;
          border: 2px solid #fbbf24;
          border-radius: 12px;
          overflow: hidden;
          box-shadow: 0 2px 8px rgba(251, 191, 36, 0.15);
        }

        .expiry-warnings.loading,
        .expiry-warnings.error {
          padding: 16px;
          display: flex;
          align-items: center;
          gap: 12px;
          justify-content: center;
        }

        .expiry-warnings.error {
          border-color: #ef4444;
          background: #fef2f2;
        }

        .loading-spinner {
          width: 20px;
          height: 20px;
          border: 2px solid #fbbf24;
          border-top-color: transparent;
          border-radius: 50%;
          animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
          to { transform: rotate(360deg); }
        }

        .retry-btn {
          padding: 4px 12px;
          background: #ef4444;
          color: white;
          border: none;
          border-radius: 6px;
          cursor: pointer;
          font-size: 13px;
          font-weight: 600;
        }

        .retry-btn:hover {
          background: #dc2626;
        }

        /* Header */
        .warnings-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 14px 16px;
          background: #fffbeb;
          border-bottom: 1px solid #fbbf24;
          cursor: pointer;
          user-select: none;
        }

        .warnings-header:hover {
          background: #fef3c7;
        }

        .header-left {
          display: flex;
          align-items: center;
          gap: 10px;
        }

        .icon {
          font-size: 20px;
          line-height: 1;
        }

        .title {
          font-size: 15px;
          font-weight: 700;
          color: #92400e;
          margin: 0;
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .count-badge {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          min-width: 24px;
          height: 24px;
          padding: 0 6px;
          background: #f59e0b;
          color: white;
          border-radius: 12px;
          font-size: 12px;
          font-weight: 700;
        }

        .collapse-btn {
          background: none;
          border: none;
          font-size: 12px;
          color: #92400e;
          cursor: pointer;
          padding: 4px 8px;
          transition: transform 0.2s;
        }

        .collapse-btn:hover {
          transform: scale(1.2);
        }

        /* Lista */
        .warnings-list {
          padding: 8px;
        }

        .warning-item {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 12px;
          margin-bottom: 8px;
          border-radius: 8px;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .warning-item:last-child {
          margin-bottom: 0;
        }

        .warning-item:hover {
          transform: translateX(4px);
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }

        /* Niveles de urgencia */
        .urgency-critical {
          background: #fee2e2;
          border-left: 4px solid #dc2626;
        }

        .urgency-warning {
          background: #fef3c7;
          border-left: 4px solid #f59e0b;
        }

        .urgency-info {
          background: #e0f2fe;
          border-left: 4px solid #0ea5e9;
        }

        .item-left {
          display: flex;
          align-items: center;
          gap: 12px;
          flex: 1;
        }

        .urgency-badge {
          font-size: 11px;
          font-weight: 700;
          text-transform: uppercase;
          padding: 4px 8px;
          border-radius: 6px;
          white-space: nowrap;
        }

        .urgency-critical .urgency-badge {
          background: #dc2626;
          color: white;
        }

        .urgency-warning .urgency-badge {
          background: #f59e0b;
          color: white;
        }

        .urgency-info .urgency-badge {
          background: #0ea5e9;
          color: white;
        }

        .item-info {
          flex: 1;
        }

        .product-name {
          font-size: 14px;
          font-weight: 600;
          color: #1f2937;
          margin-bottom: 2px;
        }

        .product-meta {
          font-size: 12px;
          color: #6b7280;
          display: flex;
          align-items: center;
          gap: 6px;
        }

        .separator {
          color: #d1d5db;
        }

        .item-right {
          display: flex;
          flex-direction: column;
          align-items: flex-end;
          gap: 4px;
        }

        .qty-badge {
          font-size: 13px;
          font-weight: 600;
          color: #374151;
        }

        .expiry-date {
          font-size: 12px;
          color: #6b7280;
        }

        .view-all-btn {
          width: 100%;
          padding: 10px;
          margin-top: 8px;
          background: #f3f4f6;
          border: 1px dashed #d1d5db;
          border-radius: 6px;
          color: #4b5563;
          font-size: 13px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s;
        }

        .view-all-btn:hover {
          background: #e5e7eb;
          border-color: #9ca3af;
          color: #1f2937;
        }

        /* Responsive */
        @media (max-width: 640px) {
          .warnings-header {
            padding: 12px;
          }

          .title {
            font-size: 14px;
          }

          .warning-item {
            flex-direction: column;
            align-items: flex-start;
            gap: 8px;
          }

          .item-right {
            flex-direction: row;
            width: 100%;
            justify-content: space-between;
          }
        }
      `}</style>
    </div>
  )
}

export default ExpiryWarnings
