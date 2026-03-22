/**
 * useCrmLabels
 *
 * Devuelve un `t()` adaptado al sector de la empresa.
 * Panadería y Taller tienen terminología propia en vez de "Leads / Oportunidades".
 *
 * Uso (drop-in para useTranslation):
 *   const { t, moduleName } = useCrmLabels()
 */
import { useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useCompanyConfig } from '../../contexts/CompanyConfigContext'

// Sector slug → overrides parciales sobre las claves de crm.json
const SECTOR_OVERRIDES: Record<string, Record<string, Record<string, string>>> = {
  panaderia: {
    dashboard: {
      title: 'Panel de Pedidos Especiales',
      totalLeads: 'Consultas activas',
      opportunities: 'Pedidos en proceso',
      pipelineValue: 'Valor en cartera',
      conversionRate: 'Tasa de confirmación',
      leadsByStatus: 'Consultas por estado',
      opportunitiesByStage: 'Pedidos por etapa',
    },
    leads: {
      title: 'Consultas',
      newLead: 'Nueva consulta',
      editLead: 'Editar consulta',
      searchPlaceholder: 'Buscar nombre o teléfono…',
      company: 'Evento / Ocasión',
      position: 'Tipo de pedido',
      score: 'Prioridad',
      statusNew: 'Consulta recibida',
      statusContacted: 'Contactado',
      statusQualified: 'Presupuesto enviado',
      statusLost: 'Cancelado',
      statusConverted: 'Pedido confirmado',
      convert: 'Convertir a pedido',
      convertConfirm: '¿Convertir consulta a pedido?',
      converted: 'Consulta convertida a pedido',
      phoneSource: 'WhatsApp / Teléfono',
      sourceSocialMedia: 'Instagram / Redes',
      sourceEvent: 'Feria / Evento',
    },
    opportunities: {
      title: 'Pedidos en proceso',
      newButton: 'Nuevo pedido',
      new: 'Nuevo pedido',
      edit: 'Editar pedido',
      name: 'Descripción del pedido',
      searchPlaceholder: 'Buscar pedido…',
      expectedCloseDate: 'Fecha del evento',
      closeDate: 'Fecha del evento',
      stageProspecting: 'Consulta inicial',
      stageQualification: 'Diseñando',
      stageProposal: 'Presupuesto enviado',
      stageNegotiation: 'Esperando confirmación',
      stageClosedWon: 'Pedido confirmado',
      stageClosedLost: 'Cancelado',
      pendingTitle: 'Pedidos sin confirmar',
      depositSection: 'Anticipo',
      depositAmount: 'Anticipo cobrado',
      depositPaid: 'Anticipo ya cobrado',
      balanceRemaining: 'Saldo pendiente',
      paymentMethod: 'Método de pago del anticipo',
      paymentMethodNone: 'Sin anticipo',
      paymentCash: 'Efectivo',
      paymentTransfer: 'Transferencia bancaria',
      paymentCard: 'Tarjeta',
      paymentWhatsapp: 'Pago por WhatsApp',
    },
  },

  taller: {
    dashboard: {
      title: 'Panel de Cotizaciones',
      totalLeads: 'Solicitudes activas',
      opportunities: 'Trabajos aprobados',
      pipelineValue: 'Valor en cartera',
      conversionRate: 'Tasa de aprobación',
      leadsByStatus: 'Solicitudes por estado',
      opportunitiesByStage: 'Trabajos por etapa',
    },
    leads: {
      title: 'Solicitudes / Cotizaciones',
      newLead: 'Nueva solicitud',
      editLead: 'Editar solicitud',
      searchPlaceholder: 'Buscar nombre o vehículo…',
      company: 'Vehículo / Equipo',
      position: 'Tipo de trabajo',
      score: 'Urgencia',
      statusNew: 'Nueva solicitud',
      statusContacted: 'En diagnóstico',
      statusQualified: 'Cotización enviada',
      statusLost: 'No aceptada',
      statusConverted: 'Trabajo aprobado',
      convert: 'Aprobar trabajo',
      convertConfirm: '¿Marcar como trabajo aprobado?',
      converted: 'Trabajo aprobado',
      phoneSource: 'Teléfono / WhatsApp',
      sourceEvent: 'Presencial',
    },
    opportunities: {
      title: 'Trabajos en proceso',
      newButton: 'Nuevo trabajo',
      new: 'Nuevo trabajo',
      edit: 'Editar trabajo',
      name: 'Descripción del trabajo',
      searchPlaceholder: 'Buscar trabajo…',
      expectedCloseDate: 'Fecha estimada de entrega',
      closeDate: 'Fecha entrega',
      stageProspecting: 'Diagnóstico',
      stageQualification: 'Preparando cotización',
      stageProposal: 'Cotización enviada',
      stageNegotiation: 'Negociando',
      stageClosedWon: 'Trabajo aprobado',
      stageClosedLost: 'No aceptado',
      pendingTitle: 'Cotizaciones pendientes',
      depositSection: 'Anticipo / Adelanto',
      depositAmount: 'Adelanto cobrado',
      depositPaid: 'Adelanto ya cobrado',
      balanceRemaining: 'Saldo al entregar',
      paymentMethod: 'Método de pago del adelanto',
      paymentMethodNone: 'Sin adelanto',
      paymentCash: 'Efectivo',
      paymentTransfer: 'Transferencia',
      paymentCard: 'Tarjeta',
      paymentWhatsapp: 'Pago por WhatsApp',
    },
  },
}

// Alias: panaderia_pro y taller_pro usan los mismos overrides
SECTOR_OVERRIDES.panaderia_pro = SECTOR_OVERRIDES.panaderia
SECTOR_OVERRIDES.taller_pro = SECTOR_OVERRIDES.taller

const MODULE_NAMES: Record<string, string> = {
  panaderia: 'Pedidos Especiales',
  panaderia_pro: 'Pedidos Especiales',
  taller: 'Cotizaciones',
  taller_pro: 'Cotizaciones',
}

export function useCrmLabels() {
  const { t: baseT } = useTranslation('crm')
  const { config } = useCompanyConfig()
  const sector = config?.sector?.plantilla || ''
  const overrides = SECTOR_OVERRIDES[sector] || {}

  const t = useCallback(
    (key: string): string => {
      const [section, subkey] = key.split('.')
      if (subkey && overrides[section]?.[subkey] !== undefined) {
        return overrides[section][subkey]
      }
      return baseT(key) as string
    },
    [baseT, overrides],
  )

  const moduleName = MODULE_NAMES[sector] || 'CRM'

  return { t, moduleName }
}
