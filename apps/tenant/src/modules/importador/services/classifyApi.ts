/**
 * classifyApi.ts
 * Servicio para consumir endpoints de clasificación del backend
 *
 * Endpoints disponibles:
 * - POST /api/v1/imports/files/classify (clasificación básica)
 * - POST /api/v1/imports/files/classify-with-ai (clasificación con IA)
 */

export interface ClassifyResponse {
  /** Parser sugerido basado en análisis del archivo */
  suggested_parser: string
  /** Confianza de la clasificación (0.0 a 1.0) */
  confidence: number
  /** Razón de la clasificación */
  reason?: string
  /** Si fue mejorado con IA (no solo heurística) */
  enhanced_by_ai: boolean
  /** Proveedor de IA usado (local, openai, azure) */
  ai_provider?: string
  /** Probabilidades para cada parser disponible */
  probabilities?: Record<string, number>
  /** Lista de parsers disponibles en el backend */
  available_parsers?: string[]
}

class ClassifyApi {
  private baseUrl: string

  constructor(baseUrl: string = '/api/v1') {
    this.baseUrl = baseUrl
  }

  /**
   * Clasificar archivo con métodos básicos (heurística local)
   * @param file Archivo a clasificar
   * @returns Resultado de clasificación
   */
  async classifyFileBasic(file: File): Promise<ClassifyResponse> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await fetch(
      `${this.baseUrl}/imports/files/classify`,
      {
        method: 'POST',
        body: formData,
      }
    )

    if (!response.ok) {
      throw new Error(`Classification failed: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Clasificar archivo con IA (local, OpenAI, o Azure)
   * Automáticamente selecciona el proveedor según configuración del backend
   * @param file Archivo a clasificar
   * @returns Resultado de clasificación mejorado con IA
   */
  async classifyFileWithAI(file: File): Promise<ClassifyResponse> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await fetch(
      `${this.baseUrl}/imports/files/classify-with-ai`,
      {
        method: 'POST',
        body: formData,
      }
    )

    if (!response.ok) {
      throw new Error(`AI classification failed: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Intentar clasificar con IA, fallback a clasificación básica si falla
   * @param file Archivo a clasificar
   * @returns Resultado de clasificación (con IA si es posible)
   */
  async classifyFileWithFallback(file: File): Promise<ClassifyResponse> {
    try {
      return await this.classifyFileWithAI(file)
    } catch (error) {
      console.warn('AI classification failed, falling back to basic:', error)
      return this.classifyFileBasic(file)
    }
  }
}

// Instancia singleton
export const classifyApi = new ClassifyApi()

export default classifyApi
