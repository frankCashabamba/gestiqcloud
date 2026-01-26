import React from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useCompanySector } from '../../../contexts/CompanyConfigContext'

export default function SectoresPanel() {
  const { t } = useTranslation()
  const sector = useCompanySector()
  
  // Get sector from company config dynamically - no hardcodes
  const sectorCode = sector?.code?.toLowerCase() || 'retail'
  
  // Map sector to available invoice sections
  const sectorMap: Record<string, { path: string; label: string }> = {
    retail: { path: 'retail', label: t('nav.invoicing') },
    panaderia: { path: 'panaderia', label: t('billing.bySectors.bakery') },
    taller: { path: 'taller', label: t('billing.bySectors.workshop') },
    bakery: { path: 'panaderia', label: t('billing.bySectors.bakery') },
    workshop: { path: 'taller', label: t('billing.bySectors.workshop') },
  }
  
  const sectorSection = sectorMap[sectorCode] || sectorMap['retail']
  
  return (
    <div style={{ padding: 16 }}>
      <h2 className="text-xl font-semibold mb-3">{t('billing.bySectors.title')}</h2>
      <p className="text-sm text-gray-600 mb-4">{t('billing.bySectors.help')}</p>
      <ul className="list-disc list-inside">
        <li>
          <Link to={sectorSection.path} className="text-blue-700">
            {sectorSection.label}
          </Link>
        </li>
      </ul>
    </div>
  )
}
