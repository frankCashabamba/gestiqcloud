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

const SIZE_PX: Record<Size, number> = { sm: 40, md: 48, lg: 64 }

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
    <Link to={href} className="admin-card-link">
      <div className="admin-card-link__icon" style={{ width: s, height: s }}>
        {iconSrc ? (
          <img src={iconSrc} alt={title} className="admin-card-link__img" />
        ) : (
          <span style={{ fontSize: s * 0.55 }}>{iconEmoji ?? '📦'}</span>
        )}
      </div>
      <h3 className="admin-card-link__title">{title}</h3>
      <p className="admin-card-link__desc">{description}</p>
    </Link>
  )
}
