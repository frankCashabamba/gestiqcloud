import { useState } from 'react'

import { subscribeCompany } from '../services/company-settings'
import { createEmpresaFull } from '../services/empresa'
import { getErrorMessage } from '../shared/toast'
import { buildEmpresaCompletaPayload } from '../utils/formToJson'

import type { BillingCycle, CrearEmpresaResponse, FormularioEmpresa } from '../typesall/empresa'

type CreateCompanyOptions = {
  subscriptionPlanId?: string | null
  billingCycle?: BillingCycle
}

function getSuccessMessage(
  subscriptionPlanId?: string | null,
  subscription?: { checkout_url?: string } | null,
  subscriptionError?: string | null,
) {
  if (subscription?.checkout_url) {
    return 'Empresa creada. Redirigiendo a checkout para completar la suscripción.'
  }
  if (subscriptionError) {
    return 'Empresa creada. El plan quedó pendiente de asignación.'
  }
  if (subscriptionPlanId) {
    return 'Empresa creada con usuario principal y plan asignado.'
  }
  return 'Empresa creada con admin, módulos y logo'
}

export const useCrearEmpresa = () => {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [needSecondSurname, setNeedSecondSurname] = useState(false)

  const attachSubscription = async (
    companyId: string | number | undefined,
    options: CreateCompanyOptions,
  ) => {
    if (!companyId || !options.subscriptionPlanId) {
      return { subscription: null, subscriptionError: null as string | null }
    }

    try {
      const subscription = await subscribeCompany(String(companyId), {
        plan_id: options.subscriptionPlanId,
        billing_cycle: options.billingCycle || 'monthly',
        return_url: typeof window !== 'undefined' ? window.location.href : null,
      })
      return { subscription, subscriptionError: null as string | null }
    } catch (billingErr: any) {
      const subscriptionError = getErrorMessage(billingErr)
      setError(`La empresa se creó, pero no se pudo asignar el plan seleccionado: ${subscriptionError}`)
      return { subscription: null, subscriptionError }
    }
  }

  const finalizeCreate = async (
    response: { msg: string; id?: string | number },
    options: CreateCompanyOptions,
  ): Promise<CrearEmpresaResponse> => {
    const { subscription, subscriptionError } = await attachSubscription(response?.id, options)
    setSuccess(getSuccessMessage(options.subscriptionPlanId, subscription, subscriptionError))
    return { ...response, subscription, subscriptionError }
  }

  const crear = async (
    datos: FormularioEmpresa,
    options: CreateCompanyOptions = {},
  ): Promise<CrearEmpresaResponse | null> => {
    setLoading(true)
    setError(null)
    setSuccess(null)
    setFieldErrors({})
    setNeedSecondSurname(false)

    try {
      const payload = await buildEmpresaCompletaPayload(datos)
      const res = await createEmpresaFull(payload)
      return await finalizeCreate(res, options)
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err?.data?.detail || err?.detail
      if (detail === 'empresa_ruc_exists') {
        setError('El RUC ya está registrado. Verifica los datos.')
        setFieldErrors({ ruc: 'RUC ya registrado' })
      } else if (detail === 'user_email_or_username_taken') {
        const base = (datos.username || '').trim()
        const segundo = (datos.segundo_apellido_encargado || '')
          .trim()
          .toLowerCase()
          .replace(/\s+/g, '')
        if (!segundo) {
          setNeedSecondSurname(true)
          setError('El usuario ya existe. Ingresa segundo apellido para sugerir uno único.')
          setFieldErrors({ username: 'Usuario ya existente' })
          return null
        }

        for (let k = 1; k <= Math.min(segundo.length, 20); k++) {
          const candidate = `${base}${segundo.slice(0, k)}`
          try {
            const payload2 = await buildEmpresaCompletaPayload({ ...datos, username: candidate })
            const res2 = await createEmpresaFull(payload2)
            return await finalizeCreate(res2, options)
          } catch (e: any) {
            const d2 = e?.response?.data?.detail || e?.data?.detail || e?.detail
            if (d2 !== 'user_email_or_username_taken') {
              setError((e && (e.message || d2)) || 'Error inesperado')
              return null
            }
          }
        }

        for (let n = 1; n <= 99; n++) {
          const candidate = `${base}${segundo[0] || ''}${n}`
          try {
            const payload3 = await buildEmpresaCompletaPayload({ ...datos, username: candidate })
            const res3 = await createEmpresaFull(payload3)
            return await finalizeCreate(res3, options)
          } catch (e: any) {
            const d3 = e?.response?.data?.detail || e?.data?.detail || e?.detail
            if (d3 !== 'user_email_or_username_taken') {
              setError((e && (e.message || d3)) || 'Error inesperado')
              return null
            }
          }
        }

        setError('No se pudo generar un usuario único automáticamente. Inténtalo nuevamente.')
        setFieldErrors({ username: 'No disponible' })
      } else {
        setError(getErrorMessage(err))
      }
      return null
    } finally {
      setLoading(false)
    }
  }

  return {
    crear,
    loading,
    error,
    success,
    fieldErrors,
    needSecondSurname,
  }
}
