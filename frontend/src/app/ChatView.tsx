import React, { useEffect, useRef, useState } from 'react'
import api from '../api/client'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'
import { colors, shadows, typography } from '../styles/tokens'

interface Message {
  role: 'user' | 'assistant'
  text: string
}

const NAV_LINKS = [
  { label: 'Inicio', href: '#top' },
  { label: 'Cómo funciona', href: '#steps' },
  { label: 'Mis casos', href: '/app/status' },
  { label: 'Nosotros', href: '#benefits' },
]

export default function ChatView() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [stage, setStage] = useState('INIT')
  const [caseId, setCaseId] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const chatRef = useRef<HTMLDivElement>(null)

  useEffect(() => { startSession() }, [])
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  async function startSession() {
    try {
      const res = await api.post('/pipeline/start')
      setSessionId(res.data.session_id)
      setStage(res.data.stage)
      setMessages([{ role: 'assistant', text: res.data.agent_reply }])
    } catch {
      setMessages([{ role: 'assistant', text: 'Hola, soy JusticIA. ¿En qué te puedo ayudar hoy?' }])
    }
  }

  async function sendMessage() {
    if (!input.trim() || loading) return
    const text = input.trim()
    setInput('')
    setMessages((m) => [...m, { role: 'user', text }])
    setLoading(true)
    try {
      const res = await api.post('/pipeline/message', { session_id: sessionId, message: text })
      setMessages((m) => [...m, { role: 'assistant', text: res.data.agent_reply }])
      setStage(res.data.stage)
      if (res.data.next_action === 'upload_document') {
        setMessages((m) => [...m, { role: 'assistant', text: 'Por favor sube el documento solicitado usando el botón de adjuntar.' }])
      }
    } catch {
      setMessages((m) => [...m, { role: 'assistant', text: 'Hubo un error. Por favor intenta de nuevo.' }])
    }
    setLoading(false)
  }

  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file || !sessionId) return
    setUploading(true)
    setMessages((m) => [...m, { role: 'user', text: `Subiendo: ${file.name}` }])
    const form = new FormData()
    form.append('session_id', sessionId)
    form.append('file', file)
    form.append('doc_type', 'factura')
    try {
      const res = await api.post('/pipeline/upload', form, { headers: { 'Content-Type': 'multipart/form-data' } })
      if (res.data.blocked) {
        setMessages((m) => [...m, { role: 'assistant', text: 'No pude leer bien ese documento. Un abogado lo revisará manualmente.' }])
      } else {
        setCaseId(res.data.case_id)
        setStage('COMPLETE')
        setMessages((m) => [...m, { role: 'assistant', text: res.data.simple_explanation || `Tu caso fue procesado. Número de referencia: ${res.data.case_id}` }])
      }
    } catch {
      setMessages((m) => [...m, { role: 'assistant', text: 'Error al subir el documento. Por favor intenta de nuevo.' }])
    }
    setUploading(false)
    if (fileRef.current) fileRef.current.value = ''
  }

  function scrollToChat() {
    chatRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const isMobile = typeof window !== 'undefined' ? window.innerWidth <= 1024 : false

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
    chatSection: {
      borderTop: `1px solid ${colors.neutral100}`,
      marginTop: 24,
      paddingTop: '4rem',
    },
    chatTitle: {
      fontFamily: typography.display,
      fontSize: 'clamp(2rem, 5vw, 2.5rem)',
      fontWeight: 400,
      marginBottom: 8,
    },
    chatContainer: {
      marginTop: 24,
      background: colors.neutral50,
      border: `1px solid ${colors.neutral100}`,
      borderRadius: 16,
      padding: '2rem',
      boxShadow: shadows.card,
    },
    chatHeader: {
      background: colors.primary,
      color: '#fff',
      padding: '0.875rem 1.25rem',
      borderRadius: 8,
      marginBottom: '1rem',
      fontWeight: 600,
      fontSize: 13,
    },
    chatMessages: {
      minHeight: 280,
      maxHeight: 420,
      overflowY: 'auto',
      display: 'flex',
      flexDirection: 'column',
      gap: 10,
      marginBottom: 16,
    },
    bubbleAssistant: {
      background: '#fff',
      padding: '1rem 1.1rem',
      borderRadius: 8,
      borderLeft: `3px solid ${colors.accent}`,
      fontSize: 14,
      lineHeight: 1.6,
      color: colors.neutral800,
      maxWidth: '90%',
      alignSelf: 'flex-start',
      whiteSpace: 'pre-wrap',
    },
    bubbleUser: {
      background: colors.primary,
      color: '#fff',
      padding: '0.85rem 1rem',
      borderRadius: 8,
      fontSize: 14,
      lineHeight: 1.5,
      maxWidth: '90%',
      alignSelf: 'flex-end',
      whiteSpace: 'pre-wrap',
    },
    chatInputGroup: {
      display: 'grid',
      gridTemplateColumns: isMobile ? '1fr' : '1fr auto',
      gap: 12,
    },
    chatInputShell: {
      border: `1px solid ${colors.neutral100}`,
      borderRadius: 10,
      background: '#fff',
      display: 'flex',
      alignItems: 'center',
      gap: 8,
      padding: '0 8px',
    },
    attachBtn: {
      width: 30,
      height: 30,
      borderRadius: 15,
      border: `1px solid ${colors.neutral200}`,
      background: colors.neutral50,
      color: colors.textMuted,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      cursor: 'pointer',
    },
    chatInput: {
      flex: 1,
      border: 'none',
      outline: 'none',
      fontSize: 14,
      fontFamily: typography.body,
      background: 'transparent',
      padding: '12px 6px',
      color: colors.text,
    },
    actionsRight: { display: 'flex', gap: 8, alignItems: 'center', justifySelf: 'end' },
    iconBtn: {
      width: 36,
      height: 36,
      borderRadius: 8,
      border: `1px solid ${colors.neutral100}`,
      background: '#fff',
      color: colors.neutral800,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      cursor: 'pointer',
    },
    sendBtn: {
      background: colors.primary,
      color: '#fff',
      border: 'none',
      borderRadius: 8,
      padding: '12px 24px',
      fontSize: 14,
      fontWeight: 600,
      cursor: 'pointer',
    },
    caseBox: {
      background: '#E8F3FF',
      border: `1px solid ${colors.accent}55`,
      borderRadius: 8,
      padding: '12px 16px',
      color: colors.primary,
      fontSize: 14,
      lineHeight: 1.6,
    },
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
          <h1 style={s.heroTitle}>Tu reclamación merece ser escuchada.</h1>
          <p style={s.heroText}>
            Si tienes un problema con un producto o servicio, nosotros te ayudamos. Presentamos tu reclamación ante la SIC de forma gratuita y profesional, con todo el respaldo legal que necesitas.
          </p>
          <div style={s.heroBtns}>
            <button style={s.btnPrimary} onClick={scrollToChat}>Iniciar mi caso</button>
            <button style={s.btnSecondary}>Ir a contacto</button>
          </div>
        </div>

        <div style={s.featureBox}>
          <h3 style={s.featureBoxTitle}>¿Qué hacemos por ti?</h3>
          {[
            'Revisión legal experta de tu caso',
            'Documentos preparados profesionalmente',
            'Presentación ante la SIC incluida',
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
              ['Cuéntanos tu caso', 'Describe qué pasó con tu compra o servicio. Nuestro asistente te guía con preguntas claras.'],
              ['Sube evidencia', 'Comparte fotos, facturas, conversaciones y cualquier documento que respalde tu reclamo.'],
              ['Revisión legal', 'Nuestro equipo revisa tu caso, valida la reclamación y prepara los documentos necesarios.'],
              ['Presentamos ante SIC', 'Enviamos tu reclamación formalmente a la Superintendencia de Industria y Comercio.'],
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
          <h2 style={s.displayTitle}>Por qué elegir JusticIA</h2>
          <div style={s.benefitsGrid}>
            {[
              ['Completamente seguro', 'Tus datos están protegidos con estándares robustos de seguridad.'],
              ['Gratis de verdad', 'No hay costos ocultos ni tarifas por transacción.'],
              ['Rápido y simple', 'Completa tu reclamación en minutos con guía paso a paso.'],
              ['Respaldo legal', 'Abogados expertos revisan cada caso antes de presentar.'],
              ['Casos validados', 'Alto porcentaje de casos validados con documentación sólida.'],
              ['Panel de control', 'Monitorea tu caso y recibe actualizaciones en cada etapa.'],
            ].map((item) => (
              <div key={item[0]}>
                <h3 style={s.benefitTitle}>{item[0]}</h3>
                <p style={s.benefitText}>{item[1]}</p>
              </div>
            ))}
          </div>
        </section>

        <section style={s.chatSection} id="chat" ref={chatRef}>
          <span style={s.sectionLabel}>Cuéntanos qué pasó</span>
          <h2 style={s.chatTitle}>Nuestro asistente te guiará paso a paso</h2>

          <div style={s.chatContainer}>
            <div style={s.chatHeader}>JusticIA — Asistente de Reclamaciones</div>
            <div style={s.chatMessages}>
              {messages.map((m, i) => (
                <div key={i} style={m.role === 'assistant' ? s.bubbleAssistant : s.bubbleUser}>{m.text}</div>
              ))}
              {loading && <div style={s.bubbleAssistant}>Escribiendo...</div>}
              {caseId && (
                <div style={s.caseBox}>
                  Caso registrado: <strong>{caseId}</strong><br />
                  Un abogado revisará tu reclamación. Te avisaremos por WhatsApp.
                </div>
              )}
              <div ref={bottomRef} />
            </div>

            {stage !== 'COMPLETE' && (
              <div style={s.chatInputGroup}>
                <input
                  ref={fileRef}
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png"
                  style={{ display: 'none' }}
                  onChange={handleFileUpload}
                />

                <div style={s.chatInputShell}>
                  <button
                    style={s.attachBtn}
                    onClick={() => fileRef.current?.click()}
                    disabled={uploading}
                    title="Adjuntar documento"
                    aria-label="Adjuntar documento"
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.2-9.19a4 4 0 115.66 5.66l-9.2 9.2a2 2 0 11-2.83-2.83l8.49-8.48" /></svg>
                  </button>
                  <input
                    style={s.chatInput}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Escribe tu mensaje..."
                    onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
                    disabled={loading}
                  />
                </div>

                <div style={s.actionsRight}>
                  <button style={s.iconBtn} title="Grabar audio" aria-label="Grabar audio" disabled>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><rect x="9" y="2" width="6" height="12" rx="3" /><path d="M5 10a7 7 0 0014 0" /><path d="M12 19v3" /><path d="M8 22h8" /></svg>
                  </button>
                  <button style={s.sendBtn} onClick={sendMessage} disabled={loading || !input.trim()}>Enviar</button>
                </div>
              </div>
            )}
          </div>
        </section>

        <section style={s.ctaSection}>
          <h2 style={s.ctaTitle}>¿Necesitas resolver un reclamo?</h2>
          <p style={s.ctaText}>
            No dejes que una mala experiencia quede sin respuesta. Te ayudamos a hacer valer tus derechos como consumidor.
          </p>
          <button style={s.ctaBtn} onClick={scrollToChat}>Comenzar ahora</button>
        </section>
      </div>

      <Footer />
    </div>
  )
}
