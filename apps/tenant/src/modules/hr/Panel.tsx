import React from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

export default function HRPanel() {
  const { t } = useTranslation(['hr', 'common'])

  return (
    <div style={{ padding: 16 }}>
      <h2>{t('hr:title')}</h2>
      <ul>
        <li><Link to="vacations">{t('hr:panel.vacations')}</Link></li>
        <li><Link to="timekeeping">{t('hr:panel.timekeeping')}</Link></li>
        <li><Link to="payroll">{t('hr:panel.payroll')}</Link></li>
      </ul>
    </div>
  )
}
