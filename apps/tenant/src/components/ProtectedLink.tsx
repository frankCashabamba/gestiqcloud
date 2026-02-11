import React from 'react'
import { Link, LinkProps } from 'react-router-dom'
import { usePermission } from '../hooks/usePermission'

export interface ProtectedLinkProps extends LinkProps {
  permission: string
  action?: string
  fallback?: React.ReactNode
}

export default function ProtectedLink({
  permission,
  action,
  fallback,
  children,
  ...rest
}: ProtectedLinkProps) {
  const can = usePermission()

  if (!can(permission, action)) {
    return fallback ? <>{fallback}</> : <span style={{ color: '#999' }}>{children}</span>
  }

  return <Link {...rest}>{children}</Link>
}
