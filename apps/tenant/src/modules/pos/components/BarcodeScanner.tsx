/**
 * BarcodeScanner - Scanner con cámara HTML5
 */
import React, { useRef, useEffect, useState } from 'react'

interface BarcodeScannerProps {
  onScan: (code: string) => void
  onClose: () => void
}

export default function BarcodeScanner({ onScan, onClose }: BarcodeScannerProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [error, setError] = useState<string | null>(null)
  const [scanning, setScanning] = useState(false)

  useEffect(() => {
    startCamera()
    return () => {
      stopCamera()
    }
  }, [])

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' }
      })
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        videoRef.current.play()
        startBarcodeDetection()
      }
    } catch (err: any) {
      setError('No se pudo acceder a la cámara: ' + err.message)
    }
  }

  const stopCamera = () => {
    if (videoRef.current?.srcObject) {
      const stream = videoRef.current.srcObject as MediaStream
      stream.getTracks().forEach((track) => track.stop())
    }
  }

  const startBarcodeDetection = async () => {
    // BarcodeDetector API (Chrome/Edge)
    if ('BarcodeDetector' in window) {
      try {
        const barcodeDetector = new (window as any).BarcodeDetector({
          formats: ['ean_13', 'ean_8', 'code_128', 'qr_code']
        })

        const detect = async () => {
          if (!videoRef.current || scanning) return

          try {
            const barcodes = await barcodeDetector.detect(videoRef.current)
            if (barcodes.length > 0) {
              setScanning(true)
              const code = barcodes[0].rawValue
              onScan(code)
              setTimeout(() => setScanning(false), 2000)
            }
          } catch (e) {
            // Ignorar errores de detección
          }

          requestAnimationFrame(detect)
        }

        detect()
      } catch (e: any) {
        setError('BarcodeDetector no soportado: ' + e.message)
      }
    } else {
      setError('BarcodeDetector no disponible en este navegador')
    }
  }

  return (
    <div className="fixed inset-0 bg-black z-50 flex flex-col">
      <div className="flex justify-between items-center p-4 bg-black bg-opacity-80">
        <h2 className="text-white font-bold">Escanear Código de Barras</h2>
        <button
          onClick={onClose}
          className="text-white text-2xl px-4 py-2 hover:bg-white hover:bg-opacity-20 rounded"
        >
          ✕
        </button>
      </div>

      <div className="flex-1 relative">
        {error ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="bg-red-600 text-white p-6 rounded max-w-md text-center">
              <p className="mb-4">{error}</p>
              <button
                onClick={onClose}
                className="bg-white text-red-600 px-4 py-2 rounded font-bold"
              >
                Cerrar
              </button>
            </div>
          </div>
        ) : (
          <>
            <video
              ref={videoRef}
              className="w-full h-full object-cover"
              playsInline
              muted
            />
            
            {/* Overlay de escaneo */}
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="border-4 border-green-500 w-64 h-32 rounded-lg animate-pulse"></div>
            </div>

            {scanning && (
              <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
                <div className="bg-green-500 text-white px-6 py-3 rounded-lg font-bold text-xl">
                  ✓ Código Detectado
                </div>
              </div>
            )}
          </>
        )}
      </div>

      <div className="p-4 bg-black bg-opacity-80 text-white text-center">
        <p className="text-sm">Apunte la cámara hacia el código de barras</p>
      </div>
    </div>
  )
}
