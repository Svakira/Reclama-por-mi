import React from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { colors, typography } from '../styles/tokens'

interface SidebarProps {
  pendingCount?: number
}

interface NavItem {
  label: string
  path: string | null
  badge?: number
}

interface NavSection {
  title: string
  items: NavItem[]
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

  const navSections: NavSection[] = [
    {
      title: 'Panel',
      items: [
        { label: 'Cola de revisión', path: '/admin', badge: pendingCount },
      ],
    },
    {
      title: 'Gestión',
      items: [
        { label: 'Datos', path: '/admin/data' },
        { label: 'Reportes', path: null },
        { label: 'Configuración', path: null },
      ],
    },
  ]

  const s: Record<string, React.CSSProperties> = {
    sidebar: {
      width: 260,
      minWidth: 260,
      background: '#1E3A56',
      color: '#fff',
      padding: '24px 20px',
      position: 'sticky',
      top: 0,
      height: '100vh',
      overflowY: 'auto',
      borderRight: '1px solid rgba(255,255,255,0.08)',
      fontFamily: typography.body,
    },
    logo: {
      display: 'flex',
      alignItems: 'center',
      gap: 12,
      marginBottom: 28,
      fontWeight: 700,
      fontSize: 16,
    },
    logoIcon: {
      width: 32,
      height: 32,
      borderRadius: 6,
      background: colors.primaryLight,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      color: '#fff',
      fontWeight: 800,
      fontSize: 16,
    },
    sectionTitle: {
      fontSize: 11,
      fontWeight: 700,
      textTransform: 'uppercase',
      color: 'rgba(255,255,255,0.52)',
      margin: '0 0 10px 0',
      letterSpacing: 0.5,
    },
    navWrap: { marginBottom: 26 },
    badge: {
      marginLeft: 'auto',
      background: '#B42318',
      color: '#fff',
      borderRadius: 10,
      padding: '1px 8px',
      fontSize: 11,
      fontWeight: 700,
    },
    userSection: {
      marginTop: 18,
      paddingTop: 16,
      borderTop: '1px solid rgba(255,255,255,0.15)',
    },
    userInfo: {
      display: 'flex',
      alignItems: 'center',
      gap: 10,
      marginBottom: 10,
    },
    userAvatar: {
      width: 36,
      height: 36,
      borderRadius: 6,
      background: colors.primary,
      color: '#fff',
      fontSize: 12,
      fontWeight: 700,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      flexShrink: 0,
    },
    userName: { fontSize: 12, fontWeight: 600, marginBottom: 1 },
    userRole: { fontSize: 11, color: 'rgba(255,255,255,0.6)' },
    logoutBtn: {
      width: '100%',
      border: '1px solid rgba(255,255,255,0.22)',
      borderRadius: 6,
      background: 'transparent',
      color: 'rgba(255,255,255,0.85)',
      padding: '8px 0',
      cursor: 'pointer',
      fontSize: 12,
      fontWeight: 500,
      fontFamily: typography.body,
    },
  }

  const navItemStyle = (active: boolean, disabled: boolean): React.CSSProperties => ({
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    padding: '10px 12px',
    borderRadius: 8,
    marginBottom: 6,
    cursor: disabled ? 'not-allowed' : 'pointer',
    color: disabled ? 'rgba(255,255,255,0.38)' : active ? '#fff' : 'rgba(255,255,255,0.8)',
    background: active ? colors.primary : 'transparent',
    border: active ? `1px solid ${colors.primaryLight}` : '1px solid transparent',
    fontSize: 13,
    fontWeight: active ? 600 : 500,
    opacity: disabled ? 0.65 : 1,
  })

  return (
    <aside style={s.sidebar}>
      <div style={s.logo}>
        <div style={s.logoIcon}>J</div>
        <span>JusticIA</span>
      </div>

      {navSections.map((section) => (
        <div key={section.title} style={s.navWrap}>
          <div style={s.sectionTitle}>{section.title}</div>
          {section.items.map((item) => {
            const disabled = !item.path
            const active = !!item.path && (location.pathname === item.path || location.pathname.startsWith(`${item.path}/`))
            return (
              <div
                key={item.label}
                style={navItemStyle(active, disabled)}
                onClick={() => { if (item.path) navigate(item.path) }}
              >
                <span>{item.label}</span>
                {!!item.badge && item.badge > 0 && <span style={s.badge}>{item.badge}</span>}
              </div>
            )
          })}
        </div>
      ))}

      <div style={s.userSection}>
        <div style={s.userInfo}>
          <div style={s.userAvatar}>{lawyerName.charAt(0).toUpperCase()}</div>
          <div>
            <div style={s.userName}>{lawyerName}</div>
            <div style={s.userRole}>Abogado · ICESI</div>
          </div>
        </div>
        <button style={s.logoutBtn} onClick={logout}>Cerrar sesión</button>
      </div>
    </aside>
  )
}
