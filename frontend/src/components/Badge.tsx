import React from 'react'

type BadgeStatus = 'pending' | 'active' | 'approved' | 'rejected' | 'ready' | 'blocked' | 'info'

const STATUS_COLORS: Record<BadgeStatus, string> = {
  pending: '#B8860B',
  active: '#1A3A5C',
  approved: '#4A6741',
  rejected: '#A73E3E',
  ready: '#4A6741',
  blocked: '#A73E3E',
  info: '#8B8680',
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
    borderRadius: 4,
    padding: '6px 12px',
    fontSize: 11,
    fontWeight: 700,
    textTransform: 'uppercase',
    whiteSpace: 'nowrap',
  }
  return <span style={style}>{label}</span>
}
