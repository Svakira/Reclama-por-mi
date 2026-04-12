// frontend/src/components/Navbar.tsx
import React from 'react'
import { colors, typography } from '../styles/tokens'

interface NavLink {
  label: string
  href: string
}

interface NavbarProps {
  links?: NavLink[]
  leftAction?: {
    label: string
    href?: string
    onClick?: () => void
  }
  contactLabel?: string
}

export default function Navbar({ links = [], leftAction, contactLabel = 'Contactar' }: NavbarProps) {
  const s: Record<string, React.CSSProperties> = {
    nav: {
      position: 'sticky',
      top: 0,
      zIndex: 100,
      background: colors.surface,
      minHeight: 76,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '18px 32px',
      borderBottom: `1px solid ${colors.neutral100}`,
    },
    left: {
      display: 'flex',
      alignItems: 'center',
      gap: 14,
    },
    backBtn: {
      border: `1px solid ${colors.neutral200}`,
      borderRadius: 10,
      background: '#fff',
      color: colors.neutral800,
      padding: '8px 10px',
      fontSize: 12,
      fontWeight: 600,
      textDecoration: 'none',
      cursor: 'pointer',
    },
    logoIconWrap: {
      width: 34,
      height: 34,
      borderRadius: 8,
      overflow: 'hidden',
      border: `1px solid ${colors.neutral200}`,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      flexShrink: 0,
    },
    logoIcon: {
      width: '100%',
      height: '100%',
      objectFit: 'cover',
      display: 'block',
    },
    logo: {
      fontSize: 18,
      fontWeight: 700,
      color: colors.text,
      letterSpacing: '-0.3px',
      textDecoration: 'none',
      fontFamily: typography.body,
    },
    links: {
      display: 'flex',
      gap: 28,
      alignItems: 'center',
    },
    link: {
      color: colors.text,
      textDecoration: 'none',
      fontSize: 14,
      fontWeight: 500,
      position: 'relative',
    },
    cta: {
      border: 'none',
      borderRadius: 20,
      background: colors.accent,
      color: '#fff',
      padding: '10px 20px',
      fontSize: 13,
      fontWeight: 600,
      cursor: 'pointer',
      fontFamily: typography.body,
    },
  }

  return (
    <nav style={s.nav}>
      <div style={s.left}>
        {leftAction && (
          leftAction.href ? (
            <a href={leftAction.href} style={s.backBtn}>{leftAction.label}</a>
          ) : (
            <button style={s.backBtn} onClick={leftAction.onClick}>{leftAction.label}</button>
          )
        )}
        <div style={s.logoIconWrap}>
          <img src="/logo-icon.png" alt="RECLAMA POR MI" style={s.logoIcon} />
        </div>
        <a href="/app" style={s.logo}>RECLAMA POR MI</a>
      </div>
      <div style={s.links}>
        {links.map((l) => (
          <a key={l.href} href={l.href} style={s.link}>{l.label}</a>
        ))}
        <button style={s.cta}>{contactLabel}</button>
      </div>
    </nav>
  )
}
