/**
 * AnalysisResult.tsx
 * Component to display file analysis results
 */

import React from 'react'
import { AnalyzeResponse } from '../services/analyzeApi'

interface AnalysisResultProps {
  result: AnalyzeResponse | null
  loading: boolean
  error: Error | null
  selectedParser: string | null
  onParserChange: (parser: string | null) => void
  onConfirm: () => void
}

const getConfidenceBadgeColor = (confidence: number): string => {
  if (confidence >= 0.8) return '#10b981'
  if (confidence >= 0.6) return '#f59e0b'
  return '#ef4444'
}

const getConfidenceLabel = (confidence: number): string => {
  if (confidence >= 0.8) return 'High'
  if (confidence >= 0.6) return 'Medium'
  return 'Low'
}

export const AnalysisResult: React.FC<AnalysisResultProps> = ({
  result,
  loading,
  error,
  selectedParser,
  onParserChange,
  onConfirm,
}) => {
  if (loading) {
    return (
      <div className="analysis-result analysis-result--loading">
        <div className="spinner" />
        <p>Analyzing file...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="analysis-result analysis-result--error">
        <div className="icon">!</div>
        <div className="content">
          <p className="title">Analysis error</p>
          <p className="message">{error.message}</p>
        </div>
      </div>
    )
  }

  if (!result) {
    return null
  }

  const confidenceColor = getConfidenceBadgeColor(result.confidence)
  const confidencePercent = Math.round(result.confidence * 100)
  const effectiveParser = selectedParser || result.suggested_parser

  return (
    <div className="analysis-result">
      <div className="analysis-result__header">
        <div className="analysis-result__suggested">
          <h3>Full analysis</h3>
          <p className="doc-type">Type: {result.suggested_doc_type}</p>
        </div>

        <div className="analysis-result__confidence">
          <div className="confidence-badge" style={{ backgroundColor: confidenceColor }}>
            <span className="confidence-percent">{confidencePercent}%</span>
            <span className="confidence-label">{getConfidenceLabel(result.confidence)}</span>
          </div>
        </div>
      </div>

      {result.requires_confirmation && (
        <div className="analysis-result__warning">
          <span className="warning-icon">!</span>
          <span>Low confidence - parser confirmation required</span>
        </div>
      )}

      <div className="analysis-result__explanation">
        <p className="label">Explanation:</p>
        <p className="value">{result.explanation}</p>
      </div>

      <div className="analysis-result__parser-select">
        <label className="label">Selected parser:</label>
        <select
          value={effectiveParser}
          onChange={(e) => onParserChange(e.target.value === result.suggested_parser ? null : e.target.value)}
          className="parser-dropdown"
        >
          <option value={result.suggested_parser}>{result.suggested_parser} (suggested)</option>
          {result.available_parsers
            .filter((p) => p !== result.suggested_parser)
            .map((parser) => (
              <option key={parser} value={parser}>
                {parser}
              </option>
            ))}
        </select>
        {selectedParser && selectedParser !== result.suggested_parser && (
          <span className="override-badge">OVERRIDE</span>
        )}
      </div>

      {result.headers_sample.length > 0 && (
        <div className="analysis-result__headers">
          <p className="label">Detected headers:</p>
          <div className="headers-tags">
            {result.headers_sample.map((header, idx) => (
              <span key={idx} className="header-tag">
                {header}
              </span>
            ))}
          </div>
        </div>
      )}

      {result.mapping_suggestion && Object.keys(result.mapping_suggestion).length > 0 && (
        <div className="analysis-result__mapping">
          <p className="label">Suggested mapping:</p>
          <div className="mapping-list">
            {Object.entries(result.mapping_suggestion).map(([source, target]) => (
              <div key={source} className="mapping-item">
                <span className="source">{source}</span>
                <span className="arrow">-&gt;</span>
                <span className="target">{target}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {result.probabilities && Object.keys(result.probabilities).length > 0 && (
        <div className="analysis-result__probabilities">
          <p className="label">Probabilities:</p>
          <div className="probabilities-list">
            {Object.entries(result.probabilities)
              .sort(([, a], [, b]) => b - a)
              .slice(0, 5)
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

      {result.ai_enhanced && (
        <div className="analysis-result__ai-enhanced">
          <span className="ai-badge">Enhanced with {result.ai_provider || 'AI'}</span>
        </div>
      )}

      {result.decision_log.length > 0 && (
        <details className="analysis-result__decision-log">
          <summary className="label">Decision log ({result.decision_log.length} steps)</summary>
          <div className="log-entries">
            {result.decision_log.map((entry, idx) => (
              <div key={idx} className="log-entry">
                <div className="log-header">
                  <span className="step">{entry.step}</span>
                  {entry.duration_ms !== undefined && <span className="duration">{entry.duration_ms}ms</span>}
                  {entry.confidence !== undefined && <span className="conf">{Math.round(entry.confidence * 100)}%</span>}
                </div>
                <div className="log-time">{entry.timestamp}</div>
              </div>
            ))}
          </div>
        </details>
      )}

      <div className="analysis-result__actions">
        <button className="confirm-btn" onClick={onConfirm}>
          Confirm and continue
        </button>
      </div>

      <style>{`
        .analysis-result {
          border: 1px solid #e5e7eb;
          border-radius: 8px;
          padding: 16px;
          background: #f9fafb;
          margin: 16px 0;
        }

        .analysis-result--loading {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 12px;
          min-height: 100px;
        }

        .analysis-result--error {
          border-color: #fee2e2;
          background: #fef2f2;
          display: flex;
          gap: 12px;
          align-items: flex-start;
        }

        .analysis-result--error .icon {
          font-size: 20px;
          flex-shrink: 0;
        }

        .analysis-result--error .title {
          color: #991b1b;
          font-weight: 600;
          margin: 0;
        }

        .analysis-result--error .message {
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

        .analysis-result__header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 16px;
          gap: 16px;
        }

        .analysis-result__suggested h3 {
          margin: 0;
          font-size: 18px;
          font-weight: 700;
          color: #1f2937;
        }

        .doc-type {
          margin: 4px 0 0;
          font-size: 14px;
          color: #6b7280;
        }

        .confidence-badge {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          width: 70px;
          height: 70px;
          border-radius: 50%;
          color: white;
          font-weight: 600;
        }

        .confidence-percent {
          font-size: 20px;
        }

        .confidence-label {
          font-size: 11px;
          margin-top: 2px;
          opacity: 0.9;
        }

        .analysis-result__warning {
          background: #fef3c7;
          border: 1px solid #f59e0b;
          border-radius: 6px;
          padding: 10px 14px;
          margin-bottom: 16px;
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 14px;
          color: #92400e;
        }

        .warning-icon {
          font-size: 16px;
        }

        .analysis-result__explanation,
        .analysis-result__headers,
        .analysis-result__mapping,
        .analysis-result__probabilities {
          margin-bottom: 16px;
        }

        .label {
          display: block;
          font-size: 12px;
          font-weight: 600;
          color: #6b7280;
          margin-bottom: 8px;
          text-transform: uppercase;
        }

        .analysis-result__explanation .value {
          margin: 0;
          color: #374151;
          font-size: 14px;
          line-height: 1.5;
        }

        .analysis-result__parser-select {
          margin-bottom: 16px;
          display: flex;
          align-items: center;
          gap: 12px;
          flex-wrap: wrap;
        }

        .parser-dropdown {
          flex: 1;
          min-width: 200px;
          padding: 8px 12px;
          border: 1px solid #d1d5db;
          border-radius: 6px;
          font-size: 14px;
          background: white;
        }

        .override-badge {
          background: #fef3c7;
          color: #92400e;
          padding: 4px 10px;
          border-radius: 4px;
          font-size: 12px;
          font-weight: 600;
        }

        .headers-tags {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
        }

        .header-tag {
          display: inline-block;
          background: #e0e7ff;
          color: #3730a3;
          padding: 4px 10px;
          border-radius: 4px;
          font-size: 12px;
          font-weight: 500;
        }

        .mapping-list {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }

        .mapping-item {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 13px;
        }

        .mapping-item .source {
          color: #6b7280;
          font-family: monospace;
        }

        .mapping-item .arrow {
          color: #9ca3af;
        }

        .mapping-item .target {
          color: #059669;
          font-weight: 500;
          font-family: monospace;
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
        }

        .probability-item .percent {
          text-align: right;
          color: #6b7280;
          font-weight: 600;
        }

        .analysis-result__ai-enhanced {
          margin-bottom: 16px;
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

        .analysis-result__decision-log {
          margin-bottom: 16px;
          border: 1px solid #e5e7eb;
          border-radius: 6px;
          background: white;
        }

        .analysis-result__decision-log summary {
          padding: 10px 14px;
          cursor: pointer;
          font-size: 12px;
          font-weight: 600;
          color: #6b7280;
          text-transform: uppercase;
        }

        .log-entries {
          padding: 0 14px 14px;
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .log-entry {
          padding: 8px;
          background: #f9fafb;
          border-radius: 4px;
          font-size: 12px;
        }

        .log-header {
          display: flex;
          gap: 10px;
          align-items: center;
        }

        .log-entry .step {
          font-weight: 600;
          color: #374151;
        }

        .log-entry .duration {
          color: #6b7280;
        }

        .log-entry .conf {
          color: #059669;
        }

        .log-time {
          color: #9ca3af;
          font-size: 11px;
          margin-top: 4px;
        }

        .analysis-result__actions {
          display: flex;
          justify-content: flex-end;
          padding-top: 16px;
          border-top: 1px solid #e5e7eb;
        }

        .confirm-btn {
          background: #3b82f6;
          color: white;
          border: none;
          padding: 10px 20px;
          border-radius: 6px;
          font-size: 14px;
          font-weight: 500;
          cursor: pointer;
          transition: background 0.2s;
        }

        .confirm-btn:hover {
          background: #2563eb;
        }
      `}</style>
    </div>
  )
}

export default AnalysisResult
