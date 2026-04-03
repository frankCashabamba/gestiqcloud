import React from 'react'
import PermissionDenied from '../../components/PermissionDenied'
import {
  useCompanySector,
  useProductionModuleEnabled,
} from '../../contexts/CompanyConfigContext'

export default function ProductionAvailabilityGuard({
  children,
}: {
  children: React.ReactNode
}) {
  const productionEnabled = useProductionModuleEnabled()
  const sector = useCompanySector()

  if (productionEnabled) {
    return <>{children}</>
  }

  const sectorLabel = sector?.plantilla || 'actual'

  return (
    <PermissionDenied
      permission="manufacturing:read"
      severity="warning"
      message={`Produccion deshabilitada para el tenant o el sector ${sectorLabel}.`}
      footer="Activa el modulo o habilita la feature correspondiente en la configuracion del sector."
    />
  )
}
