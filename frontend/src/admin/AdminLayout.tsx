import React from 'react'
import Sidebar from '../components/Sidebar'
import { colors } from '../styles/tokens'

interface AdminLayoutProps {
  children: React.ReactNode
  pendingCount?: number
}

export default function AdminLayout({ children, pendingCount = 0 }: AdminLayoutProps) {
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '260px 1fr',
      minHeight: '100vh',
    }}>
      <Sidebar pendingCount={pendingCount} />
      <main style={{
        overflowY: 'auto',
        background: colors.bg,
        height: '100vh',
      }}>
        {children}
      </main>
    </div>
  )
}
