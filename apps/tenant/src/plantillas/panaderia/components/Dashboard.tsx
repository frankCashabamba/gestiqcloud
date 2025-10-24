/**
 * Dashboard Panadería - Vista general con KPIs
 */
import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { getDailyInventoryStats, getPurchaseStats, getMilkStats } from './services'

export default function Dashboard() {
  const [inventoryStats, setInventoryStats] = useState<any>(null)
  const [purchaseStats, setPurchaseStats] = useState<any>(null)
  const [milkStats, setMilkStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadStats()
  }, [])

  const loadStats = async () => {
    try {
      setLoading(true)
      const today = new Date()
      const lastMonth = new Date(today.getFullYear(), today.getMonth() - 1, 1)
      
      const params = {
        fecha_desde: lastMonth.toISOString().split('T')[0],
        fecha_hasta: today.toISOString().split('T')[0],
      }

      const [inv, pur, milk] = await Promise.all([
        getDailyInventoryStats(params),
        getPurchaseStats(params),
        getMilkStats(params),
      ])

      setInventoryStats(inv)
      setPurchaseStats(pur)
      setMilkStats(milk)
    } catch (err) {
      console.error('Error loading stats:', err)
    } finally {
      setLoading(false)
    }
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('es-ES', {
      style: 'currency',
      currency: 'EUR',
    }).format(value)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="text-center">
          <div className="mx-auto h-12 w-12 animate-spin rounded-full border-4 border-blue-200 border-t-blue-600" />
          <p className="mt-4 text-sm text-slate-500">Cargando dashboard...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Dashboard Panadería</h1>
        <p className="mt-1 text-sm text-slate-500">Resumen del último mes</p>
      </div>

      {/* KPIs Grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* Ventas */}
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Ventas (Unidades)</p>
          <p className="mt-3 text-3xl font-bold text-blue-600">
            {inventoryStats?.total_ventas_unidades?.toFixed(0) || '0'}
          </p>
        </div>

        {/* Ingresos */}
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Ingresos</p>
          <p className="mt-3 text-3xl font-bold text-green-600">
            {formatCurrency(inventoryStats?.total_ingresos || 0)}
          </p>
        </div>

        {/* Compras */}
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Compras</p>
          <p className="mt-3 text-3xl font-bold text-amber-600">
            {formatCurrency(purchaseStats?.total_costo || 0)}
          </p>
          <p className="mt-1 text-xs text-slate-400">{purchaseStats?.total_compras || 0} pedidos</p>
        </div>

        {/* Leche */}
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Leche Recibida</p>
          <p className="mt-3 text-3xl font-bold text-purple-600">
            {milkStats?.total_litros?.toFixed(0) || '0'} L
          </p>
          <p className="mt-1 text-xs text-slate-400">
            {milkStats?.promedio_grasa ? `${milkStats.promedio_grasa.toFixed(1)}% grasa` : '-'}
          </p>
        </div>
      </div>

      {/* Accesos Rápidos */}
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900">Accesos Rápidos</h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Link
            to="inventario"
            className="group flex items-center gap-3 rounded-lg border border-slate-200 p-4 transition hover:border-blue-300 hover:bg-blue-50"
          >
            <div className="rounded-lg bg-blue-100 p-3">
              <svg className="h-6 w-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
            </div>
            <div>
              <p className="font-medium text-slate-900">Inventario Diario</p>
              <p className="text-xs text-slate-500">Control de stock</p>
            </div>
          </Link>

          <Link
            to="compras"
            className="group flex items-center gap-3 rounded-lg border border-slate-200 p-4 transition hover:border-amber-300 hover:bg-amber-50"
          >
            <div className="rounded-lg bg-amber-100 p-3">
              <svg className="h-6 w-6 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
            </div>
            <div>
              <p className="font-medium text-slate-900">Compras</p>
              <p className="text-xs text-slate-500">Materias primas</p>
            </div>
          </Link>

          <Link
            to="leche"
            className="group flex items-center gap-3 rounded-lg border border-slate-200 p-4 transition hover:border-purple-300 hover:bg-purple-50"
          >
            <div className="rounded-lg bg-purple-100 p-3">
              <svg className="h-6 w-6 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
            </div>
            <div>
              <p className="font-medium text-slate-900">Registro de Leche</p>
              <p className="text-xs text-slate-500">Recepción diaria</p>
            </div>
          </Link>

          <Link
            to="importador"
            className="group flex items-center gap-3 rounded-lg border border-slate-200 p-4 transition hover:border-green-300 hover:bg-green-50"
          >
            <div className="rounded-lg bg-green-100 p-3">
              <svg className="h-6 w-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            </div>
            <div>
              <p className="font-medium text-slate-900">Importar Excel</p>
              <p className="text-xs text-slate-500">Diarios producción</p>
            </div>
          </Link>
        </div>
      </div>
    </div>
  )
}
