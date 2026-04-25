import React from 'react'

interface Props {
  children: React.ReactNode
  className?: string
}

export default function PageContainerWide({ children, className = '' }: Props) {
  return (
    <div className={`gc-container-wide py-8 ${className}`}>
      {children}
    </div>
  )
}
