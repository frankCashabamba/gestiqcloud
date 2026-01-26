export function normalizarTextoOCR(text: string): string {
  return text.replace(/\r/g, '').trim()
}
