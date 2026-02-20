import React, { useState } from 'react'
import { IMPORTS } from '@endpoints/imports'

interface FeedbackPromptProps {
  batchId: string
  originalParser: string
  originalConfidence: number
  originalDocType: string
  confirmedParser: string
  headers: string[]
  filename: string
  availableParsers?: Array<{ id: string; label: string }>
  onSubmit: () => void
  onDismiss?: () => void
}

interface FeedbackData {
  batch_id: string
  original_parser: string
  original_confidence: number
  original_doc_type: string
  corrected_parser: string | null
  corrected_doc_type: string | null
  was_correct: boolean
  headers: string[]
  filename: string
}

export function FeedbackPrompt({
  batchId,
  originalParser,
  originalConfidence,
  originalDocType,
  confirmedParser,
  headers,
  filename,
  availableParsers = [],
  onSubmit,
  onDismiss,
}: FeedbackPromptProps) {
  const [showForm, setShowForm] = useState(true)
  const [submitted, setSubmitted] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [showCorrectionForm, setShowCorrectionForm] = useState(false)
  const [selectedCorrectParser, setSelectedCorrectParser] = useState<string>('')
  const [error, setError] = useState<string | null>(null)

  const wasAutoCorrect = confirmedParser === originalParser

  const handleCorrectClick = async () => {
    await submitFeedback({
      batch_id: batchId,
      original_parser: originalParser,
      original_confidence: originalConfidence,
      original_doc_type: originalDocType,
      corrected_parser: null,
      corrected_doc_type: null,
      was_correct: true,
      headers,
      filename,
    })
  }

  const handleIncorrectClick = () => {
    if (wasAutoCorrect) {
      setShowCorrectionForm(true)
    } else {
      submitFeedback({
        batch_id: batchId,
        original_parser: originalParser,
        original_confidence: originalConfidence,
        original_doc_type: originalDocType,
        corrected_parser: confirmedParser,
        corrected_doc_type: null,
        was_correct: false,
        headers,
        filename,
      })
    }
  }

  const handleCorrectionSubmit = async () => {
    if (!selectedCorrectParser) {
      setError('Por favor selecciona el parser correcto')
      return
    }

    await submitFeedback({
      batch_id: batchId,
      original_parser: originalParser,
      original_confidence: originalConfidence,
      original_doc_type: originalDocType,
      corrected_parser: selectedCorrectParser,
      corrected_doc_type: null,
      was_correct: false,
      headers,
      filename,
    })
  }

  const submitFeedback = async (data: FeedbackData) => {
    setSubmitting(true)
    setError(null)

    try {
      const response = await fetch(IMPORTS.feedback.base, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
        credentials: 'include',
      })

      if (!response.ok) {
        throw new Error('Error al enviar feedback')
      }

      setSubmitted(true)
      setShowForm(false)
      onSubmit()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error desconocido')
    } finally {
      setSubmitting(false)
    }
  }

  const handleDismiss = () => {
    setShowForm(false)
    onDismiss?.()
  }

  if (!showForm) {
    if (submitted) {
      return (
        <div className="feedback-prompt feedback-prompt--success">
          <span className="feedback-prompt__icon">✓</span>
          <span>Gracias por tu feedback</span>
        </div>
      )
    }
    return null
  }

  if (showCorrectionForm) {
    return (
      <div className="feedback-prompt feedback-prompt--correction">
        <div className="feedback-prompt__header">
          <span className="feedback-prompt__icon">🔧</span>
          <span>¿Cuál era el parser correcto?</span>
        </div>

        <select
          className="feedback-prompt__select"
          value={selectedCorrectParser}
          onChange={(e) => setSelectedCorrectParser(e.target.value)}
          disabled={submitting}
        >
          <option value="">-- Selecciona --</option>
          {availableParsers
            .filter((p) => p.id !== originalParser)
            .map((parser) => (
              <option key={parser.id} value={parser.id}>
                {parser.label || parser.id}
              </option>
            ))}
        </select>

        {error && <div className="feedback-prompt__error">{error}</div>}

        <div className="feedback-prompt__actions">
          <button
            className="feedback-prompt__btn feedback-prompt__btn--secondary"
            onClick={() => setShowCorrectionForm(false)}
            disabled={submitting}
          >
            Cancelar
          </button>
          <button
            className="feedback-prompt__btn feedback-prompt__btn--primary"
            onClick={handleCorrectionSubmit}
            disabled={submitting || !selectedCorrectParser}
          >
            {submitting ? 'Enviando...' : 'Enviar'}
          </button>
        </div>

        <style>{styles}</style>
      </div>
    )
  }

  return (
    <div className="feedback-prompt">
      <div className="feedback-prompt__header">
        <span className="feedback-prompt__icon">💡</span>
        <span>¿La clasificación automática fue correcta?</span>
        <button
          className="feedback-prompt__dismiss"
          onClick={handleDismiss}
          title="Cerrar"
        >
          ×
        </button>
      </div>

      <div className="feedback-prompt__info">
        <span className="feedback-prompt__parser">
          Parser: <strong>{originalParser}</strong>
        </span>
        <span className="feedback-prompt__confidence">
          Confianza: {Math.round(originalConfidence * 100)}%
        </span>
      </div>

      {error && <div className="feedback-prompt__error">{error}</div>}

      <div className="feedback-prompt__actions">
        <button
          className="feedback-prompt__btn feedback-prompt__btn--success"
          onClick={handleCorrectClick}
          disabled={submitting}
        >
          👍 Sí, correcto
        </button>
        <button
          className="feedback-prompt__btn feedback-prompt__btn--warning"
          onClick={handleIncorrectClick}
          disabled={submitting}
        >
          👎 No, era otro
        </button>
      </div>

      <style>{styles}</style>
    </div>
  )
}

const styles = `
  .feedback-prompt {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 12px 16px;
    margin: 12px 0;
    font-size: 14px;
  }

  .feedback-prompt--success {
    background: #ecfdf5;
    border-color: #a7f3d0;
    color: #065f46;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .feedback-prompt--correction {
    background: #fffbeb;
    border-color: #fcd34d;
  }

  .feedback-prompt__header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 10px;
    font-weight: 500;
    color: #334155;
  }

  .feedback-prompt__icon {
    font-size: 16px;
  }

  .feedback-prompt__dismiss {
    margin-left: auto;
    background: none;
    border: none;
    font-size: 18px;
    color: #94a3b8;
    cursor: pointer;
    padding: 0;
    line-height: 1;
  }

  .feedback-prompt__dismiss:hover {
    color: #475569;
  }

  .feedback-prompt__info {
    display: flex;
    gap: 16px;
    margin-bottom: 12px;
    font-size: 13px;
    color: #64748b;
  }

  .feedback-prompt__parser strong {
    color: #1e293b;
  }

  .feedback-prompt__error {
    background: #fef2f2;
    border: 1px solid #fecaca;
    color: #991b1b;
    padding: 8px 12px;
    border-radius: 6px;
    margin-bottom: 12px;
    font-size: 13px;
  }

  .feedback-prompt__select {
    width: 100%;
    padding: 10px 12px;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    font-size: 14px;
    margin-bottom: 12px;
    background: white;
  }

  .feedback-prompt__select:focus {
    outline: none;
    border-color: #3b82f6;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
  }

  .feedback-prompt__actions {
    display: flex;
    gap: 8px;
  }

  .feedback-prompt__btn {
    flex: 1;
    padding: 8px 16px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.15s;
    border: 1px solid transparent;
  }

  .feedback-prompt__btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .feedback-prompt__btn--success {
    background: #ecfdf5;
    color: #065f46;
    border-color: #a7f3d0;
  }

  .feedback-prompt__btn--success:hover:not(:disabled) {
    background: #d1fae5;
  }

  .feedback-prompt__btn--warning {
    background: #fffbeb;
    color: #92400e;
    border-color: #fcd34d;
  }

  .feedback-prompt__btn--warning:hover:not(:disabled) {
    background: #fef3c7;
  }

  .feedback-prompt__btn--primary {
    background: #3b82f6;
    color: white;
  }

  .feedback-prompt__btn--primary:hover:not(:disabled) {
    background: #2563eb;
  }

  .feedback-prompt__btn--secondary {
    background: white;
    color: #475569;
    border-color: #cbd5e1;
  }

  .feedback-prompt__btn--secondary:hover:not(:disabled) {
    background: #f1f5f9;
  }
`

export default FeedbackPrompt
