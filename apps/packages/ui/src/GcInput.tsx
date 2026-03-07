import React from 'react'

export interface GcInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  hint?: string
  required?: boolean
}

export const GcInput = React.forwardRef<HTMLInputElement, GcInputProps>(
  ({ label, error, hint, required, className = '', id, ...props }, ref) => {
    const inputId = id || props.name
    return (
      <div className="gc-field">
        {label && (
          <label htmlFor={inputId} className="gc-label">
            {label}
            {required && <span className="ml-1 text-red-500">*</span>}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
          className={`gc-input ${error ? 'gc-input--error' : ''} ${className}`}
          aria-invalid={!!error}
          aria-describedby={error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined}
          {...props}
        />
        {error && (
          <p id={`${inputId}-error`} className="gc-field-error">{error}</p>
        )}
        {hint && !error && (
          <p id={`${inputId}-hint`} className="gc-field-hint">{hint}</p>
        )}
      </div>
    )
  }
)
GcInput.displayName = 'GcInput'
