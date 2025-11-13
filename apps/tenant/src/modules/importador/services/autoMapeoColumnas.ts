export function autoMapeoColumnas(headers: string[], alias: Record<string, string[]>) {
  const lower = headers.map(h => h.toLowerCase())
  const result: Record<string, string> = {}
  for (const objetivo of Object.keys(alias)) {
    const candidatos = alias[objetivo]
    let match: string | undefined
    for (const cand of candidatos) {
      const idx = lower.indexOf(cand.toLowerCase())
      if (idx !== -1) { match = headers[idx]; break }
    }
    if (match) result[objetivo] = match
  }
  return result
}
