export type ImportAIProvider = 'local' | 'openai' | 'azure' | 'ollama' | 'ovhcloud'

const STORAGE_KEY = 'importador_ai_provider'

export function getImportAIProviderPreference(): ImportAIProvider | null {
  try {
    const value = localStorage.getItem(STORAGE_KEY)
    if (!value) return null
    if (['local', 'openai', 'azure', 'ollama', 'ovhcloud'].includes(value)) {
      return value as ImportAIProvider
    }
  } catch {}
  return null
}

export function withImportAIProvider(path: string): string {
  const provider = getImportAIProviderPreference()
  if (!provider) return path
  const joiner = path.includes('?') ? '&' : '?'
  return `${path}${joiner}provider=${encodeURIComponent(provider)}`
}
