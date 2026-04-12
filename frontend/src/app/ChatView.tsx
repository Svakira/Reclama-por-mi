import React, { useEffect, useMemo, useRef, useState } from 'react'
import api from '../api/client'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'
import { colors, shadows, typography } from '../styles/tokens'

interface Message {
  role: 'user' | 'assistant'
  text: string
}

interface PendingAttachment {
  id: string
  file: File
}

const NAV_LINKS = [
  { label: 'Inicio', href: '/app#top' },
  { label: 'Como funciona', href: '/app#steps' },
  { label: 'Nosotros', href: '/app#benefits' },
  { label: 'Estado de caso', href: '/app/status' },
]

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function ChatView() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [stage, setStage] = useState('INIT')
  const [caseId, setCaseId] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const [isProcessingFinal, setIsProcessingFinal] = useState(false)
  const [pendingAttachments, setPendingAttachments] = useState<PendingAttachment[]>([])
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [isMobile, setIsMobile] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false
    return window.innerWidth <= 980
  })

  const fileRef = useRef<HTMLInputElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => { startSession() }, [])
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  useEffect(() => {
    function onResize() {
      const mobile = window.innerWidth <= 980
      setIsMobile(mobile)
      if (!mobile) setSidebarOpen(false)
    }
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  async function startSession() {
    try {
      const res = await api.post('/pipeline/start')
      setSessionId(res.data.session_id)
      setStage(res.data.stage)
      setMessages([{ role: 'assistant', text: res.data.agent_reply }])
    } catch {
      setMessages([{ role: 'assistant', text: 'Hola, soy Reclama por mi. En que te puedo ayudar hoy?' }])
    }
  }

  async function uploadSingleFile(file: File) {
    if (!sessionId) return

    const form = new FormData()
    form.append('session_id', sessionId)
    form.append('file', file)
    form.append('doc_type', 'auto')

    try {
      const res = await api.post('/pipeline/upload', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })

      if (res.data.blocked) {
        setMessages((m) => [
          ...m,
          {
            role: 'assistant',
            text: res.data.message || 'No pude leer bien ese documento. Intenta subir una foto mas clara.',
          },
        ])
      } else {
        setStage(res.data.stage || 'DOCS_NEEDED')
        setMessages((m) => [...m, { role: 'assistant', text: res.data.message }])
      }
    } catch {
      setMessages((m) => [
        ...m,
        { role: 'assistant', text: `Error al subir ${file.name}. Puedes volver a intentarlo.` },
      ])
    }
  }

  function queueFiles(e: React.ChangeEvent<HTMLInputElement>) {
    const selected = Array.from(e.target.files || [])
    if (selected.length === 0) return

    const next = selected.map((file) => ({ id: `${file.name}-${file.size}-${Math.random()}`, file }))
    setPendingAttachments((prev) => [...prev, ...next])

    if (fileRef.current) fileRef.current.value = ''
  }

  function removeQueuedFile(id: string) {
    setPendingAttachments((prev) => prev.filter((item) => item.id !== id))
  }

  async function sendComposite() {
    if (loading || uploading) return

    const text = input.trim()
    const hasFiles = pendingAttachments.length > 0
    if (!text && !hasFiles) return

    const fileNames = pendingAttachments.map((item) => item.file.name)
    const userSummary = [
      text,
      hasFiles ? `Adjuntos: ${fileNames.join(', ')}` : '',
    ].filter(Boolean).join('\n\n')

    setMessages((m) => [...m, { role: 'user', text: userSummary }])
    setInput('')
    setLoading(true)

    if (hasFiles) {
      setUploading(true)
      setMessages((m) => [...m, { role: 'assistant', text: `Recibi ${pendingAttachments.length} archivo(s). Voy a analizarlos ahora.` }])
      for (const item of pendingAttachments) {
        // Upload each attachment in order so backend stage/messages stay consistent.
        // eslint-disable-next-line no-await-in-loop
        await uploadSingleFile(item.file)
      }
      setPendingAttachments([])
      setUploading(false)
    }

    if (text) {
      try {
        const res = await api.post('/pipeline/message', { session_id: sessionId, message: text })
        setMessages((m) => [...m, { role: 'assistant', text: res.data.agent_reply }])
        setStage(res.data.stage)
        if (res.data.stage === 'COMPLETE' && res.data.case_id) {
          setCaseId(res.data.case_id)
        }
      } catch {
        setMessages((m) => [
          ...m,
          { role: 'assistant', text: 'Hubo un error enviando tu mensaje. Por favor intenta de nuevo.' },
        ])
      }
    }

    setLoading(false)
  }

  async function finalizePipeline() {
    if (!sessionId || loading) return
    setLoading(true)
    setIsProcessingFinal(true)
    setMessages((m) => [
      ...m,
      { role: 'assistant', text: 'Estamos revisando tu caso.' },
    ])

    try {
      const res = await api.post('/pipeline/finalize', { session_id: sessionId })
      setCaseId(res.data.case_id)
      setStage(res.data.stage || 'WHATSAPP_OPTIN')
      setMessages((m) => [
        ...m,
        {
          role: 'assistant',
          text: res.data.message || res.data.simple_explanation || `Tu caso fue registrado: ${res.data.case_id}`,
        },
      ])
    } catch (err: any) {
      const detail = err?.response?.data?.detail || 'Error al procesar el caso. Por favor intenta de nuevo.'
      setMessages((m) => [...m, { role: 'assistant', text: detail }])
    }

    setIsProcessingFinal(false)
    setLoading(false)
  }

  const placeholder = useMemo(() => {
    if (stage === 'DOCS_NEEDED') return 'Escribe algo como: aqui te mando la factura y foto del celular.'
    if (stage === 'WHATSAPP_OPTIN') return 'Escribe tu numero de WhatsApp o "no"...'
    return 'Escribe tu mensaje...'
  }, [stage])

  const s: Record<string, React.CSSProperties> = {
    page: {
      minHeight: '100vh',
      background: 'linear-gradient(180deg, #F7F6F4 0%, #FDFDFC 45%, #FFFFFF 100%)',
      color: colors.text,
      fontFamily: typography.body,
      display: 'flex',
      flexDirection: 'column',
    },
    workspace: {
      maxWidth: 1240,
      margin: '0 auto',
      padding: isMobile ? '1rem' : '1.25rem',
      display: 'grid',
      gridTemplateColumns: isMobile ? '1fr' : '320px minmax(0, 1fr)',
      gap: 18,
      alignItems: 'start',
    },
    sidebar: {
      border: `1px solid ${colors.neutral100}`,
      borderRadius: 16,
      background: '#fff',
      boxShadow: shadows.card,
      padding: '1rem',
      position: isMobile ? 'fixed' : 'sticky',
      top: isMobile ? 76 : 84,
      left: isMobile ? 12 : 'auto',
      width: isMobile ? '82vw' : 'auto',
      zIndex: isMobile ? 80 : 'auto',
      transform: isMobile ? (sidebarOpen ? 'translateX(0)' : 'translateX(-120%)') : 'none',
      transition: 'transform 180ms ease-out',
    },
    overlay: {
      position: 'fixed',
      inset: 0,
      background: 'rgba(15,20,25,0.35)',
      zIndex: 70,
      display: isMobile && sidebarOpen ? 'block' : 'none',
    },
    sideTitle: { margin: 0, fontFamily: typography.display, fontSize: 26, lineHeight: 1.1 },
    sideSubtitle: { margin: '8px 0 0', fontSize: 13, color: colors.textMuted, lineHeight: 1.6 },
    infoCard: {
      marginTop: 14,
      borderRadius: 12,
      border: `1px solid ${colors.neutral100}`,
      background: colors.neutral50,
      padding: '0.75rem 0.8rem',
    },
    infoTitle: { margin: 0, fontSize: 12, textTransform: 'uppercase', letterSpacing: 0.5, color: colors.accent },
    infoText: { margin: '6px 0 0', fontSize: 13, color: colors.neutral800, lineHeight: 1.5 },
    infoList: { margin: '8px 0 0 0', paddingLeft: 18, fontSize: 13, color: colors.neutral800, lineHeight: 1.6 },
    chatColumn: {
      width: '100%',
      maxWidth: 780,
      justifySelf: 'center',
    },
    chatWrap: {
      width: '100%',
      maxWidth: 780,
      justifySelf: 'center',
      border: `1px solid ${colors.neutral100}`,
      borderRadius: 16,
      background: '#fff',
      boxShadow: shadows.card,
      overflow: 'hidden',
    },
    chatHead: {
      background: colors.primary,
      color: '#fff',
      padding: '0.9rem 1rem',
      fontSize: 13,
      fontWeight: 600,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
    },
    chatHeadLeft: {
      display: 'flex',
      alignItems: 'center',
      gap: 8,
    },
    drawerBtn: {
      width: 28,
      height: 28,
      borderRadius: 8,
      border: '1px solid rgba(255,255,255,0.35)',
      background: 'transparent',
      color: '#fff',
      cursor: 'pointer',
      display: isMobile ? 'inline-flex' : 'none',
      alignItems: 'center',
      justifyContent: 'center',
      fontSize: 14,
      lineHeight: 1,
    },
    chatMessages: {
      minHeight: isMobile ? 330 : 420,
      maxHeight: isMobile ? 460 : 560,
      overflowY: 'auto',
      display: 'flex',
      flexDirection: 'column',
      gap: 10,
      padding: '1rem',
      background: '#FDFCF9',
    },
    bubbleAssistant: {
      background: '#fff',
      padding: '0.9rem 1rem',
      borderRadius: 10,
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
      borderRadius: 10,
      fontSize: 14,
      lineHeight: 1.55,
      maxWidth: '90%',
      alignSelf: 'flex-end',
      whiteSpace: 'pre-wrap',
    },
    caseBox: {
      background: '#E8F3FF',
      border: `1px solid ${colors.accent}55`,
      borderRadius: 8,
      padding: '10px 12px',
      color: colors.primary,
      fontSize: 13,
      lineHeight: 1.5,
    },
    loadingRow: {
      display: 'flex',
      alignItems: 'center',
      gap: 8,
    },
    loadingSpinner: {
      width: 14,
      height: 14,
      borderRadius: '50%',
      border: `2px solid ${colors.neutral200}`,
      borderTopColor: colors.primary,
      animation: 'rpm-spin 0.9s linear infinite',
      flexShrink: 0,
    },
    inputArea: { borderTop: `1px solid ${colors.neutral100}`, padding: '0.85rem' },
    previewWrap: {
      display: 'flex',
      flexWrap: 'wrap',
      gap: 8,
      marginBottom: pendingAttachments.length > 0 ? 10 : 0,
    },
    previewItem: {
      display: 'flex',
      alignItems: 'center',
      gap: 8,
      border: `1px solid ${colors.neutral200}`,
      background: colors.neutral50,
      borderRadius: 999,
      padding: '6px 10px',
      maxWidth: '100%',
    },
    previewName: {
      fontSize: 12,
      color: colors.neutral800,
      maxWidth: isMobile ? 150 : 210,
      overflow: 'hidden',
      textOverflow: 'ellipsis',
      whiteSpace: 'nowrap',
    },
    previewSize: { fontSize: 11, color: colors.textMuted },
    removeFileBtn: {
      width: 22,
      height: 22,
      borderRadius: 11,
      border: 'none',
      background: '#EDEAE5',
      color: colors.text,
      cursor: 'pointer',
      fontWeight: 700,
      lineHeight: 1,
      padding: 0,
    },
    chatInputGroup: {
      display: 'grid',
      gridTemplateColumns: isMobile ? '1fr' : '1fr auto',
      gap: 10,
    },
    chatInputShell: {
      border: `1px solid ${colors.neutral100}`,
      borderRadius: 12,
      background: '#fff',
      display: 'flex',
      alignItems: 'center',
      gap: 8,
      padding: '0 8px',
    },
    attachBtn: {
      width: 32,
      height: 32,
      borderRadius: 16,
      border: `1px solid ${colors.neutral200}`,
      background: colors.neutral50,
      color: colors.textMuted,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      cursor: 'pointer',
      flexShrink: 0,
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
    actionsRight: { display: 'flex', gap: 8, alignItems: 'center', justifySelf: isMobile ? 'stretch' : 'end' },
    voiceBtn: {
      width: 42,
      height: 42,
      borderRadius: 10,
      border: `1px solid ${colors.neutral100}`,
      background: '#fff',
      color: colors.neutral800,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      cursor: 'pointer',
      flexShrink: 0,
    },
    sendBtn: {
      background: colors.primary,
      color: '#fff',
      border: 'none',
      borderRadius: 10,
      padding: '12px 22px',
      fontSize: 14,
      fontWeight: 600,
      cursor: 'pointer',
      width: isMobile ? '100%' : 'auto',
    },
    processBtn: {
      background: colors.success,
      color: '#fff',
      border: 'none',
      borderRadius: 10,
      padding: '10px 14px',
      fontSize: 13,
      fontWeight: 600,
      cursor: 'pointer',
      marginBottom: 10,
      width: '100%',
    },
    backBtnRow: {
      width: '100%',
      marginBottom: 10,
    },
    backBtn: {
      border: `1px solid ${colors.neutral200}`,
      borderRadius: 10,
      background: '#fff',
      color: colors.neutral800,
      padding: '8px 12px',
      fontSize: 12,
      fontWeight: 600,
      textDecoration: 'none',
      display: 'inline-block',
    },
  }

  return (
    <div style={s.page}>
      <Navbar links={NAV_LINKS} contactLabel="Ayuda" />

      <div style={s.overlay} onClick={() => setSidebarOpen(false)} />

      <main style={s.workspace}>
        <aside style={s.sidebar}>
          <h2 style={s.sideTitle}>Como usar este chat</h2>
          <p style={s.sideSubtitle}>
            Este asistente organiza tu caso, revisa documentos y te guia para construir una reclamacion completa.
          </p>

          <div style={s.infoCard}>
            <h3 style={s.infoTitle}>Que hace RECLAMA POR MI</h3>
            <p style={s.infoText}>Te ayuda a estructurar hechos, subir evidencias y preparar un borrador formal para revision legal.</p>
          </div>

          <div style={s.infoCard}>
            <h3 style={s.infoTitle}>Como interactuar</h3>
            <ol style={s.infoList}>
              <li>Escribe tu caso en lenguaje simple.</li>
              <li>Adjunta varios archivos y, si quieres, envia texto en el mismo mensaje.</li>
              <li>Cuando el chat pida mas soporte, usa "Procesar mi reclamacion" al terminar.</li>
            </ol>
          </div>

          <div style={s.infoCard}>
            <h3 style={s.infoTitle}>Tip util</h3>
            <p style={s.infoText}>Ejemplo: "Aqui te mando la factura y foto del celular. La falla empezo hace 2 semanas".</p>
          </div>
        </aside>

        <section style={s.chatColumn}>
          <div style={s.backBtnRow}>
            <a href="/app" style={s.backBtn}>Volver</a>
          </div>

          <div style={s.chatWrap}>
            <div style={s.chatHead}>
              <span style={s.chatHeadLeft}>
                <button style={s.drawerBtn} onClick={() => setSidebarOpen(true)} aria-label="Abrir panel de ayuda">
                  ☰
                </button>
                <span>Conversacion activa</span>
              </span>
              <span>{uploading ? 'Subiendo archivos...' : loading ? 'Procesando...' : 'Listo'}</span>
            </div>

            <div style={s.chatMessages}>
              {messages.map((m, i) => (
                <div key={i} style={m.role === 'assistant' ? s.bubbleAssistant : s.bubbleUser}>{m.text}</div>
              ))}

              {(loading || uploading || isProcessingFinal) && (
                <div style={s.bubbleAssistant}>
                  <span style={s.loadingRow}>
                    <span style={s.loadingSpinner} aria-hidden="true" />
                    <span>Estamos revisando tu caso...</span>
                  </span>
                </div>
              )}

              {caseId && stage === 'COMPLETE' && (
                <div style={s.caseBox}>
                  Caso registrado: <strong>{caseId}</strong>
                </div>
              )}
              <div ref={bottomRef} />
            </div>

            {stage !== 'COMPLETE' && (
              <div style={s.inputArea}>
                {stage === 'DOCS_NEEDED' && (
                  <button style={s.processBtn} onClick={finalizePipeline} disabled={loading || uploading}>
                    Procesar mi reclamacion
                  </button>
                )}

                <input
                  ref={fileRef}
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png"
                  multiple
                  style={{ display: 'none' }}
                  onChange={queueFiles}
                />

                <div style={s.previewWrap}>
                  {pendingAttachments.map((item) => (
                    <div key={item.id} style={s.previewItem}>
                      <div style={s.previewName}>{item.file.name}</div>
                      <div style={s.previewSize}>{formatSize(item.file.size)}</div>
                      <button
                        style={s.removeFileBtn}
                        onClick={() => removeQueuedFile(item.id)}
                        aria-label={`Eliminar ${item.file.name}`}
                      >
                        ×
                      </button>
                    </div>
                  ))}
                </div>

                <div style={s.chatInputGroup}>
                  <div style={s.chatInputShell}>
                    {(stage === 'DOCS_NEEDED' || stage === 'INTAKE') && (
                      <button
                        style={s.attachBtn}
                        onClick={() => fileRef.current?.click()}
                        disabled={uploading || loading}
                        title="Adjuntar varios documentos"
                        aria-label="Adjuntar varios documentos"
                      >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.2-9.19a4 4 0 115.66 5.66l-9.2 9.2a2 2 0 11-2.83-2.83l8.49-8.48" /></svg>
                      </button>
                    )}

                    <input
                      style={s.chatInput}
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      placeholder={placeholder}
                      onKeyDown={(e) => e.key === 'Enter' && sendComposite()}
                      disabled={loading || uploading}
                    />
                  </div>

                  <div style={s.actionsRight}>
                    <button style={s.voiceBtn} title="Grabar audio" aria-label="Grabar audio" disabled>
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><rect x="9" y="2" width="6" height="12" rx="3" /><path d="M5 10a7 7 0 0014 0" /><path d="M12 19v3" /><path d="M8 22h8" /></svg>
                    </button>
                    <button
                      style={s.sendBtn}
                      onClick={sendComposite}
                      disabled={loading || uploading || (!input.trim() && pendingAttachments.length === 0)}
                    >
                      Enviar
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </section>
      </main>

      <Footer />
    </div>
  )
}
