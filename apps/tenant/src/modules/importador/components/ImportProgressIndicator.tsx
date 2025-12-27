/**
 * ImportProgressIndicator - Real-time progress indicator
 */
import React from 'react'
import { ProgressUpdate } from '../hooks/useImportProgress'

interface ImportProgressIndicatorProps {
  progress: ProgressUpdate | null
  progressPercent: number
  isConnected: boolean
  error?: string | null
}

const formatTime = (seconds: number): string => {
  if (seconds < 60) return `${Math.round(seconds)}s`
  const mins = Math.floor(seconds / 60)
  const secs = Math.round(seconds % 60)
  return `${mins}m ${secs}s`
}

export const ImportProgressIndicator: React.FC<ImportProgressIndicatorProps> = ({
  progress,
  progressPercent,
  isConnected,
  error,
}) => {
  if (!progress) {
    return (
      <div className="flex items-center gap-3 p-4 bg-gray-50 border border-gray-200 rounded">
        <div className="spinner" />
        <span className="text-gray-700">Connecting to server...</span>
      </div>
    )
  }

  const getStatusColor = () => {
    switch (progress.status) {
      case 'completed':
        return 'bg-green-50 border-green-200'
      case 'failed':
        return 'bg-red-50 border-red-200'
      case 'processing':
        return 'bg-blue-50 border-blue-200'
      default:
        return 'bg-gray-50 border-gray-200'
    }
  }

  const getStatusIcon = () => {
    switch (progress.status) {
      case 'completed':
        return 'OK'
      case 'failed':
        return 'X'
      case 'processing':
        return '*'
      default:
        return '!'
    }
  }

  const getProgressBarColor = () => {
    if (progress.status === 'completed') return 'bg-green-500'
    if (progress.status === 'failed') return 'bg-red-500'
    if (progressPercent > 75) return 'bg-blue-500'
    if (progressPercent > 50) return 'bg-indigo-500'
    if (progressPercent > 25) return 'bg-amber-500'
    return 'bg-orange-500'
  }

  return (
    <div className={`border rounded-lg p-6 space-y-4 ${getStatusColor()}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-3xl">{getStatusIcon()}</span>
          <div>
            <h3 className="font-bold text-gray-900">Importing...</h3>
            <p className="text-sm text-gray-600">{progress.currentStep}</p>
          </div>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-gray-900">{progressPercent}%</div>
          <div className="text-xs text-gray-600">
            {progress.rowsProcessed} / {progress.totalRows} rows
          </div>
        </div>
      </div>

      <div className="w-full h-3 bg-gray-300 rounded-full overflow-hidden">
        <div
          className={`h-full ${getProgressBarColor()} transition-all duration-500 rounded-full`}
          style={{ width: `${progressPercent}%` }}
        />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="bg-white rounded p-3 text-center">
          <div className="text-xs text-gray-600">Speed</div>
          <div className="text-lg font-bold text-gray-900">{Math.round(progress.speed)} rows/s</div>
        </div>

        <div className="bg-white rounded p-3 text-center">
          <div className="text-xs text-gray-600">Estimated time</div>
          <div className="text-lg font-bold text-gray-900">{formatTime(progress.estimatedTime)}</div>
        </div>

        <div className={`rounded p-3 text-center ${progress.errorCount > 0 ? 'bg-red-100' : 'bg-green-100'}`}>
          <div className="text-xs text-gray-600">Errors</div>
          <div className={`text-lg font-bold ${progress.errorCount > 0 ? 'text-red-700' : 'text-green-700'}`}>
            {progress.errorCount}
          </div>
        </div>

        <div className={`rounded p-3 text-center ${isConnected ? 'bg-green-100' : 'bg-amber-100'}`}>
          <div className="text-xs text-gray-600">Connection</div>
          <div
            className={`text-lg font-bold flex items-center justify-center gap-1 ${
              isConnected ? 'text-green-700' : 'text-amber-700'
            }`}
          >
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-600' : 'bg-amber-600'}`} />
            {isConnected ? 'Active' : 'Lost'}
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded p-3 text-red-700 text-sm">
          <strong>Error:</strong> {error}
        </div>
      )}

      {progress.errors && progress.errors.length > 0 && (
        <div className="bg-white rounded p-3 border border-gray-200">
          <div className="text-xs font-bold text-gray-700 mb-2">Recent errors ({progress.errors.length})</div>
          <div className="space-y-1 max-h-24 overflow-y-auto">
            {progress.errors.slice(-3).map((err, idx) => (
              <div key={idx} className="text-xs text-gray-600 border-l-2 border-red-400 pl-2">
                <strong>Row {err.row}:</strong> {err.message}
              </div>
            ))}
          </div>
        </div>
      )}

      {progress.status === 'completed' && (
        <div className="bg-green-100 border border-green-300 rounded p-3 text-green-800 text-sm">
          <strong>Import completed successfully</strong>
        </div>
      )}

      {progress.status === 'failed' && (
        <div className="bg-red-100 border border-red-300 rounded p-3 text-red-800 text-sm">
          <strong>Import failed</strong>
          <p className="text-xs mt-1">Review the errors above for more details</p>
        </div>
      )}

      <style>{`
        .spinner {
          width: 20px;
          height: 20px;
          border: 2px solid #e5e7eb;
          border-top-color: #3b82f6;
          border-radius: 50%;
          animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}
