// frontend/src/components/Navbar.tsx
import React from 'react'
import { colors, typography } from '../styles/tokens'

interface NavLink {
  label: string
  href: string
}

interface NavbarProps {
  links?: NavLink[]
}

export default function Navbar({ links = [] }: NavbarProps) {
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
      gap: 12,
    },
    logoIcon: {
      width: 32,
      height: 32,
      borderRadius: 6,
      background: colors.primary,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      color: '#fff',
      fontWeight: 800,
      fontSize: 16,
      flexShrink: 0,
    },
    logo: {
      fontSize: 20,
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
        <div style={s.logoIcon}>J</div>
        <a href="/app" style={s.logo}>JusticIA</a>
      </div>
      <div style={s.links}>
        {links.map((l) => (
          <a key={l.href} href={l.href} style={s.link}>{l.label}</a>
        ))}
        <button style={s.cta}>Contactar</button>
      </div>
    </nav>
  )
}
