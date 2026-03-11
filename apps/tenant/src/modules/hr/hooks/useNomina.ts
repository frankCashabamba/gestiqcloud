import { useEffect, useState } from 'react'
import {
  approveNomina,
  createNomina,
  listNominas,
  payNomina,
  type PayrollSummary,
} from '../services/nomina'

export function useNomina() {
  const [recibos, setRecibos] = useState<PayrollSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = () => {
    setLoading(true)
    setError(null)
    listNominas()
      .then((items) => setRecibos(items))
      .catch((err: unknown) => {
        const message =
          err instanceof Error ? err.message : 'No se pudo cargar la nómina'
        setError(message)
        setRecibos([])
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [])

  const generate = async (payrollMonth: string, payrollDate: string) => {
    setSubmitting(true)
    setError(null)
    try {
      await createNomina({ payroll_month: payrollMonth, payroll_date: payrollDate })
      load()
      return true
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo generar la nómina')
      return false
    } finally {
      setSubmitting(false)
    }
  }

  const confirm = async (id: string) => {
    setSubmitting(true)
    setError(null)
    try {
      await approveNomina(id)
      load()
      return true
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo confirmar la nómina')
      return false
    } finally {
      setSubmitting(false)
    }
  }

  const markPaid = async (id: string) => {
    setSubmitting(true)
    setError(null)
    try {
      await payNomina(id)
      load()
      return true
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo marcar la nómina como pagada')
      return false
    } finally {
      setSubmitting(false)
    }
  }

  return {
    recibos,
    loading,
    submitting,
    error,
    reload: load,
    generate,
    confirm,
    markPaid,
  }
}
