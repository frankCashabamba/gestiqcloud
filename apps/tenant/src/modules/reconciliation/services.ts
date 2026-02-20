import api from '../../services/api/client'

export interface BankStatement {
  id: string
  bank_name: string
  account_number: string
  statement_date: string
  status: 'imported' | 'processing' | 'reconciled' | 'partial'
  total_transactions: number
  matched_count: number
  unmatched_count: number
  created_at: string
}

export interface StatementLine {
  id: string
  transaction_date: string
  description: string
  reference: string
  amount: number
  transaction_type: 'credit' | 'debit'
  match_status: 'matched' | 'unmatched' | 'partial'
  match_confidence: number
  matched_invoice_id: string | null
  created_at: string
}

export interface ReconciliationSummary {
  total_statements: number
  total_lines: number
  matched: number
  unmatched: number
  auto_matched: number
  manual_matched: number
}

export interface StatementImportPayload {
  bank_name: string
  account_number: string
  statement_date: string
  transactions: {
    transaction_date: string
    description: string
    reference: string
    amount: number
    transaction_type: 'credit' | 'debit'
  }[]
}

const BASE = '/reconciliation'

export async function listStatements(): Promise<{ items: BankStatement[]; total: number }> {
  return api.get(`${BASE}/statements`).then(r => r.data)
}

export async function getStatementDetail(id: string): Promise<BankStatement> {
  return api.get(`${BASE}/statements/${id}`).then(r => r.data)
}

export async function getStatementLines(id: string): Promise<StatementLine[]> {
  return api.get(`${BASE}/statements/${id}/lines`).then(r => r.data)
}

export async function importStatement(payload: StatementImportPayload): Promise<BankStatement> {
  return api.post(`${BASE}/statements`, payload).then(r => r.data)
}

export async function autoMatch(statementId: string): Promise<BankStatement> {
  return api.post(`${BASE}/statements/${statementId}/auto-match`).then(r => r.data)
}

export async function manualMatch(lineId: string, invoiceId: string): Promise<StatementLine> {
  return api.post(`${BASE}/match`, { line_id: lineId, invoice_id: invoiceId }).then(r => r.data)
}

export async function getSummary(): Promise<ReconciliationSummary> {
  return api.get(`${BASE}/summary`).then(r => r.data)
}

export async function getPendingReconciliations(): Promise<{ count: number; pending_invoices: any[] }> {
  return api.get(`${BASE}/pending`).then(r => r.data)
}
