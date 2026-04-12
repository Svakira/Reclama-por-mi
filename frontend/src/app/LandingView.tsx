import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'
import { colors, typography } from '../styles/tokens'

const NAV_LINKS = [
  { label: 'Inicio', href: '#top' },
  { label: 'Como funciona', href: '#steps' },
  { label: 'Nosotros', href: '#benefits' },
  { label: 'Reclamar ahora', href: '/app/chat' },
]

export default function LandingView() {
  const navigate = useNavigate()
  const [isMobile, setIsMobile] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false
    return window.innerWidth <= 1024
  })

  useEffect(() => {
    function onResize() {
      setIsMobile(window.innerWidth <= 1024)
    }
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  const s: Record<string, React.CSSProperties> = {
    page: { minHeight: '100vh', background: colors.surface, color: colors.text },
    container: { maxWidth: 1400, margin: '0 auto', padding: '0 2rem' },
    hero: {
      padding: '4rem 2rem',
      background: colors.surface,
      display: 'grid',
      gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr',
      gap: '4rem',
      alignItems: 'center',
    },
    sectionLabel: {
      fontSize: 12,
      fontWeight: 700,
      textTransform: 'uppercase',
      letterSpacing: 1,
      color: colors.accent,
      marginBottom: 16,
      display: 'block',
    },
    heroTitle: {
      fontFamily: typography.display,
      fontSize: 'clamp(2.2rem, 6vw, 3.5rem)',
      fontWeight: 400,
      lineHeight: 1.1,
      marginBottom: 20,
      color: colors.text,
    },
    heroText: {
      fontSize: 16,
      color: colors.neutral800,
      lineHeight: 1.8,
      marginBottom: 24,
      maxWidth: 620,
    },
    heroBtns: { display: 'flex', gap: 12, flexWrap: 'wrap' },
    btnPrimary: {
      background: colors.primary,
      color: '#fff',
      padding: '12px 28px',
      borderRadius: 20,
      fontWeight: 600,
      border: 'none',
      cursor: 'pointer',
      fontSize: 14,
    },
    btnSecondary: {
      background: '#fff',
      color: colors.neutral800,
      padding: '12px 28px',
      borderRadius: 20,
      fontWeight: 600,
      border: `1px solid ${colors.neutral100}`,
      cursor: 'pointer',
      fontSize: 14,
    },
    featureBox: {
      background: colors.neutral50,
      border: `1px solid ${colors.neutral100}`,
      borderRadius: 16,
      padding: '2rem',
    },
    featureBoxTitle: {
      margin: '0 0 1rem 0',
      fontSize: 20,
      fontWeight: 700,
      color: colors.text,
    },
    featureRow: { display: 'flex', gap: 12, marginBottom: 14, alignItems: 'flex-start' },
    featureDot: {
      width: 20,
      height: 20,
      borderRadius: '50%',
      background: colors.primary,
      color: '#fff',
      fontWeight: 700,
      fontSize: 12,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      flexShrink: 0,
      marginTop: 2,
    },
    featureText: { fontSize: 14, color: colors.neutral800, lineHeight: 1.6 },
    sectionWrap: { padding: '4rem 0' },
    displayTitle: {
      fontFamily: typography.display,
      fontSize: 'clamp(2rem, 5vw, 2.5rem)',
      fontWeight: 400,
      marginBottom: 40,
      color: colors.text,
    },
    stepsGrid: {
      display: 'grid',
      gridTemplateColumns: isMobile ? '1fr' : 'repeat(4, 1fr)',
      gap: '2rem',
    },
    stepCard: { textAlign: 'left' },
    stepNum: {
      width: 48,
      height: 48,
      borderRadius: 8,
      border: `1px solid ${colors.neutral100}`,
      background: colors.neutral100,
      color: colors.primary,
      fontWeight: 700,
      fontSize: 18,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      marginBottom: 16,
    },
    stepTitle: { fontSize: 16, fontWeight: 600, marginBottom: 10 },
    stepText: { fontSize: 14, color: colors.textMuted, lineHeight: 1.6 },
    featuresSection: {
      borderTop: `1px solid ${colors.neutral100}`,
      marginTop: 24,
    },
    benefitsGrid: {
      display: 'grid',
      gridTemplateColumns: isMobile ? '1fr' : 'repeat(3, 1fr)',
      gap: '2.2rem',
    },
    benefitTitle: { fontSize: 16, fontWeight: 600, marginBottom: 8 },
    benefitText: { fontSize: 14, color: colors.textMuted, lineHeight: 1.6 },
    ctaSection: {
      marginTop: 32,
      borderRadius: 16,
      background: colors.primary,
      color: '#fff',
      padding: '4rem 2rem',
    },
    ctaTitle: {
      fontFamily: typography.display,
      fontSize: 'clamp(2rem, 5vw, 2.5rem)',
      fontWeight: 400,
      marginBottom: 12,
    },
    ctaText: { fontSize: 16, lineHeight: 1.6, opacity: 0.95, marginBottom: 20, maxWidth: 780 },
    ctaBtn: {
      border: 'none',
      borderRadius: 20,
      background: '#fff',
      color: colors.primary,
      padding: '12px 28px',
      fontSize: 14,
      fontWeight: 600,
      cursor: 'pointer',
    },
  }

  return (
    <div style={s.page} id="top">
      <Navbar links={NAV_LINKS} />

      <section style={s.hero}>
        <div>
          <span style={s.sectionLabel}>Defiende tus derechos</span>
          <h1 style={s.heroTitle}>RECLAMA POR MI: reclamaciones legales automaticas.</h1>
          <p style={s.heroText}>
            Si tienes un problema con un producto o servicio, te ayudamos a preparar tu reclamacion formal.
            Un abogado la verifica y te entregamos el PDF final listo para presentarlo ante la SIC.
          </p>
          <div style={s.heroBtns}>
            <button style={s.btnPrimary} onClick={() => navigate('/app/chat')}>Iniciar mi caso</button>
            <button style={s.btnSecondary}>Ir a contacto</button>
          </div>
        </div>

        <div style={s.featureBox}>
          <h3 style={s.featureBoxTitle}>Que hacemos por ti?</h3>
          {[
            'Revision legal experta de tu caso',
            'Documentos preparados profesionalmente',
            'PDF final listo para presentar ante la SIC',
            'Seguimiento completo del caso',
            'Servicio 100% gratuito',
          ].map((t) => (
            <div style={s.featureRow} key={t}>
              <div style={s.featureDot}>✓</div>
              <div style={s.featureText}>{t}</div>
            </div>
          ))}
        </div>
      </section>

      <div style={s.container}>
        <section style={s.sectionWrap} id="steps">
          <span style={s.sectionLabel}>Proceso simple</span>
          <h2 style={s.displayTitle}>Cuatro pasos para resolver tu problema</h2>
          <div style={s.stepsGrid}>
            {[
              ['Cuentanos tu caso', 'Describe que paso con tu compra o servicio. Nuestro asistente te guia con preguntas claras.'],
              ['Sube evidencia', 'Comparte fotos, facturas, conversaciones y cualquier documento que respalde tu reclamo.'],
              ['Revision legal', 'Nuestro equipo revisa tu caso, valida la reclamacion y prepara los documentos necesarios.'],
              ['Recibes tu PDF final', 'Te enviamos por WhatsApp la reclamacion verificada por abogado, lista para presentarla ante la SIC.'],
            ].map((step, idx) => (
              <div style={s.stepCard} key={step[0]}>
                <div style={s.stepNum}>{idx + 1}</div>
                <h3 style={s.stepTitle}>{step[0]}</h3>
                <p style={s.stepText}>{step[1]}</p>
              </div>
            ))}
          </div>
        </section>

        <section style={{ ...s.sectionWrap, ...s.featuresSection }} id="benefits">
          <span style={s.sectionLabel}>Ventajas</span>
          <h2 style={s.displayTitle}>Por que elegir RECLAMA POR MI</h2>
          <div style={s.benefitsGrid}>
            {[
              ['Completamente seguro', 'Tus datos estan protegidos con estandares robustos de seguridad.'],
              ['Gratis de verdad', 'No hay costos ocultos ni tarifas por transaccion.'],
              ['Rapido y simple', 'Completa tu reclamacion en minutos con guia paso a paso.'],
              ['Respaldo legal', 'Abogados expertos revisan cada caso antes de presentar.'],
              ['Casos validados', 'Alto porcentaje de casos validados con documentacion solida.'],
              ['Panel de control', 'Monitorea tu caso y recibe actualizaciones en cada etapa.'],
            ].map((item) => (
              <div key={item[0]}>
                <h3 style={s.benefitTitle}>{item[0]}</h3>
                <p style={s.benefitText}>{item[1]}</p>
              </div>
            ))}
          </div>
        </section>

        <section style={s.ctaSection}>
          <h2 style={s.ctaTitle}>Necesitas resolver un reclamo?</h2>
          <p style={s.ctaText}>
            No dejes que una mala experiencia quede sin respuesta. Te ayudamos a hacer valer tus derechos como consumidor.
          </p>
          <button style={s.ctaBtn} onClick={() => navigate('/app/chat')}>Comenzar ahora</button>
        </section>
      </div>

      <Footer />
    </div>
  )
}
