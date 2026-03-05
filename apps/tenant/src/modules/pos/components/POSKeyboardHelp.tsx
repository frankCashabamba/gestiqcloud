/**
 * POSKeyboardHelp - Overlay con atajos de teclado disponibles
 */
import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'

export function POSKeyboardHelp() {
  const { t } = useTranslation(['pos', 'common'])
  const [isOpen, setIsOpen] = useState(false)

  const SHORTCUTS = [
    { key: 'F2', action: t('pos:keyboard.searchProduct') },
    { key: 'F4', action: t('pos:keyboard.selectCustomer') },
    { key: 'F6', action: t('pos:keyboard.globalDiscount') },
    { key: 'F8', action: t('pos:keyboard.suspendSale') },
    { key: 'F9', action: t('pos:keyboard.openPayment') },
    { key: 'Enter', action: t('pos:keyboard.confirmPayment') },
    { key: 'Esc', action: t('pos:keyboard.closeModal') },
    { key: '↑↓', action: t('pos:keyboard.navigateLists') },
  ]

  return (
    <>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-4 right-4 w-10 h-10 bg-gray-700 text-white rounded-full flex items-center justify-center hover:bg-gray-800 z-40"
        title={t('pos:keyboard.shortcutsButton')}
      >
        ⌨
      </button>

      {isOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold">{t('pos:keyboard.title')}</h2>
              <button
                onClick={() => setIsOpen(false)}
                className="text-gray-500 hover:text-gray-700"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 max-h-96 overflow-y-auto">
              {SHORTCUTS.map((shortcut) => (
                <div key={shortcut.key} className="flex gap-3">
                  <kbd className="flex-shrink-0 bg-gray-800 text-white px-3 py-1 rounded font-mono font-bold text-sm">
                    {shortcut.key}
                  </kbd>
                  <span className="text-gray-700 text-sm">{shortcut.action}</span>
                </div>
              ))}
            </div>

            <p className="text-xs text-gray-500 mt-4 pt-4 border-t">
              {t('pos:keyboard.tip')}
            </p>
          </div>
        </div>
      )}
    </>
  )
}