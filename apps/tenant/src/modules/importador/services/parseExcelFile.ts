import { apiFetch } from '../../../lib/http'

export async function parseExcelFile(file: File, authToken?: string): Promise<{ headers: string[]; rows: Record<string,string>[] }> {
  const fd = new FormData()
  fd.append('file', file)
  const data = await apiFetch<{ headers: any[]; rows: any[] }>('/api/v1/imports/excel/parse', {
    method: 'POST',
    body: fd,
    authToken,
  })
  return {
    headers: Array.isArray(data?.headers) ? data.headers.map((x: any) => String(x)) : [],
    rows: Array.isArray(data?.rows) ? data.rows.map((r: any) => Object.fromEntries(Object.entries(r || {}).map(([k,v]) => [String(k), String(v ?? '')]))) : [],
  }
}
