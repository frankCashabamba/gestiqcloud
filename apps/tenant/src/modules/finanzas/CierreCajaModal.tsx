import React, { useState } from 'react'
import { useToast, getErrorMessage } from '../../shared/toast'

type CierreCajaModalProps = {
    open: boolean
    onClose: () => void
    onSuccess: (data: any) => void
}

export default function CierreCajaModal({ open, onClose, onSuccess }: CierreCajaModalProps) {
    const [fecha, setFecha] = useState(new Date().toISOString().slice(0, 10))
    const [saldoFinal, setSaldoFinal] = useState(0)
    const [notas, setNotas] = useState('')
    const { success, error } = useToast()
    const [loading, setLoading] = useState(false)

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        try {
            setLoading(true)
            // Aquí iría la llamada al endpoint de cierre
            // const data = await cerrarCaja({ fecha, saldo_final: saldoFinal, notas })
            const data = { fecha, saldo_final: saldoFinal, notas }
            success('Cierre de caja registrado')
            onSuccess(data)
            onClose()
        } catch (e: any) {
            error(getErrorMessage(e))
        } finally {
            setLoading(false)
        }
    }

    if (!open) return null

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 w-full max-w-md">
                <h3 className="text-xl font-semibold mb-4">Cierre de Caja</h3>
                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="block mb-1">Fecha</label>
                        <input
                            type="date"
                            value={fecha}
                            onChange={(e) => setFecha(e.target.value)}
                            className="border px-2 py-1 w-full rounded"
                            required
                        />
                    </div>
                    <div>
                        <label className="block mb-1">Saldo Final</label>
                        <input
                            type="number"
                            value={saldoFinal}
                            onChange={(e) => setSaldoFinal(Number(e.target.value))}
                            className="border px-2 py-1 w-full rounded"
                            required
                            step="0.01"
                        />
                    </div>
                    <div>
                        <label className="block mb-1">Notas</label>
                        <textarea
                            value={notas}
                            onChange={(e) => setNotas(e.target.value)}
                            className="border px-2 py-1 w-full rounded"
                            rows={3}
                        />
                    </div>
                    <div className="flex justify-end gap-2 pt-2">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-3 py-2 border rounded"
                            disabled={loading}
                        >
                            Cancelar
                        </button>
                        <button
                            type="submit"
                            className="bg-blue-600 text-white px-3 py-2 rounded"
                            disabled={loading}
                        >
                            {loading ? 'Guardando...' : 'Guardar Cierre'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    )
}
