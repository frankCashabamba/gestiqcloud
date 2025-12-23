import React, { useState, useMemo } from 'react'
import { ParserRegistry } from '@api-types/imports'

interface ClassificationResult {
  suggested_parser: string
  confidence: number
  reason?: string
  enhanced_by_ai?: boolean
  ai_provider?: string | null
  probabilities?: Record<string, number>
  available_parsers?: string[]
}

interface ConfirmParserModalProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: (parserId: string, mappingId?: string | null) => Promise<void>
  classificationResult: ClassificationResult | null
  parserRegistry: ParserRegistry | null
  loading?: boolean
}

const getConfidenceColor = (confidence: number): string => {
  if (confidence >= 0.7) return '#10b981'
  if (confidence >= 0.5) return '#f59e0b'
  return '#ef4444'
}

const getConfidenceLabel = (confidence: number): string => {
  if (confidence >= 0.7) return 'Alta'
  if (confidence >= 0.5) return 'Media'
  return 'Baja'
}

export const ConfirmParserModal: React.FC<ConfirmParserModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  classificationResult,
  parserRegistry,
  loading = false,
}) => {
  const [selectedParser, setSelectedParser] = useState<string | null>(null)
  const [confirming, setConfirming] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const effectiveParser = selectedParser ?? classificationResult?.suggested_parser ?? ''
  const isOverride = selectedParser !== null && selectedParser !== classificationResult?.suggested_parser

  const sortedParsers = useMemo(() => {
    if (!parserRegistry?.parsers) return []
    const probs = classificationResult?.probabilities ?? {}
    return Object.entries(parserRegistry.parsers)
      .map(([id, info]) => ({
        id,
        ...info,
        probability: probs[id] ?? 0,
      }))
      .sort((a, b) => b.probability - a.probability)
  }, [parserRegistry, classificationResult])

  const handleConfirm = async () => {
    if (!effectiveParser) return

    setConfirming(true)
    setError(null)

    try {
      await onConfirm(effectiveParser, null)
      onClose()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Error al confirmar')
    } finally {
      setConfirming(false)
    }
  }

  if (!isOpen) return null

  const confidencePercent = Math.round((classificationResult?.confidence ?? 0) * 100)
  const confidenceColor = getConfidenceColor(classificationResult?.confidence ?? 0)

  return (
    <div className="confirm-parser-modal-overlay">
      <div className="confirm-parser-modal">
        <div className="confirm-parser-modal__header">
          <h2>Confirmar Parser</h2>
          <button className="close-btn" onClick={onClose} disabled={confirming}>
            ×
          </button>
        </div>

        <div className="confirm-parser-modal__content">
          <div className="warning-banner">
            <span className="warning-icon">⚠️</span>
            <div>
              <strong>Confianza insuficiente</strong>
              <p>
                El sistema no pudo determinar con certeza el tipo de archivo.
                Por favor, confirma o selecciona el parser correcto.
              </p>
            </div>
          </div>

          {classificationResult && (
            <div className="suggestion-card">
              <div className="suggestion-header">
                <div className="suggestion-info">
                  <span className="label">Parser Sugerido:</span>
                  <span className="parser-name">{classificationResult.suggested_parser}</span>
                </div>
                <div
                  className="confidence-badge"
                  style={{ backgroundColor: confidenceColor }}
                >
                  <span className="percent">{confidencePercent}%</span>
                  <span className="level">{getConfidenceLabel(classificationResult.confidence)}</span>
                </div>
              </div>

              {classificationResult.reason && (
                <p className="reason">{classificationResult.reason}</p>
              )}

              {classificationResult.enhanced_by_ai && (
                <span className="ai-badge">
                  🤖 Analizado con {classificationResult.ai_provider || 'IA'}
                </span>
              )}
            </div>
          )}

          <div className="parser-selection">
            <label className="selection-label">Seleccionar Parser:</label>

            <div className="parser-list">
              {sortedParsers.map((parser) => {
                const isSelected = parser.id === effectiveParser
                const isSuggested = parser.id === classificationResult?.suggested_parser

                return (
                  <button
                    key={parser.id}
                    className={`parser-option ${isSelected ? 'selected' : ''} ${isSuggested ? 'suggested' : ''}`}
                    onClick={() => setSelectedParser(parser.id)}
                    disabled={confirming}
                  >
                    <div className="parser-option__info">
                      <span className="parser-id">{parser.id}</span>
                      <span className="parser-type">{parser.doc_type}</span>
                      {parser.description && (
                        <span className="parser-desc">{parser.description}</span>
                      )}
                    </div>
                    <div className="parser-option__meta">
                      {parser.probability > 0 && (
                        <span className="probability">{Math.round(parser.probability * 100)}%</span>
                      )}
                      {isSuggested && <span className="suggested-tag">Sugerido</span>}
                      {isSelected && <span className="selected-check">✓</span>}
                    </div>
                  </button>
                )
              })}
            </div>
          </div>

          {isOverride && (
            <div className="override-notice">
              <span className="notice-icon">ℹ️</span>
              <span>
                Has seleccionado un parser diferente al sugerido. Esto quedará registrado.
              </span>
            </div>
          )}

          {error && (
            <div className="error-message">
              <span>❌</span> {error}
            </div>
          )}
        </div>

        <div className="confirm-parser-modal__footer">
          <button
            className="btn-cancel"
            onClick={onClose}
            disabled={confirming}
          >
            Cancelar
          </button>
          <button
            className="btn-confirm"
            onClick={handleConfirm}
            disabled={confirming || !effectiveParser || loading}
          >
            {confirming ? 'Confirmando...' : isOverride ? 'Confirmar (Override)' : 'Confirmar'}
          </button>
        </div>
      </div>

      <style>{`
        .confirm-parser-modal-overlay {
          position: fixed;
          inset: 0;
          background: rgba(0, 0, 0, 0.5);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 1000;
          padding: 16px;
        }

        .confirm-parser-modal {
          background: white;
          border-radius: 12px;
          max-width: 600px;
          width: 100%;
          max-height: 90vh;
          display: flex;
          flex-direction: column;
          box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
        }

        .confirm-parser-modal__header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 16px 20px;
          border-bottom: 1px solid #e5e7eb;
        }

        .confirm-parser-modal__header h2 {
          margin: 0;
          font-size: 18px;
          font-weight: 600;
          color: #111827;
        }

        .close-btn {
          background: none;
          border: none;
          font-size: 24px;
          color: #6b7280;
          cursor: pointer;
          padding: 0;
          line-height: 1;
        }

        .close-btn:hover {
          color: #111827;
        }

        .confirm-parser-modal__content {
          padding: 20px;
          overflow-y: auto;
          flex: 1;
        }

        .warning-banner {
          display: flex;
          gap: 12px;
          padding: 12px 16px;
          background: #fef3c7;
          border: 1px solid #f59e0b;
          border-radius: 8px;
          margin-bottom: 16px;
        }

        .warning-icon {
          font-size: 20px;
          flex-shrink: 0;
        }

        .warning-banner strong {
          display: block;
          color: #92400e;
          margin-bottom: 4px;
        }

        .warning-banner p {
          margin: 0;
          font-size: 13px;
          color: #78350f;
        }

        .suggestion-card {
          background: #f9fafb;
          border: 1px solid #e5e7eb;
          border-radius: 8px;
          padding: 16px;
          margin-bottom: 16px;
        }

        .suggestion-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 8px;
        }

        .suggestion-info .label {
          display: block;
          font-size: 12px;
          color: #6b7280;
          text-transform: uppercase;
          font-weight: 600;
        }

        .suggestion-info .parser-name {
          font-size: 16px;
          font-weight: 700;
          color: #111827;
        }

        .confidence-badge {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          width: 60px;
          height: 60px;
          border-radius: 50%;
          color: white;
        }

        .confidence-badge .percent {
          font-size: 16px;
          font-weight: 700;
        }

        .confidence-badge .level {
          font-size: 10px;
          opacity: 0.9;
        }

        .reason {
          margin: 8px 0;
          font-size: 13px;
          color: #4b5563;
        }

        .ai-badge {
          display: inline-block;
          background: #dbeafe;
          color: #1e40af;
          padding: 4px 10px;
          border-radius: 12px;
          font-size: 11px;
          font-weight: 500;
        }

        .parser-selection {
          margin-bottom: 16px;
        }

        .selection-label {
          display: block;
          font-size: 14px;
          font-weight: 600;
          color: #374151;
          margin-bottom: 12px;
        }

        .parser-list {
          display: flex;
          flex-direction: column;
          gap: 8px;
          max-height: 240px;
          overflow-y: auto;
        }

        .parser-option {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 12px 16px;
          border: 2px solid #e5e7eb;
          border-radius: 8px;
          background: white;
          cursor: pointer;
          text-align: left;
          transition: all 0.15s;
        }

        .parser-option:hover {
          border-color: #3b82f6;
          background: #f0f9ff;
        }

        .parser-option.selected {
          border-color: #3b82f6;
          background: #eff6ff;
        }

        .parser-option.suggested {
          border-color: #10b981;
        }

        .parser-option.suggested.selected {
          border-color: #3b82f6;
        }

        .parser-option__info {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }

        .parser-id {
          font-weight: 600;
          color: #111827;
          font-size: 14px;
        }

        .parser-type {
          font-size: 12px;
          color: #6b7280;
        }

        .parser-desc {
          font-size: 11px;
          color: #9ca3af;
        }

        .parser-option__meta {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .probability {
          font-size: 12px;
          color: #6b7280;
          font-weight: 500;
        }

        .suggested-tag {
          background: #d1fae5;
          color: #065f46;
          padding: 2px 8px;
          border-radius: 10px;
          font-size: 10px;
          font-weight: 600;
          text-transform: uppercase;
        }

        .selected-check {
          color: #3b82f6;
          font-size: 18px;
          font-weight: bold;
        }

        .override-notice {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 10px 14px;
          background: #fef3c7;
          border-radius: 6px;
          font-size: 13px;
          color: #92400e;
          margin-bottom: 12px;
        }

        .error-message {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 10px 14px;
          background: #fee2e2;
          border-radius: 6px;
          font-size: 13px;
          color: #991b1b;
        }

        .confirm-parser-modal__footer {
          display: flex;
          justify-content: flex-end;
          gap: 12px;
          padding: 16px 20px;
          border-top: 1px solid #e5e7eb;
        }

        .btn-cancel,
        .btn-confirm {
          padding: 10px 20px;
          border-radius: 6px;
          font-size: 14px;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.15s;
        }

        .btn-cancel {
          background: white;
          border: 1px solid #d1d5db;
          color: #374151;
        }

        .btn-cancel:hover:not(:disabled) {
          background: #f3f4f6;
        }

        .btn-confirm {
          background: #3b82f6;
          border: none;
          color: white;
        }

        .btn-confirm:hover:not(:disabled) {
          background: #2563eb;
        }

        .btn-confirm:disabled,
        .btn-cancel:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
      `}</style>
    </div>
  )
}
