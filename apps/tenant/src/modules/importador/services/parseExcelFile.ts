export async function parseExcelFile(file: File): Promise<{ headers: string[]; rows: Record<string,string>[] }> {
  const fd = new FormData()
  fd.append('file', file)
  const res = await fetch('/v1/imports/excel/parse', { method: 'POST', body: fd, credentials: 'include' })
  if (!res.ok) {
    const msg = await res.text().catch(() => '')
    throw new Error(msg || res.statusText)
  }
  const data = await res.json()
  return {
    headers: Array.isArray(data?.headers) ? data.headers.map((x: any) => String(x)) : [],
    rows: Array.isArray(data?.rows) ? data.rows.map((r: any) => Object.fromEntries(Object.entries(r || {}).map(([k,v]) => [String(k), String(v ?? '')]))) : [],
  }
}
