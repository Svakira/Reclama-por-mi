// frontend/src/admin/AdminLayout.tsx
import React from 'react'
import Sidebar from '../components/Sidebar'
import { colors } from '../styles/tokens'

interface AdminLayoutProps {
  children: React.ReactNode
  pendingCount?: number
}

export default function AdminLayout({ children, pendingCount = 0 }: AdminLayoutProps) {
  const s: React.CSSProperties = {
    display: 'flex',
    height: '100vh',
    background: colors.bg,
    overflow: 'hidden',
  }
  const main: React.CSSProperties = {
    flex: 1,
    overflowY: 'auto',
    background: colors.bg,
  }

  return (
    <div style={s}>
      <Sidebar pendingCount={pendingCount} />
      <main style={main}>{children}</main>
    </div>
  )
}
