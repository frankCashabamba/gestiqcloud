/**
 * ExpiryWarnings
 *
 * Component that displays alerts for products nearing expiration
 * Only visible if features.inventory_expiry_tracking === true
 */
import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
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
  /** Days in advance for the alert (default: 3) */
  warningDays?: number
  /** Maximum products to display (default: 5) */
  maxItems?: number
  /** Callback when a product is clicked */
  onProductClick?: (productId: string) => void
}

export function ExpiryWarnings({
  warningDays = 3,
  maxItems = 5,
  onProductClick
}: ExpiryWarningsProps) {
  const features = useCompanyFeatures()
  useCompanySector()

  const [products, setProducts] = useState<ExpiringProduct[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [collapsed, setCollapsed] = useState(false)

  useEffect(() => {
    if (!features.inventory_expiry_tracking) return
    loadExpiringProducts()
  }, [features.inventory_expiry_tracking, warningDays, maxItems])

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
      setError(err.message || 'Error loading expiring products')
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
    if (days === 0) return 'TODAY!'
    if (days === 1) return 'Tomorrow'
    return `${days} days`
  }

  // Only render if feature is enabled
  if (!features.inventory_expiry_tracking) {
    return null
  }

  if (loading) {
    return (
      <div className="expiry-warnings loading" role="status" aria-label="Loading expiry alerts">
        <div className="loading-spinner"></div>
        <span>Checking expiration dates...</span>
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
          aria-label="Retry loading"
        >
          Retry
        </button>
      </div>
    )
  }

  if (products.length === 0) {
    return null // Don't show anything if no products are nearing expiration
  }

  return (
    <div className="expiry-warnings" role="region" aria-label="Products nearing expiration">
      {/* Header */}
      <div className="warnings-header" onClick={() => setCollapsed(!collapsed)}>
        <div className="header-left">
          <span className="icon" aria-hidden="true">
            📦
          </span>
          <h3 className="title">
            Products Nearing Expiration
            <span className="count-badge" aria-label={`${products.length} products`}>
              {products.length}
            </span>
          </h3>
        </div>
        <button
          className="collapse-btn"
          aria-label={collapsed ? 'Expand' : 'Collapse'}
          aria-expanded={!collapsed}
        >
          {collapsed ? '▼' : '▲'}
        </button>
      </div>

      {/* Product list */}
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
                aria-label={`${product.name} - Expires in ${urgencyLabel}`}
              >
                <div className="item-left">
                  <div className="urgency-badge" aria-label={`Urgency: ${urgency}`}>
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
                   <div className="qty-badge" aria-label={`Quantity: ${product.qty_on_hand}`}>
                     {product.qty_on_hand} units
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

          {/* View all button */}
          {products.length === maxItems && (
            <button
              className="view-all-btn"
              onClick={() => window.location.href = '/inventory/expiring'}
              aria-label="View all products nearing expiration"
            >
              View all products nearing expiration →
            </button>
          )}
        </div>
      )}

      <style>{`
        .expiry-warnings {
          background: var(--gc-surface);
          border: 2px solid var(--gc-warning);
          border-radius: 12px;
          overflow: hidden;
          box-shadow: 0 2px 8px color-mix(in srgb, var(--gc-warning) 15%, transparent);
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
          border-color: var(--gc-danger);
          background: color-mix(in srgb, var(--gc-danger) 8%, white);
        }

        .loading-spinner {
          width: 20px;
          height: 20px;
          border: 2px solid var(--gc-warning);
          border-top-color: transparent;
          border-radius: 50%;
          animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
          to { transform: rotate(360deg); }
        }

        .retry-btn {
          padding: 4px 12px;
          background: var(--gc-danger);
          color: white;
          border: none;
          border-radius: 6px;
          cursor: pointer;
          font-size: 13px;
          font-weight: 600;
        }

        .retry-btn:hover {
          background: color-mix(in srgb, var(--gc-danger) 85%, black);
        }

        /* Header */
        .warnings-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 14px 16px;
          background: color-mix(in srgb, var(--gc-warning) 6%, white);
          border-bottom: 1px solid var(--gc-warning);
          cursor: pointer;
          user-select: none;
        }

        .warnings-header:hover {
          background: color-mix(in srgb, var(--gc-warning) 15%, white);
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
          background: var(--gc-warning);
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
          background: color-mix(in srgb, var(--gc-danger) 10%, white);
          border-left: 4px solid var(--gc-danger);
        }

        .urgency-warning {
          background: color-mix(in srgb, var(--gc-warning) 15%, white);
          border-left: 4px solid var(--gc-warning);
        }

        .urgency-info {
          background: color-mix(in srgb, var(--gc-primary) 8%, white);
          border-left: 4px solid var(--gc-primary);
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
          background: var(--gc-danger);
          color: white;
        }

        .urgency-warning .urgency-badge {
          background: var(--gc-warning);
          color: white;
        }

        .urgency-info .urgency-badge {
          background: var(--gc-primary);
          color: white;
        }

        .item-info {
          flex: 1;
        }

        .product-name {
          font-size: 14px;
          font-weight: 600;
          color: var(--gc-foreground);
          margin-bottom: 2px;
        }

        .product-meta {
          font-size: 12px;
          color: var(--gc-muted);
          display: flex;
          align-items: center;
          gap: 6px;
        }

        .separator {
          color: var(--gc-border);
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
          color: var(--gc-foreground);
        }

        .expiry-date {
          font-size: 12px;
          color: var(--gc-muted);
        }

        .view-all-btn {
          width: 100%;
          padding: 10px;
          margin-top: 8px;
          background: var(--gc-bg);
          border: 1px dashed var(--gc-border);
          border-radius: 6px;
          color: var(--gc-muted);
          font-size: 13px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s;
        }

        .view-all-btn:hover {
          background: var(--gc-border);
          border-color: var(--gc-muted);
          color: var(--gc-foreground);
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
