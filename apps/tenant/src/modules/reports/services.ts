import api from '../../services/api/client'
import { TENANT_REPORTS } from '@shared/endpoints'

export interface ReportData {
  columns: string[]
  rows: any[][]
  summary?: Record<string, any>
}

export interface GeneratedReport {
  id: string
  name: string
  report_type: string
  format: string
  status: string
  row_count: number
  data: ReportData
}

export interface ReportType {
  value: string
  label: string
}

export async function getAvailableReports(): Promise<{ available_types: ReportType[], history: any }> {
  return api.get(TENANT_REPORTS.base).then(r => r.data)
}

export async function generateReport(params: { report_type: string, name: string, date_from?: string, date_to?: string, format?: string }): Promise<GeneratedReport> {
  return api.post(TENANT_REPORTS.generate, params).then(r => r.data)
}

export async function getSalesReport(dateFrom?: string, dateTo?: string): Promise<GeneratedReport> {
  return api.get(TENANT_REPORTS.sales, { params: { date_from: dateFrom, date_to: dateTo } }).then(r => r.data)
}

export async function getInventoryReport(): Promise<GeneratedReport> {
  return api.get(TENANT_REPORTS.inventory).then(r => r.data)
}

export async function getFinancialReport(dateFrom?: string, dateTo?: string): Promise<GeneratedReport> {
  return api.get(TENANT_REPORTS.financial, { params: { date_from: dateFrom, date_to: dateTo } }).then(r => r.data)
}

export async function exportReport(params: { report_type: string, format: string, date_from?: string, date_to?: string }): Promise<Blob> {
  return api.post(TENANT_REPORTS.export, params, { responseType: 'blob' }).then(r => r.data)
}

export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

export async function downloadReport(reportType: string, format: string, dateFrom?: string, dateTo?: string) {
  const ext: Record<string, string> = { csv: 'csv', excel: 'xlsx', pdf: 'pdf', json: 'json', html: 'html' }
  const blob = await exportReport({ report_type: reportType, format, date_from: dateFrom, date_to: dateTo })
  downloadBlob(blob, `${reportType}_${new Date().toISOString().slice(0, 10)}.${ext[format] || 'bin'}`)
}
