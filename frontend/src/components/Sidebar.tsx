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
  const initials = lawyerName.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()

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
        { label: 'Aprobados', path: '/admin/approved' },
        { label: 'Cerrados', path: '/admin/closed' },
      ],
    },
    {
      title: 'Gestión',
      items: [
        { label: 'Mis casos', path: '/admin/my-cases' },
        { label: 'Reportes', path: '/admin/reports' },
        { label: 'Configuración', path: '/admin/settings' },
      ],
    },
  ]

  const s: Record<string, React.CSSProperties> = {
    sidebar: {
      width: 260,
      minWidth: 260,
      background: colors.darkBg,
      color: '#fff',
      padding: '24px',
      position: 'relative',
      height: '100vh',
      overflowY: 'auto',
      borderRight: '1px solid rgba(255,255,255,0.1)',
      fontFamily: typography.body,
      display: 'flex',
      flexDirection: 'column',
    },
    logo: {
      display: 'flex',
      alignItems: 'center',
      gap: 12,
      marginBottom: 32,
      fontWeight: 700,
      fontSize: 16,
    },
    logoIcon: {
      width: 32,
      height: 32,
      borderRadius: 6,
      background: '#fff',
      overflow: 'hidden',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
    },
    logoImg: {
      width: '100%',
      height: '100%',
      objectFit: 'cover',
      display: 'block',
    },
    sectionTitle: {
      fontSize: 11,
      fontWeight: 700,
      textTransform: 'uppercase',
      color: 'rgba(255,255,255,0.5)',
      margin: '0 0 12px 0',
      letterSpacing: 0.5,
    },
    navWrap: { marginBottom: 32 },
    badge: {
      marginLeft: 'auto',
      background: colors.danger,
      color: '#fff',
      borderRadius: 10,
      padding: '1px 8px',
      fontSize: 11,
      fontWeight: 700,
    },
    userSection: {
      marginTop: 'auto',
      paddingTop: 24,
      borderTop: '1px solid rgba(255,255,255,0.2)',
    },
    userInfo: {
      display: 'flex',
      alignItems: 'center',
      gap: 12,
      marginBottom: 12,
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
      border: '1px solid rgba(255,255,255,0.2)',
      borderRadius: 6,
      background: 'transparent',
      color: 'rgba(255,255,255,0.8)',
      padding: '10px 0',
      cursor: 'pointer',
      fontSize: 12,
      fontWeight: 500,
      fontFamily: typography.body,
      transition: 'all 0.3s ease',
    },
  }

  const navItemStyle = (active: boolean, disabled: boolean): React.CSSProperties => ({
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    padding: '14px 16px',
    borderRadius: 8,
    marginBottom: 8,
    cursor: disabled ? 'not-allowed' : 'pointer',
    color: disabled ? 'rgba(255,255,255,0.38)' : active ? '#fff' : 'rgba(255,255,255,0.8)',
    background: active ? colors.primary : 'transparent',
    border: active ? `1px solid ${colors.primary}` : '1px solid transparent',
    fontSize: 13,
    fontWeight: 500,
    opacity: disabled ? 0.65 : 1,
    transition: 'all 0.3s ease',
  })

  return (
    <aside style={s.sidebar}>
      <div style={s.logo}>
        <div style={s.logoIcon}>
          <img src="/logo-icon.png" alt="RECLAMA POR MI" style={s.logoImg} />
        </div>
        <span>RECLAMA POR MI</span>
      </div>

      {navSections.map((section) => (
        <div key={section.title} style={s.navWrap}>
          <div style={s.sectionTitle}>{section.title}</div>
          {section.items.map((item) => {
            const disabled = !item.path
            const active = !!item.path && (
              item.path === '/admin'
                ? location.pathname === '/admin'
                : (location.pathname === item.path || location.pathname.startsWith(`${item.path}/`))
            )
            return (
              <div
                key={item.label}
                style={navItemStyle(active, disabled)}
                onClick={() => { if (item.path) navigate(item.path) }}
                onMouseEnter={(e) => { if (!disabled && !active) e.currentTarget.style.background = 'rgba(255,255,255,0.1)' }}
                onMouseLeave={(e) => { if (!disabled && !active) e.currentTarget.style.background = 'transparent' }}
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
          <div style={s.userAvatar}>{initials}</div>
          <div>
            <div style={s.userName}>{lawyerName}</div>
            <div style={s.userRole}>Abogado · ICESI</div>
          </div>
        </div>
        <button
          style={s.logoutBtn}
          onClick={logout}
          onMouseEnter={(e) => { e.currentTarget.style.borderColor = colors.danger; e.currentTarget.style.color = colors.danger }}
          onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.2)'; e.currentTarget.style.color = 'rgba(255,255,255,0.8)' }}
        >
          Cerrar sesión
        </button>
      </div>
    </aside>
  )
}
