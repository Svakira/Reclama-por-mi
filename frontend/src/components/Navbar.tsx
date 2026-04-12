// frontend/src/components/Navbar.tsx
import React from 'react'
import { colors } from '../styles/tokens'

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
      background: colors.primary,
      height: 56,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 32px',
      boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
    },
    logo: {
      fontSize: 20,
      fontWeight: 700,
      color: '#ffffff',
      letterSpacing: '-0.3px',
      textDecoration: 'none',
    },
    links: {
      display: 'flex',
      gap: 24,
      alignItems: 'center',
    },
    link: {
      color: 'rgba(255,255,255,0.85)',
      textDecoration: 'none',
      fontSize: 14,
      fontWeight: 500,
    },
  }

  return (
    <nav style={s.nav}>
      <a href="/app" style={s.logo}>⚖️ JusticIA</a>
      {links.length > 0 && (
        <div style={s.links}>
          {links.map((l) => (
            <a key={l.href} href={l.href} style={s.link}>{l.label}</a>
          ))}
        </div>
      )}
    </nav>
  )
}
