import React from 'react'
import { Link } from 'react-router-dom'

type Size = 'sm' | 'md' | 'lg'
interface AdminCardProps {
  href: string
  iconSrc?: string
  iconEmoji?: string
  title: string
  description: string
  iconSize?: Size
}

const SIZE_PX: Record<Size, number> = { sm: 40, md: 56, lg: 80 }

export const AdminCard: React.FC<AdminCardProps> = ({
  href,
  iconSrc,
  iconEmoji,
  title,
  description,
  iconSize = 'md',
}) => {
  const s = SIZE_PX[iconSize]

  return (
    <Link
      to={href}
      style={{
        display: 'block',
        padding: 16,
        borderRadius: 16,
        background: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        boxShadow: 'var(--shadow-sm)',
        color: 'inherit',
        textDecoration: 'none',
        textAlign: 'center',
        transition: 'transform .12s, box-shadow .12s',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.transform = 'translateY(-2px)'
        e.currentTarget.style.boxShadow = '0 8px 20px rgba(0,0,0,.08)'
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = ''
        e.currentTarget.style.boxShadow = 'var(--shadow-sm)'
      }}
    >
      <div
        style={{
          width: s,
          height: s,
          borderRadius: '50%',
          overflow: 'hidden',
          display: 'grid',
          placeItems: 'center',
          background: 'var(--color-bg)',
          margin: '0 auto 12px',
        }}
      >
        {iconSrc ? (
          <img
            src={iconSrc}
            alt={title}
            style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block' }}
          />
        ) : (
          <span style={{ fontSize: s * 0.6, lineHeight: 1 }}>{iconEmoji ?? '📦'}</span>
        )}
      </div>

      <h3 style={{ fontWeight: 700, fontSize: 16, margin: '4px 0' }}>{title}</h3>
      <p style={{ fontSize: 13, color: 'var(--color-muted)' }}>{description}</p>
    </Link>
  )
}
