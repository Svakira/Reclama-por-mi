// frontend/src/components/Badge.tsx
import React from 'react'
import { colors } from '../styles/tokens'

type BadgeStatus = 'pending' | 'active' | 'approved' | 'rejected' | 'ready' | 'blocked' | 'info'

const STATUS_COLORS: Record<BadgeStatus, string> = {
  pending: colors.warning,
  active: colors.primary,
  approved: colors.success,
  rejected: colors.danger,
  ready: colors.success,
  blocked: colors.danger,
  info: '#6c757d',
}

interface BadgeProps {
  status: BadgeStatus
  label: string
}

export default function Badge({ status, label }: BadgeProps) {
  const color = STATUS_COLORS[status]
  const style: React.CSSProperties = {
    display: 'inline-block',
    background: color + '22',
    color,
    border: `1px solid ${color}55`,
    borderRadius: 4,
    padding: '3px 8px',
    fontSize: 12,
    fontWeight: 600,
    whiteSpace: 'nowrap',
  }
  return <span style={style}>{label}</span>
}
