/**
 * POSLayout - Layout responsivo desktop/móvil
 * Desktop: 2 columnas (catálogo | carrito)
 * Móvil: Tab entre catálogo y carrito
 */
import React, { useState } from 'react'
import { useMediaQuery } from '../../../hooks/useMediaQuery'

interface POSLayoutProps {
  catalog: React.ReactNode
  cart: React.ReactNode
  cartItemsCount: number
  bottomPaymentBar: React.ReactNode
}

export function POSLayout({
  catalog,
  cart,
  cartItemsCount,
  bottomPaymentBar,
}: POSLayoutProps) {
  const isMobile = useMediaQuery('(max-width: 768px)')
  const [mobileTab, setMobileTab] = useState<'catalog' | 'cart'>('catalog')

  if (isMobile) {
    // Vista móvil: pestañas
    return (
      <div className="flex flex-col h-screen bg-gray-50">
        {/* Tabs */}
        <div className="flex border-b bg-white sticky top-0 z-10">
          <button
            onClick={() => setMobileTab('catalog')}
            className={`flex-1 py-3 font-medium transition ${
              mobileTab === 'catalog'
                ? 'border-b-2 border-blue-600 text-blue-600'
                : 'text-gray-600'
            }`}
          >
            Catálogo
          </button>
          <button
            onClick={() => setMobileTab('cart')}
            className={`flex-1 py-3 font-medium transition relative ${
              mobileTab === 'cart'
                ? 'border-b-2 border-blue-600 text-blue-600'
                : 'text-gray-600'
            }`}
          >
            Carrito
            {cartItemsCount > 0 && (
              <span className="absolute top-0 right-2 bg-red-500 text-white text-xs rounded-full w-6 h-6 flex items-center justify-center">
                {cartItemsCount}
              </span>
            )}
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {mobileTab === 'catalog' ? catalog : cart}
        </div>

        {/* Bottom Payment Bar */}
        <div className="sticky bottom-0 bg-white border-t">{bottomPaymentBar}</div>
      </div>
    )
  }

  // Vista desktop: 2 columnas
  return (
    <div className="flex flex-col h-screen bg-gray-50">
      <div className="flex flex-1 overflow-hidden">
        {/* Catálogo a la izquierda */}
        <div className="flex-1 overflow-y-auto border-r bg-white">{catalog}</div>

        {/* Carrito a la derecha */}
        <div className="w-1/3 flex flex-col border-r bg-white">
          <div className="flex-1 overflow-y-auto">{cart}</div>
          <div className="border-t">{bottomPaymentBar}</div>
        </div>
      </div>
    </div>
  )
}
