/**
 * parseCSVFile.ts
 * Parser CSV robusto que maneja comillas, escapes y delimitadores correctamente.
 * 
 * Si hay problemas con archivos complejos, se puede delegar al backend.
 */

type Row = Record<string, string>

interface ParseResult {
  headers: string[]
  rows: Row[]
}

/**
 * Parse a CSV value handling quoted fields with commas and escaped quotes
 */
function parseCSVLine(line: string, delimiter = ','): string[] {
  const result: string[] = []
  let current = ''
  let inQuotes = false
  
  for (let i = 0; i < line.length; i++) {
    const char = line[i]
    const nextChar = line[i + 1]
    
    if (inQuotes) {
      if (char === '"') {
        if (nextChar === '"') {
          // Escaped quote
          current += '"'
          i++ // Skip next quote
        } else {
          // End of quoted field
          inQuotes = false
        }
      } else {
        current += char
      }
    } else {
      if (char === '"') {
        // Start of quoted field
        inQuotes = true
      } else if (char === delimiter) {
        // End of field
        result.push(current.trim())
        current = ''
      } else {
        current += char
      }
    }
  }
  
  // Don't forget the last field
  result.push(current.trim())
  
  return result
}

/**
 * Detect the delimiter used in the CSV (comma, semicolon, or tab)
 */
function detectDelimiter(firstLine: string): string {
  const delimiters = [',', ';', '\t']
  let bestDelimiter = ','
  let maxCount = 0
  
  for (const delimiter of delimiters) {
    const count = (firstLine.match(new RegExp(`\\${delimiter}`, 'g')) || []).length
    if (count > maxCount) {
      maxCount = count
      bestDelimiter = delimiter
    }
  }
  
  return bestDelimiter
}

/**
 * Parse CSV text into headers and rows
 */
export function parseCSV(text: string): ParseResult {
  // Normalize line endings
  const normalizedText = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n')
  const lines = normalizedText.split('\n').filter(line => line.trim())
  
  if (lines.length === 0) {
    return { headers: [], rows: [] }
  }
  
  // Detect delimiter from first line
  const delimiter = detectDelimiter(lines[0])
  
  // Parse headers
  const headers = parseCSVLine(lines[0], delimiter)
  
  // Parse data rows
  const rows: Row[] = []
  for (let i = 1; i < lines.length; i++) {
    const values = parseCSVLine(lines[i], delimiter)
    const row: Row = {}
    
    headers.forEach((header, idx) => {
      row[header] = values[idx] ?? ''
    })
    
    rows.push(row)
  }
  
  return { headers, rows }
}

/**
 * Parse CSV file
 */
export async function parseCSVFile(file: File): Promise<ParseResult> {
  const text = await file.text()
  return parseCSV(text)
}

export default parseCSVFile
