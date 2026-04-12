// frontend/src/components/Footer.tsx
import React from 'react'
import { colors } from '../styles/tokens'

export default function Footer() {
  const s: Record<string, React.CSSProperties> = {
    footer: {
      background: colors.neutral50,
      borderTop: `1px solid ${colors.neutral100}`,
      marginTop: 'auto',
      padding: '40px 24px 24px',
    },
    grid: {
      maxWidth: 1280,
      margin: '0 auto 24px',
      display: 'grid',
      gap: 24,
      gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
    },
    title: {
      margin: '0 0 10px 0',
      fontSize: 14,
      fontWeight: 700,
      color: colors.text,
    },
    item: {
      display: 'block',
      fontSize: 13,
      color: colors.textMuted,
      textDecoration: 'none',
      marginBottom: 6,
    },
    bottom: {
      maxWidth: 1280,
      margin: '0 auto',
      borderTop: `1px solid ${colors.neutral100}`,
      paddingTop: 16,
      color: colors.textMuted,
      fontSize: 12,
      textAlign: 'center',
    },
  }

  return (
    <footer style={s.footer}>
      <div style={s.grid}>
        <div>
          <h4 style={s.title}>JusticIA</h4>
          <a href="#" style={s.item}>Sobre nosotros</a>
          <a href="#" style={s.item}>Blog</a>
          <a href="#" style={s.item}>Preguntas frecuentes</a>
        </div>
        <div>
          <h4 style={s.title}>Legal</h4>
          <a href="#" style={s.item}>Términos</a>
          <a href="#" style={s.item}>Privacidad</a>
          <a href="#" style={s.item}>Cookies</a>
        </div>
        <div>
          <h4 style={s.title}>Contacto</h4>
          <a href="#" style={s.item}>info@justicia.co</a>
          <a href="#" style={s.item}>+57 (2) 555-1234</a>
          <a href="#" style={s.item}>Chat en vivo</a>
        </div>
        <div>
          <h4 style={s.title}>Síguenos</h4>
          <a href="#" style={s.item}>Facebook</a>
          <a href="#" style={s.item}>Twitter</a>
          <a href="#" style={s.item}>Instagram</a>
        </div>
      </div>
      <div style={s.bottom}>
        © 2026 Clínica Jurídica ICESI · Superintendencia de Industria y Comercio · Ley 1480 de 2011
      </div>
    </footer>
  )
}
