/**
 * CatalogSection - Búsqueda + Categorías + Grilla de Productos
 * Componente reutilizable para la sección de catálogo
 */
import React, { RefObject } from 'react'
import { useTranslation } from 'react-i18next'
import ProtectedButton from '../../../components/ProtectedButton'
import { useCurrency } from '../../../hooks/useCurrency'
import type { Producto } from '../../products/types'

interface CatalogSectionProps {
  searchQuery: string
  setSearchQuery: (query: string) => void
  barcodeInput: string
  setBarcodeInput: (input: string) => void
  searchExpanded: boolean
  setSearchExpanded: React.Dispatch<React.SetStateAction<boolean>>
  selectedCategory: string
  setSelectedCategory: (category: string) => void
  viewMode: 'categories' | 'all'
  setViewMode: (mode: 'categories' | 'all') => void
  filteredProducts: Producto[]
  categories: string[]
  searchInputRef: RefObject<HTMLInputElement>
  onAddToCart: (product: Producto) => void
  onSearchEnter: (e: React.KeyboardEvent<HTMLInputElement>) => void
  onBarcodeEnter: (e: React.KeyboardEvent<HTMLInputElement>) => void
}

export function CatalogSection({
  searchQuery,
  setSearchQuery,
  barcodeInput,
  setBarcodeInput,
  searchExpanded,
  setSearchExpanded,
  selectedCategory,
  setSelectedCategory,
  viewMode,
  setViewMode,
  filteredProducts,
  categories,
  searchInputRef,
  onAddToCart,
  onSearchEnter,
  onBarcodeEnter,
}: CatalogSectionProps) {
  const { t } = useTranslation(['pos', 'common'])
  const { symbol: currencySymbol } = useCurrency()

  return (
    <section className="left">
      {/* Search */}
      <div
        className={`search ${searchExpanded ? 'search--expanded' : 'search--collapsed'}`}
        role="search"
      >
        <ProtectedButton
          permission="pos:read"
          className="btn sm ghost search-toggle"
          onClick={() => setSearchExpanded((prev) => !prev)}
          type="button"
        >
          {t('pos:search.button')}
        </ProtectedButton>
        <input
          ref={searchInputRef}
          id="search"
          autoFocus
          placeholder={t('pos:search.placeholder')}
          aria-label={t('pos:search.placeholder')}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onFocus={() => setSearchExpanded(true)}
          onBlur={() => {
            if (!searchQuery.trim()) setSearchExpanded(false)
          }}
          onKeyDown={(e) => {
            if (e.key === 'F2') {
              e.currentTarget.focus()
              return
            }
            onSearchEnter(e)
          }}
        />
        <input
          id="barcode"
          placeholder={t('pos:search.barcodeInput')}
          aria-label={t('pos:search.barcodeInput')}
          style={{ width: 140, borderLeft: '1px solid var(--pos-border)', paddingLeft: 8 }}
          value={barcodeInput}
          onChange={(e) => setBarcodeInput(e.target.value)}
          onKeyDown={onBarcodeEnter}
        />
        <ProtectedButton
          permission="pos:read"
          className="btn sm"
          onClick={() => {
            setSearchQuery('')
            setBarcodeInput('')
          }}
        >
          {t('common:clear')}
        </ProtectedButton>
        <div className="mode-inline" role="tablist" aria-label="Modo de vista">
          <ProtectedButton
            permission="pos:read"
            className={`btn sm ${viewMode === 'categories' ? 'primary' : 'ghost'}`}
            onClick={() => setViewMode('categories')}
          >
            {t('pos:view.byCategories')}
          </ProtectedButton>
          <ProtectedButton
            permission="pos:read"
            className={`btn sm ${viewMode === 'all' ? 'primary' : 'ghost'}`}
            onClick={() => setViewMode('all')}
          >
            {t('pos:view.all')}
          </ProtectedButton>
        </div>
      </div>

      {/* Categories - only visible in categories mode */}
      {viewMode === 'categories' && (
        <div className="cats" role="tablist" aria-label={t('pos:catalog.title')}>
          {categories.map((cat) => (
            <ProtectedButton
              permission="pos:read"
              key={cat}
              className={`cat ${selectedCategory === cat ? 'active' : ''}`}
              onClick={() => setSelectedCategory(cat)}
            >
              {cat === '*' ? t('pos:view.all') : cat}
            </ProtectedButton>
          ))}
        </div>
      )}
      {viewMode === 'all' && selectedCategory !== '*' && (
        <div className="active-filter-row">
          <span className="active-filter-chip">
            Categoria: {selectedCategory}
            <button
              type="button"
              className="active-filter-clear"
              onClick={() => setSelectedCategory('*')}
              aria-label="Limpiar filtro de categoria"
            >
              x
            </button>
          </span>
        </div>
      )}

      {/* Product Grid */}
      <div id="catalog" className="catalog" role="list" aria-label={t('pos:catalog.title')}>
        {filteredProducts.map((p) => (
          <ProtectedButton
            permission="pos:update"
            key={p.id}
            className="tile"
            role="listitem"
            title={p.sku || ''}
            onClick={() => onAddToCart(p)}
          >
            <strong>{p.name}</strong>
            <small>
              {p.price?.toFixed(2) || '0.00'}
              {currencySymbol}
            </small>
            {p.product_metadata?.tags && (
              <div className="tags">
                {p.product_metadata.tags.map((tag: string) => (
                  <span key={tag} className="chip">
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </ProtectedButton>
        ))}
        {filteredProducts.length === 0 && (
          <div style={{ gridColumn: '1/-1', textAlign: 'center', padding: 40, color: 'var(--muted)' }}>
            {t('pos:catalog.empty')}
          </div>
        )}
      </div>
    </section>
  )
}
