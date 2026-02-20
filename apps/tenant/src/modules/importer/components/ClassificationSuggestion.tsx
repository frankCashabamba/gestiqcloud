// src/modules/importer/components/ClassificationSuggestion.tsx
// UI for file classification suggestions

import React from 'react'
import { ClassifyResponse } from '../services/classifyApi'

interface ClassificationSuggestionProps {
  result: ClassifyResponse | null
  loading: boolean
  error: Error | null
  confidence: 'high' | 'medium' | 'low' | null
}

const getConfidenceBadgeColor = (confidence: 'high' | 'medium' | 'low' | null) => {
  switch (confidence) {
    case 'high':
      return '#10b981'
    case 'medium':
      return '#f59e0b'
    case 'low':
    default:
      return '#ef4444'
  }
}

const getConfidenceLabel = (confidence: 'high' | 'medium' | 'low' | null) => {
  switch (confidence) {
    case 'high':
      return 'High'
    case 'medium':
      return 'Medium'
    case 'low':
      return 'Low'
    default:
      return 'N/A'
  }
}

export const ClassificationSuggestion: React.FC<ClassificationSuggestionProps> = ({
  result,
  loading,
  error,
  confidence,
}) => {
  if (loading) {
    return (
      <div className="classification-suggestion classification-suggestion--loading">
        <div className="spinner" />
        <p>Classifying file...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="classification-suggestion classification-suggestion--error">
        <div className="icon">!</div>
        <div className="content">
          <p className="title">Classification error</p>
          <p className="message">{error.message}</p>
        </div>
      </div>
    )
  }

  if (!result) {
    return null
  }

  const confidenceColor = getConfidenceBadgeColor(confidence)
  const confidencePercent = Math.round(result.confidence * 100)

  return (
    <div className="classification-suggestion">
      <div className="classification-suggestion__header">
        <div className="classification-suggestion__suggested-parser">
          <h3>Suggested parser</h3>
          <p className="parser-name">{result.suggested_parser}</p>
        </div>

        <div className="classification-suggestion__confidence">
          <div className="confidence-badge" style={{ backgroundColor: confidenceColor }}>
            <span className="confidence-percent">{confidencePercent}%</span>
            <span className="confidence-label">{getConfidenceLabel(confidence)}</span>
          </div>
        </div>
      </div>

      {result.reason && (
        <div className="classification-suggestion__reason">
          <p className="label">Reason:</p>
          <p className="value">{result.reason}</p>
        </div>
      )}

      {result.enhanced_by_ai && (
        <div className="classification-suggestion__ai-enhanced">
          <span className="ai-badge">Enhanced with {result.ai_provider || 'AI'}</span>
        </div>
      )}

      {result.probabilities && Object.keys(result.probabilities).length > 0 && (
        <div className="classification-suggestion__probabilities">
          <p className="label">Parser probabilities:</p>
          <div className="probabilities-list">
            {Object.entries(result.probabilities)
              .sort(([, a], [, b]) => b - a)
              .slice(0, 6)
              .map(([parser, prob]) => (
                <div key={parser} className="probability-item">
                  <span className="parser">{parser}</span>
                  <div className="bar-container">
                    <div className="bar" style={{ width: `${prob * 100}%` }} />
                  </div>
                  <span className="percent">{Math.round(prob * 100)}%</span>
                </div>
              ))}
          </div>
        </div>
      )}

      {result.available_parsers && result.available_parsers.length > 0 && (
        <div className="classification-suggestion__available">
          <p className="label">Available parsers:</p>
          <div className="parsers-tags">
            {result.available_parsers.map((parser) => (
              <span key={parser} className="parser-tag">
                {parser}
              </span>
            ))}
          </div>
        </div>
      )}

      <style>{`
        .classification-suggestion {
          border: 1px solid #e5e7eb;
          border-radius: 8px;
          padding: 16px;
          background: #f9fafb;
          margin: 16px 0;
        }

        .classification-suggestion--loading {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 12px;
          min-height: 100px;
        }

        .classification-suggestion--error {
          border-color: #fee2e2;
          background: #fef2f2;
          display: flex;
          gap: 12px;
          align-items: flex-start;
        }

        .classification-suggestion--error .icon {
          font-size: 20px;
          flex-shrink: 0;
        }

        .classification-suggestion--error .title {
          color: #991b1b;
          font-weight: 600;
          margin: 0;
        }

        .classification-suggestion--error .message {
          color: #7f1d1d;
          margin: 4px 0 0;
          font-size: 14px;
        }

        .spinner {
          width: 24px;
          height: 24px;
          border: 3px solid #e5e7eb;
          border-top-color: #3b82f6;
          border-radius: 50%;
          animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
          to { transform: rotate(360deg); }
        }

        .classification-suggestion__header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 16px;
          gap: 16px;
        }

        .classification-suggestion__suggested-parser h3 {
          margin: 0;
          font-size: 12px;
          color: #6b7280;
          text-transform: uppercase;
          font-weight: 600;
        }

        .parser-name {
          margin: 4px 0 0;
          font-size: 18px;
          font-weight: 700;
          color: #1f2937;
        }

        .confidence-badge {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          width: 80px;
          height: 80px;
          border-radius: 50%;
          color: white;
          font-weight: 600;
        }

        .confidence-percent {
          font-size: 24px;
        }

        .confidence-label {
          font-size: 12px;
          margin-top: 4px;
          opacity: 0.9;
        }

        .classification-suggestion__reason {
          margin-bottom: 12px;
        }

        .classification-suggestion__reason .label,
        .classification-suggestion__probabilities .label,
        .classification-suggestion__available .label {
          display: block;
          font-size: 12px;
          font-weight: 600;
          color: #6b7280;
          margin-bottom: 8px;
          text-transform: uppercase;
        }

        .classification-suggestion__reason .value {
          margin: 0;
          color: #374151;
          font-size: 14px;
        }

        .classification-suggestion__ai-enhanced {
          margin-bottom: 12px;
        }

        .ai-badge {
          display: inline-block;
          background: #dbeafe;
          color: #0c4a6e;
          padding: 4px 12px;
          border-radius: 12px;
          font-size: 12px;
          font-weight: 500;
        }

        .probabilities-list {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .probability-item {
          display: grid;
          grid-template-columns: 120px 1fr 50px;
          align-items: center;
          gap: 8px;
          font-size: 12px;
        }

        .probability-item .parser {
          color: #374151;
          font-weight: 500;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .bar-container {
          height: 6px;
          background: #e5e7eb;
          border-radius: 3px;
          overflow: hidden;
        }

        .bar {
          height: 100%;
          background: #3b82f6;
          border-radius: 3px;
          transition: width 0.3s ease;
        }

        .probability-item .percent {
          text-align: right;
          color: #6b7280;
          font-weight: 600;
        }

        .parsers-tags {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
        }

        .parser-tag {
          display: inline-block;
          background: #e0e7ff;
          color: #3730a3;
          padding: 6px 12px;
          border-radius: 6px;
          font-size: 12px;
          font-weight: 500;
        }
      `}</style>
    </div>
  )
}
