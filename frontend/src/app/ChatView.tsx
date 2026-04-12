// frontend/src/app/ChatView.tsx
import React, { useState, useRef, useEffect } from 'react'
import api from '../api/client'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'
import { colors, shadows } from '../styles/tokens'

interface Message {
  role: 'user' | 'assistant'
  text: string
}

const NAV_LINKS = [
  { label: 'Inicio', href: '#top' },
  { label: 'Cómo funciona', href: '#chat' },
  { label: 'Mis casos', href: '/app/status' },
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

  const iconBtnBase: React.CSSProperties = {
    width: 34,
    height: 34,
    borderRadius: 17,
    border: `1px solid ${colors.border}`,
    background: '#f1f3f5',
    color: '#495057',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    cursor: 'pointer',
  }

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
        setMessages((m) => [...m, { role: 'assistant', text: '📎 Por favor sube el documento que te pedí. Puedes usar el botón de adjuntar.' }])
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
    setMessages((m) => [...m, { role: 'user', text: `📎 Subiendo: ${file.name}` }])
    const form = new FormData()
    form.append('session_id', sessionId)
    form.append('file', file)
    form.append('doc_type', 'factura')
    try {
      const res = await api.post('/pipeline/upload', form, { headers: { 'Content-Type': 'multipart/form-data' } })
      if (res.data.blocked) {
        setMessages((m) => [...m, { role: 'assistant', text: 'No pude leer bien ese documento. Un abogado lo revisará manualmente. Te avisaremos pronto.' }])
      } else {
        setCaseId(res.data.case_id)
        setStage('COMPLETE')
        setMessages((m) => [...m, { role: 'assistant', text: res.data.simple_explanation || `¡Tu caso fue procesado! Número de referencia: ${res.data.case_id}` }])
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

  const isMobile = typeof window !== 'undefined' ? window.innerWidth <= 960 : false

  const s: Record<string, React.CSSProperties> = {
    page: { minHeight: '100vh', display: 'flex', flexDirection: 'column', background: colors.bg },
    hero: {
      background: `linear-gradient(135deg, ${colors.primary} 0%, ${colors.primaryLight} 100%)`,
      padding: '72px 20px',
      textAlign: 'center',
    },
    heroInner: { maxWidth: 680, margin: '0 auto' },
    heroTitle: {
      fontSize: 'clamp(1.75rem, 4vw, 2.5rem)',
      fontWeight: 700,
      color: '#ffffff',
      lineHeight: 1.2,
      marginBottom: 16,
    },
    heroSub: {
      fontSize: 'clamp(1rem, 2vw, 1.15rem)',
      color: 'rgba(255,255,255,0.85)',
      lineHeight: 1.6,
      marginBottom: 32,
    },
    heroCta: {
      background: colors.success,
      color: '#fff',
      border: 'none',
      borderRadius: 6,
      padding: '14px 32px',
      fontSize: 16,
      fontWeight: 700,
      cursor: 'pointer',
      boxShadow: '0 4px 16px rgba(0,0,0,0.2)',
    },
    chatSection: {
      background: colors.surface,
      padding: '56px 20px',
      flex: 1,
    },
    chatSectionInner: { maxWidth: 1120, margin: '0 auto' },
    workspace: {
      display: 'grid',
      gridTemplateColumns: isMobile ? '1fr' : '300px 1fr',
      gap: 20,
      alignItems: 'start',
    },
    guideCard: {
      border: `1px solid ${colors.border}`,
      borderRadius: 12,
      background: '#f8f9fa',
      boxShadow: shadows.card,
      padding: 18,
      position: 'sticky',
      top: 72,
    },
    guideTitle: {
      margin: 0,
      fontSize: 15,
      color: colors.primary,
      fontWeight: 700,
      marginBottom: 10,
    },
    guideText: {
      margin: 0,
      color: colors.textMuted,
      fontSize: 13,
      lineHeight: 1.5,
    },
    guideList: {
      margin: '10px 0 0 0',
      paddingLeft: 18,
      color: colors.text,
      fontSize: 13,
      lineHeight: 1.6,
    },
    guideHint: {
      marginTop: 12,
      padding: '10px 12px',
      borderRadius: 8,
      background: '#edf2ff',
      border: '1px solid #d0d9ff',
      color: '#2d4f8f',
      fontSize: 12,
      lineHeight: 1.5,
    },
    chatCol: {
      minWidth: 0,
    },
    sectionTitle: {
      fontSize: 'clamp(1.25rem, 3vw, 1.6rem)',
      fontWeight: 700,
      color: colors.primary,
      textAlign: 'center',
      marginBottom: 8,
    },
    sectionSub: {
      fontSize: 14,
      color: colors.textMuted,
      textAlign: 'center',
      marginBottom: 28,
    },
    chatBox: {
      border: `1px solid ${colors.border}`,
      borderRadius: 12,
      overflow: 'hidden',
      boxShadow: shadows.card,
    },
    chatHeader: {
      background: colors.primary,
      color: '#fff',
      padding: '14px 20px',
      fontSize: 14,
      fontWeight: 600,
    },
    chatMessages: {
      background: '#f8f9fa',
      minHeight: 320,
      maxHeight: 440,
      overflowY: 'auto',
      padding: 20,
      display: 'flex',
      flexDirection: 'column',
      gap: 10,
    },
    inputArea: {
      background: colors.surface,
      borderTop: `1px solid ${colors.border}`,
      padding: '12px 16px',
      display: 'flex',
      gap: 10,
      alignItems: 'center',
    },
    inputShell: {
      flex: 1,
      border: `1px solid ${colors.border}`,
      borderRadius: 20,
      padding: '0 8px 0 12px',
      display: 'flex',
      alignItems: 'center',
      gap: 8,
      background: colors.surface,
    },
    attachInsideBtn: {
      ...iconBtnBase,
      width: 30,
      height: 30,
      borderRadius: 15,
      opacity: 0.72,
    },
    inputField: {
      flex: 1,
      border: 'none',
      borderRadius: 16,
      padding: '10px 4px',
      fontSize: 14,
      color: colors.text,
      outline: 'none',
      background: colors.surface,
    },
    inputActions: {
      display: 'flex',
      alignItems: 'center',
      gap: 8,
    },
    audioBtn: {
      ...iconBtnBase,
      opacity: 0.85,
    },
    sendBtn: {
      background: colors.primary,
      border: 'none',
      borderRadius: 18,
      width: 36,
      height: 36,
      color: '#fff',
      fontWeight: 600,
      cursor: 'pointer',
      fontSize: 13,
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
    },
    caseBox: {
      background: '#e8f5e9',
      border: `1px solid ${colors.success}55`,
      borderRadius: 8,
      padding: '12px 16px',
      color: '#1b5e20',
      fontSize: 14,
      lineHeight: 1.6,
    },
  }

  const bubbleStyle = (role: 'user' | 'assistant'): React.CSSProperties => ({
    maxWidth: '80%',
    padding: '10px 14px',
    borderRadius: role === 'user' ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
    background: role === 'user' ? colors.primary : colors.surface,
    color: role === 'user' ? '#fff' : colors.text,
    fontSize: 14,
    lineHeight: 1.5,
    alignSelf: role === 'user' ? 'flex-end' : 'flex-start',
    border: role === 'assistant' ? `1px solid ${colors.border}` : 'none',
    whiteSpace: 'pre-wrap',
  })

  return (
    <div style={s.page} id="top">
      <Navbar links={NAV_LINKS} />

      <section style={s.hero}>
        <div style={s.heroInner}>
          <h1 style={s.heroTitle}>Defiende tus derechos como consumidor</h1>
          <p style={s.heroSub}>
            La Clínica Jurídica ICESI te ayuda a presentar tu reclamación ante la Superintendencia de Industria y Comercio de forma gratuita.
          </p>
          <button style={s.heroCta} onClick={scrollToChat}>Comenzar</button>
        </div>
      </section>

      {/* Chat Section */}
      <section style={s.chatSection} id="chat" ref={chatRef}>
        <div style={s.chatSectionInner}>
          <h2 style={s.sectionTitle}>Cuéntanos qué pasó</h2>
          <p style={s.sectionSub}>Nuestro asistente te guiará paso a paso</p>

          <div style={s.workspace}>
            <aside style={s.guideCard}>
              <h3 style={s.guideTitle}>Guía rápida</h3>
              <p style={s.guideText}>Para obtener un caso válido más rápido:</p>
              <ul style={s.guideList}>
                <li>Describe el problema en orden cronológico.</li>
                <li>Incluye fechas, montos y empresa involucrada.</li>
                <li>Adjunta factura o evidencia cuando te lo pida.</li>
                <li>Responde las preguntas del asistente sin omitir datos.</li>
              </ul>
              <div style={s.guideHint}>
                Resultado esperado: diagnóstico legal + borrador de reclamación + número de caso para seguimiento.
              </div>
            </aside>

            <div style={s.chatCol}>
              <div style={s.chatBox}>
                <div style={s.chatHeader}>JusticIA — Asistente de Reclamaciones</div>
                <div style={s.chatMessages}>
                  {messages.map((m, i) => (
                    <div key={i} style={bubbleStyle(m.role)}>{m.text}</div>
                  ))}
                  {loading && (
                    <div style={{ ...bubbleStyle('assistant'), color: colors.textMuted }}>Escribiendo...</div>
                  )}
                  {caseId && (
                    <div style={s.caseBox}>
                      Caso registrado: <strong>{caseId}</strong><br />
                      Un abogado revisará tu reclamación. Te avisaremos por WhatsApp.
                    </div>
                  )}
                  <div ref={bottomRef} />
                </div>

                {stage !== 'COMPLETE' && (
                  <div style={s.inputArea}>
                    <input
                      ref={fileRef}
                      type="file"
                      accept=".pdf,.jpg,.jpeg,.png"
                      style={{ display: 'none' }}
                      onChange={handleFileUpload}
                    />

                    <div style={s.inputShell}>
                      <button
                        style={s.attachInsideBtn}
                        onClick={() => fileRef.current?.click()}
                        disabled={uploading}
                        title="Adjuntar documento"
                        aria-label="Adjuntar documento"
                      >
                        {uploading ? (
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10" /></svg>
                        ) : (
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.2-9.19a4 4 0 115.66 5.66l-9.2 9.2a2 2 0 11-2.83-2.83l8.49-8.48" /></svg>
                        )}
                      </button>

                      <input
                        style={s.inputField}
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Escribe tu mensaje..."
                        onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
                        disabled={loading}
                      />
                    </div>

                    <div style={s.inputActions}>
                      <button
                        style={s.audioBtn}
                        title="Grabar audio (próximamente)"
                        aria-label="Grabar audio"
                        disabled
                      >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><rect x="9" y="2" width="6" height="12" rx="3" /><path d="M5 10a7 7 0 0014 0" /><path d="M12 19v3" /><path d="M8 22h8" /></svg>
                      </button>
                      <button style={s.sendBtn} onClick={sendMessage} disabled={loading || !input.trim()} aria-label="Enviar mensaje">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" /></svg>
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  )
}
