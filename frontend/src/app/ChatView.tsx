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
    chatSectionInner: { maxWidth: 720, margin: '0 auto' },
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
      gap: 8,
      alignItems: 'center',
    },
    inputField: {
      flex: 1,
      border: `1px solid ${colors.border}`,
      borderRadius: 6,
      padding: '10px 14px',
      fontSize: 14,
      color: colors.text,
      outline: 'none',
      background: colors.surface,
    },
    sendBtn: {
      background: colors.primary,
      border: 'none',
      borderRadius: 6,
      padding: '10px 20px',
      color: '#fff',
      fontWeight: 600,
      cursor: 'pointer',
      fontSize: 14,
    },
    attachBtn: {
      background: colors.bg,
      border: `1px solid ${colors.border}`,
      borderRadius: 6,
      padding: '10px 14px',
      color: colors.textMuted,
      cursor: 'pointer',
      fontSize: 14,
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

      {/* Hero */}
      <section style={s.hero}>
        <div style={s.heroInner}>
          <h1 style={s.heroTitle}>Defiende tus derechos como consumidor</h1>
          <p style={s.heroSub}>
            La Clínica Jurídica ICESI te ayuda a presentar tu reclamación ante la Superintendencia de Industria y Comercio de forma gratuita.
          </p>
          <button style={s.heroCta} onClick={scrollToChat}>Iniciar mi caso →</button>
        </div>
      </section>

      {/* Chat Section */}
      <section style={s.chatSection} id="chat" ref={chatRef}>
        <div style={s.chatSectionInner}>
          <h2 style={s.sectionTitle}>Cuéntanos qué pasó</h2>
          <p style={s.sectionSub}>Nuestro asistente te guiará paso a paso</p>

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
                  ✅ Caso registrado: <strong>{caseId}</strong><br />
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
                <button
                  style={s.attachBtn}
                  onClick={() => fileRef.current?.click()}
                  disabled={uploading}
                  title="Adjuntar documento"
                >
                  {uploading ? '⏳' : '📎'}
                </button>
                <input
                  style={s.inputField}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Escribe tu mensaje..."
                  onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
                  disabled={loading}
                />
                <button style={s.sendBtn} onClick={sendMessage} disabled={loading || !input.trim()}>
                  Enviar
                </button>
              </div>
            )}
          </div>
        </div>
      </section>

      <Footer />
    </div>
  )
}
