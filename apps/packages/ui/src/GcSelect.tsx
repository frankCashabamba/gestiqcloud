import React from 'react'

export interface GcSelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string
  error?: string
  hint?: string
  required?: boolean
  options?: Array<{ value: string; label: string }>
}

export const GcSelect = React.forwardRef<HTMLSelectElement, GcSelectProps>(
  ({ label, error, hint, required, options, children, className = '', id, ...props }, ref) => {
    const selectId = id || props.name
    return (
      <div className="gc-field">
        {label && (
          <label htmlFor={selectId} className="gc-label">
            {label}
            {required && <span className="ml-1 text-red-500">*</span>}
          </label>
        )}
        <select
          ref={ref}
          id={selectId}
          className={`gc-input gc-select ${error ? 'gc-input--error' : ''} ${className}`}
          aria-invalid={!!error}
          {...props}
        >
          {options
            ? options.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))
            : children}
        </select>
        {error && <p className="gc-field-error">{error}</p>}
        {hint && !error && <p className="gc-field-hint">{hint}</p>}
      </div>
    )
  }
)
GcSelect.displayName = 'GcSelect'
