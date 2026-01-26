import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import CajaList from './CashList'
import BancoList from './BankList'
import SaldosView from './BalancesView'

export default function FinanzasRoutes() {
  return (
    <Routes>
      <Route index element={<SaldosView />} />
      <Route path="saldos" element={<SaldosView />} />
      <Route path="caja" element={<CajaList />} />
      <Route path="bancos" element={<BancoList />} />
      <Route path="*" element={<Navigate to="." replace />} />
    </Routes>
  )
}
