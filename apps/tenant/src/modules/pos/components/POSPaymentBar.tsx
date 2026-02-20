import React from 'react'
import { useTranslation } from 'react-i18next'
import { useCurrency } from '../../../hooks/useCurrency'
import ProtectedButton from '../../../components/ProtectedButton'

interface POSPaymentBarProps {
  cartTotal: number
  discount: number
  tax: number
  subtotal: number
  cartIsEmpty: boolean
  onPayClick: () => void
  isLoading: boolean
}

export function POSPaymentBar({
  cartTotal,
  discount,
  tax,
  subtotal,
  cartIsEmpty,
  onPayClick,
  isLoading,
}: POSPaymentBarProps) {
  const { t } = useTranslation(['pos', 'common'])
  const { symbol: currencySymbol } = useCurrency()

  return (
    <div className="pos-payment-bar bg-gradient-to-r from-slate-950 via-slate-900 to-slate-800 text-white px-3 py-2">
      <div className="flex items-end justify-between gap-3 mb-1 text-xs">
        <div className="flex items-end gap-4">
          <div>
            <span className="block text-gray-300">{t('pos:cart.subtotal')}</span>
            <span className="block text-base font-bold">{currencySymbol}{subtotal.toFixed(2)}</span>
          </div>
          {discount > 0 && (
            <div>
              <span className="block text-gray-300">{t('pos:cart.discount')}</span>
              <span className="block text-base font-bold text-red-400">-{currencySymbol}{discount.toFixed(2)}</span>
            </div>
          )}
          {tax > 0 && (
            <div>
              <span className="block text-gray-300">{t('pos:cart.tax')}</span>
              <span className="block text-base font-bold text-blue-400">+{currencySymbol}{tax.toFixed(2)}</span>
            </div>
          )}
        </div>
        <div className="text-right">
          <span className="block text-gray-300">{t('pos:cart.total')}</span>
          <span className="block text-xl font-bold text-green-400">{currencySymbol}{cartTotal.toFixed(2)}</span>
        </div>
      </div>

      <ProtectedButton
        permission="pos:create"
        onClick={onPayClick}
        disabled={cartIsEmpty || isLoading}
        className="w-full bg-gradient-to-r from-emerald-500 to-green-600 hover:from-emerald-600 hover:to-green-700 text-white font-extrabold py-2 rounded-lg text-lg tracking-wide disabled:opacity-50 transition"
      >
        {isLoading ? t('pos:common.processing') : 'COBRAR (F9)'}
      </ProtectedButton>

      <div className="mt-2 grid grid-cols-4 gap-2 text-xs md:hidden">
        <button onClick={onPayClick} disabled={cartIsEmpty || isLoading} className="flex-1 bg-green-600 hover:bg-green-700 px-2 py-1 rounded disabled:opacity-50">
          Efectivo
        </button>
        <button onClick={onPayClick} disabled={cartIsEmpty || isLoading} className="flex-1 bg-blue-600 hover:bg-blue-700 px-2 py-1 rounded disabled:opacity-50">
          Tarjeta
        </button>
        <button onClick={onPayClick} disabled={cartIsEmpty || isLoading} className="flex-1 bg-cyan-700 hover:bg-cyan-800 px-2 py-1 rounded disabled:opacity-50">
          Transferencia
        </button>
        <button onClick={onPayClick} disabled={cartIsEmpty || isLoading} className="flex-1 bg-slate-600 hover:bg-slate-700 px-2 py-1 rounded disabled:opacity-50">
          Mas opciones
        </button>
      </div>

      <p className="text-[11px] text-gray-400 mt-1 md:hidden">
        F2 Buscar | F4 Cliente | F6 Desc | F8 Suspender | F9 Cobrar | Esc Cerrar
      </p>
    </div>
  )
}
