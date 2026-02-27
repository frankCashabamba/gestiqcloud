import React from 'react'
import { Routes, Route, Navigate, Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import VacationsList from './VacationsList'
import FichajesView from './FichajesView'
import NominaView from './NominaView'

function Index() {
  const { t } = useTranslation(['hr', 'common'])
  return (
    <div style={{ padding: 16 }}>
      <h2>{t('hr:title')}</h2>
      <ul>
        <li><Link to="vacaciones">{t('hr:panel.vacations')}</Link></li>
        <li><Link to="fichajes">{t('hr:panel.timekeeping')}</Link></li>
        <li><Link to="nomina">{t('hr:panel.payroll')}</Link></li>
      </ul>
    </div>
  )
}

export default function RRHHRoutes() {
  return (
    <Routes>
      <Route index element={<Index />} />
      <Route path="vacaciones" element={<VacationsList />} />
      <Route path="fichajes" element={<FichajesView />} />
      <Route path="nomina" element={<NominaView />} />
      <Route path="*" element={<Navigate to="vacaciones" replace />} />
    </Routes>
  )
}
