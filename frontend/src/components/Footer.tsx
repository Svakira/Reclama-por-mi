// frontend/src/components/Footer.tsx
import React from 'react'
import { colors } from '../styles/tokens'

export default function Footer() {
  const s: React.CSSProperties = {
    background: colors.primaryDark,
    color: 'rgba(255,255,255,0.6)',
    fontSize: 13,
    textAlign: 'center',
    padding: '14px 32px',
    marginTop: 'auto',
  }
  return (
    <footer style={s}>
      © 2026 Clínica Jurídica ICESI · Superintendencia de Industria y Comercio · Ley 1480 de 2011
    </footer>
  )
}
