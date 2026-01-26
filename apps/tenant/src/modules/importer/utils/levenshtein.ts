/**
 * Calcula la distancia de Levenshtein entre dos strings
 * Utilizado para auto-detección inteligente de columnas
 */

export function levenshteinDistance(a: string, b: string): number {
    const matrix: number[][] = []

    // Inicializar matriz
    for (let i = 0; i <= b.length; i++) {
        matrix[i] = [i]
    }
    for (let j = 0; j <= a.length; j++) {
        matrix[0][j] = j
    }

    // Llenar matriz
    for (let i = 1; i <= b.length; i++) {
        for (let j = 1; j <= a.length; j++) {
            if (b.charAt(i - 1) === a.charAt(j - 1)) {
                matrix[i][j] = matrix[i - 1][j - 1]
            } else {
                matrix[i][j] = Math.min(
                    matrix[i - 1][j - 1] + 1, // Sustitución
                    matrix[i][j - 1] + 1,     // Inserción
                    matrix[i - 1][j] + 1      // Eliminación
                )
            }
        }
    }

    return matrix[b.length][a.length]
}

export function calculateSimilarity(a: string, b: string): number {
    const distance = levenshteinDistance(a.toLowerCase(), b.toLowerCase())
    const maxLength = Math.max(a.length, b.length)

    if (maxLength === 0) return 100

    return Math.round(((maxLength - distance) / maxLength) * 100)
}

export interface ColumnSuggestion {
    sourceColumn: string
    confidence: number
}

export function getSuggestions(
    targetField: string,
    sourceColumns: string[],
    aliases: string[] = []
): ColumnSuggestion[] {
    const suggestions: ColumnSuggestion[] = []

    // Buscar en columnas fuente
    for (const col of sourceColumns) {
        const similarity = calculateSimilarity(targetField, col)

        if (similarity >= 60) { // Umbral mínimo 60%
            suggestions.push({
                sourceColumn: col,
                confidence: similarity
            })
        }
    }

    // Buscar en aliases
    for (const alias of aliases) {
        for (const col of sourceColumns) {
            const similarity = calculateSimilarity(alias, col)

            if (similarity >= 60) {
                const existing = suggestions.find(s => s.sourceColumn === col)
                if (!existing || similarity > existing.confidence) {
                    if (existing) {
                        existing.confidence = similarity
                    } else {
                        suggestions.push({
                            sourceColumn: col,
                            confidence: similarity
                        })
                    }
                }
            }
        }
    }

    // Ordenar por confianza descendente
    return suggestions.sort((a, b) => b.confidence - a.confidence)
}
