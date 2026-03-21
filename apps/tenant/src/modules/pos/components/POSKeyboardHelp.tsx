/**
 * POSKeyboardHelp - Overlay con atajos de teclado disponibles
 */
import React, { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  getBulkPricingShortcutItems,
  type BulkPricingItem,
} from '../bakeryShortcuts'

interface POSKeyboardHelpProps {
  bulkPricingItems?: BulkPricingItem[]
}

export function POSKeyboardHelp({ bulkPricingItems = [] }: POSKeyboardHelpProps) {
  const { t } = useTranslation(['pos', 'common'])
  const [isOpen, setIsOpen] = useState(false)

  const shortcuts = useMemo(() => {
    const base = [
      { key: 'F2', action: t('pos:keyboard.searchProduct') },
      { key: 'F4', action: t('pos:keyboard.selectCustomer') },
      { key: 'F6', action: t('pos:keyboard.globalDiscount') },
      { key: 'F7', action: t('pos:keyboard.printQuote') },
      { key: 'F8', action: t('pos:keyboard.suspendSale') },
      { key: 'F9', action: t('pos:keyboard.openPayment') },
      { key: 'F10', action: t('pos:keyboard.expressCash') },
      { key: 'F11', action: t('pos:keyboard.expressCashPrint') },
      { key: 'Enter', action: t('pos:keyboard.confirmPayment') },
      { key: 'Esc', action: t('pos:keyboard.closeModal') },
      { key: 'Up/Down', action: t('pos:keyboard.navigateLists') },
    ]

    const bakery = getBulkPricingShortcutItems(bulkPricingItems).map((item) => ({
      key: item.shortcut_letter || '',
      action: t('pos:keyboard.bakeryShortcutItem', {
        product: item.product_name || item.product_id,
        quantity: item.quantity,
        price: item.unit_price.toFixed(2),
      }),
    }))

    if (bakery.length > 0) {
      base.push({
        key: t('pos:keyboard.bakeryShortcutKey'),
        action: t('pos:keyboard.bakeryShortcutDescription'),
      })
    }

    return [...base, ...bakery]
  }, [bulkPricingItems, t])

  return (
    <>
      <button
        onClick={() => setIsOpen(!isOpen)}
        aria-label={t('pos:keyboard.shortcutsButton')}
        className="fixed bottom-4 right-4 flex h-10 w-10 items-center justify-center rounded-full bg-gray-700 text-sm font-bold text-white hover:bg-gray-800 z-40"
        title={t('pos:keyboard.shortcutsButton')}
      >
        KB
      </button>

      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="max-w-md rounded-lg bg-white p-6">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-xl font-bold">{t('pos:keyboard.title')}</h2>
              <button
                onClick={() => setIsOpen(false)}
                aria-label={t('common:close', { defaultValue: 'Close' })}
                className="text-gray-500 hover:text-gray-700"
              >
                x
              </button>
            </div>

            <div className="max-h-96 space-y-3 overflow-y-auto">
              {shortcuts.map((shortcut) => (
                <div key={`${shortcut.key}-${shortcut.action}`} className="flex gap-3">
                  <kbd className="flex-shrink-0 rounded bg-gray-800 px-3 py-1 font-mono text-sm font-bold text-white">
                    {shortcut.key}
                  </kbd>
                  <span className="text-sm text-gray-700">{shortcut.action}</span>
                </div>
              ))}
            </div>

            <p className="mt-4 border-t pt-4 text-xs text-gray-500">
              {t('pos:keyboard.tip')}
            </p>
          </div>
        </div>
      )}
    </>
  )
}
