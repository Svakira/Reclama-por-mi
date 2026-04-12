// frontend/src/components/Sidebar.tsx
import React from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { colors } from '../styles/tokens'

interface SidebarProps {
  pendingCount?: number
}

export default function Sidebar({ pendingCount = 0 }: SidebarProps) {
  const navigate = useNavigate()
  const location = useLocation()
  const lawyerName = localStorage.getItem('justicia_lawyer_name') || 'Abogado'

  function logout() {
    localStorage.removeItem('justicia_token')
    localStorage.removeItem('justicia_lawyer_name')
    navigate('/admin/login')
  }

  const isQueueActive = location.pathname === '/admin' || location.pathname.startsWith('/admin/cases')

  const s: Record<string, React.CSSProperties> = {
    sidebar: {
      width: 240,
      minWidth: 240,
      background: colors.primary,
      display: 'flex',
      flexDirection: 'column',
      height: '100vh',
      position: 'sticky',
      top: 0,
      overflowY: 'auto',
    },
    logoSection: {
      padding: '20px 20px 16px',
      borderBottom: '1px solid rgba(255,255,255,0.1)',
    },
    logoText: {
      fontSize: 18,
      fontWeight: 700,
      color: '#ffffff',
    },
    logoSub: {
      fontSize: 11,
      color: 'rgba(255,255,255,0.5)',
      marginTop: 2,
    },
    nav: {
      flex: 1,
      padding: '12px 0',
    },
    badge: {
      marginLeft: 'auto',
      background: colors.danger,
      color: '#fff',
      borderRadius: 10,
      padding: '1px 7px',
      fontSize: 11,
      fontWeight: 700,
    },
    footer: {
      padding: '16px 20px',
      borderTop: '1px solid rgba(255,255,255,0.1)',
    },
    avatar: {
      display: 'flex',
      alignItems: 'center',
      gap: 10,
      marginBottom: 10,
    },
    avatarCircle: {
      width: 32,
      height: 32,
      borderRadius: '50%',
      background: 'rgba(255,255,255,0.2)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontSize: 14,
      color: '#fff',
      fontWeight: 700,
      flexShrink: 0,
    },
    avatarName: {
      fontSize: 13,
      color: '#ffffff',
      fontWeight: 600,
    },
    avatarRole: {
      fontSize: 11,
      color: 'rgba(255,255,255,0.5)',
    },
    logoutBtn: {
      width: '100%',
      background: 'rgba(255,255,255,0.08)',
      border: '1px solid rgba(255,255,255,0.15)',
      borderRadius: 6,
      padding: '8px 0',
      color: 'rgba(255,255,255,0.7)',
      cursor: 'pointer',
      fontSize: 13,
    },
  }

  const navItemStyle = (active: boolean): React.CSSProperties => ({
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    padding: '10px 20px',
    cursor: 'pointer',
    color: active ? '#ffffff' : 'rgba(255,255,255,0.7)',
    background: active ? 'rgba(255,255,255,0.15)' : 'transparent',
    borderLeft: active ? '3px solid #ffffff' : '3px solid transparent',
    fontSize: 14,
    fontWeight: active ? 600 : 400,
  })

  return (
    <div style={s.sidebar}>
      <div style={s.logoSection}>
        <div style={s.logoText}>⚖️ JusticIA</div>
        <div style={s.logoSub}>Panel del Abogado</div>
      </div>

      <nav style={s.nav}>
        <div
          style={navItemStyle(isQueueActive)}
          onClick={() => navigate('/admin')}
        >
          <span>📋</span>
          <span>Cola de revisión</span>
          {pendingCount > 0 && <span style={s.badge}>{pendingCount}</span>}
        </div>
      </nav>

      <div style={s.footer}>
        <div style={s.avatar}>
          <div style={s.avatarCircle}>{lawyerName.charAt(0).toUpperCase()}</div>
          <div>
            <div style={s.avatarName}>{lawyerName}</div>
            <div style={s.avatarRole}>Abogado · ICESI</div>
          </div>
        </div>
        <button style={s.logoutBtn} onClick={logout}>Cerrar sesión</button>
      </div>
    </div>
  )
}
