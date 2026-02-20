/**
 * useSinglePaymentFlow - Hook que unifica el flujo de pago
 * Reemplaza la lógica dispersa de PaymentModal en POSView
 */
import { useState, useCallback } from 'react'
import { useToast } from '../../../components/Toast'
import type { POSPayment } from '../../../types/pos'

export interface PaymentFlowState {
  isOpen: boolean
  totalAmount: number
  selectedMethod: 'cash' | 'card' | 'store_credit' | 'link'
  cashAmount: string
  loading: boolean
}

export interface PaymentFlowResult {
  payments: POSPayment[]
  response?: any
}

export function useSinglePaymentFlow() {
  const toast = useToast()
  const [state, setState] = useState<PaymentFlowState>({
    isOpen: false,
    totalAmount: 0,
    selectedMethod: 'cash',
    cashAmount: '0',
    loading: false,
  })

  const openPayment = useCallback((totalAmount: number) => {
    setState((prev) => ({
      ...prev,
      isOpen: true,
      totalAmount,
      cashAmount: totalAmount.toFixed(2),
      selectedMethod: 'cash',
    }))
  }, [])

  const closePayment = useCallback(() => {
    setState((prev) => ({
      ...prev,
      isOpen: false,
    }))
  }, [])

  const setMethod = useCallback((method: 'cash' | 'card' | 'store_credit' | 'link') => {
    setState((prev) => ({
      ...prev,
      selectedMethod: method,
    }))
  }, [])

  const setCashAmount = useCallback((amount: string) => {
    setState((prev) => ({
      ...prev,
      cashAmount: amount,
    }))
  }, [])

  const calculateChange = useCallback(() => {
    if (state.selectedMethod === 'cash') {
      const paid = parseFloat(state.cashAmount) || 0
      return Math.max(0, paid - state.totalAmount)
    }
    return 0
  }, [state.selectedMethod, state.cashAmount, state.totalAmount])

  const validateAndPay = useCallback(
    async (handler: (state: PaymentFlowState) => Promise<PaymentFlowResult>) => {
      if (state.loading) return null

      setState((prev) => ({ ...prev, loading: true }))

      try {
        // Validaciones básicas
        if (state.selectedMethod === 'cash') {
          const paid = parseFloat(state.cashAmount) || 0
          if (paid <= 0) {
            toast.error('Ingresa el importe recibido')
            return null
          }
          if (paid < state.totalAmount) {
            toast.warning(
              `Monto insuficiente. Falta: ${(state.totalAmount - paid).toFixed(2)}`
            )
            return null
          }
        }

        // Llamar handler externo (que hace el pago real)
        const result = await handler(state)

        toast.success(`Pago procesado exitosamente`)
        return result
      } catch (error: any) {
        const message = error.response?.data?.detail || error.message || 'Error al procesar pago'
        toast.error(message, {
          duration: 5000,
          action: {
            label: 'Reintentar',
            onClick: () => {
              // El usuario debe reintentar manualmente
            },
          },
        })
        return null
      } finally {
        setState((prev) => ({ ...prev, loading: false }))
      }
    },
    [state, toast]
  )

  return {
    state,
    openPayment,
    closePayment,
    setMethod,
    setCashAmount,
    calculateChange,
    validateAndPay,
    isOpen: state.isOpen,
    isLoading: state.loading,
  }
}
