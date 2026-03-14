import { useEffect, useState } from 'react'
import { getErrorMessage } from '../../../shared/toast'
import {
  approveNomina,
  createNomina,
  listNominas,
  payNomina,
  removeNomina,
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
        setError(getErrorMessage(err))
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
      setError(getErrorMessage(err))
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
      setError(getErrorMessage(err))
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
      setError(getErrorMessage(err))
      return false
    } finally {
      setSubmitting(false)
    }
  }

  const remove = async (id: string) => {
    setSubmitting(true)
    setError(null)
    try {
      await removeNomina(id)
      load()
      return true
    } catch (err) {
      setError(getErrorMessage(err))
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
    remove,
  }
}
