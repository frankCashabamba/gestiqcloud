import React from 'react'
import { useTranslation } from 'react-i18next'

export function PlanContable() {
  const { t } = useTranslation()
  return (
    <div className="p-4">
      <h2 className="text-lg font-semibold mb-2">{t('accounting.chartOfAccounts.title')}</h2>
      <p className="text-sm text-gray-600">{t('accounting.chartOfAccounts.placeholder')}</p>
    </div>
  )
}
