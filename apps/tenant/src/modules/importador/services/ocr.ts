export type OCRResult = { text: string }

export async function procesarImagenConOCR(_file: File): Promise<OCRResult> {
  // Stub: aquí integrarías Tesseract u otro servicio OCR
  return { text: '' }
}

