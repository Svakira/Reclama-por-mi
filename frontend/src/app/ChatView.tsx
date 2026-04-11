import React, { useState, useRef, useEffect } from 'react'
import api from '../api/client'

interface Message {
  role: 'user' | 'assistant'
  text: string
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: '100vh',
    background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: '0',
  },
  header: {
    width: '100%',
    maxWidth: 640,
    padding: '20px 20px 10px',
    borderBottom: '1px solid #334155',
  },
  logo: {
    fontSize: 22,
    fontWeight: 700,
    color: '#38bdf8',
    letterSpacing: '-0.5px',
  },
  subtitle: {
    fontSize: 12,
    color: '#94a3b8',
    marginTop: 2,
  },
  chat: {
    flex: 1,
    width: '100%',
    maxWidth: 640,
    padding: '16px 20px',
    overflowY: 'auto',
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
  },
  inputBar: {
    width: '100%',
    maxWidth: 640,
    padding: '12px 20px 20px',
    display: 'flex',
    gap: 8,
    borderTop: '1px solid #334155',
  },
  input: {
    flex: 1,
    background: '#1e293b',
    border: '1px solid #334155',
    borderRadius: 24,
    padding: '10px 16px',
    color: '#f1f5f9',
    fontSize: 14,
    outline: 'none',
  },
  sendBtn: {
    background: '#0ea5e9',
    border: 'none',
    borderRadius: 24,
    padding: '10px 20px',
    color: '#fff',
    fontWeight: 600,
    cursor: 'pointer',
    fontSize: 14,
  },
  uploadBtn: {
    background: '#334155',
    border: 'none',
    borderRadius: 24,
    padding: '10px 14px',
    color: '#94a3b8',
    cursor: 'pointer',
    fontSize: 14,
  },
  fileHint: {
    color: '#64748b',
    fontSize: 12,
    textAlign: 'center' as const,
    padding: '4px 0',
  },
  caseIdBox: {
    background: '#0f2d1a',
    border: '1px solid #22c55e',
    borderRadius: 12,
    padding: '12px 16px',
    color: '#86efac',
    fontSize: 13,
    margin: '8px 0',
  },
}

const bubbleStyle = (role: 'user' | 'assistant'): React.CSSProperties => ({
  maxWidth: '80%',
  padding: '10px 14px',
  borderRadius: role === 'user' ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
  background: role === 'user' ? '#0ea5e9' : '#1e293b',
  color: '#f1f5f9',
  fontSize: 14,
  lineHeight: 1.5,
  alignSelf: role === 'user' ? 'flex-end' : 'flex-start',
  border: role === 'assistant' ? '1px solid #334155' : 'none',
  whiteSpace: 'pre-wrap',
})

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

  useEffect(() => {
    startSession()
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

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
      const res = await api.post('/pipeline/message', {
        session_id: sessionId,
        message: text,
      })
      setMessages((m) => [...m, { role: 'assistant', text: res.data.agent_reply }])
      setStage(res.data.stage)
      if (res.data.next_action === 'upload_document') {
        setMessages((m) => [
          ...m,
          {
            role: 'assistant',
            text: '📎 Por favor sube el documento que te pedí. Puedes usar el botón de adjuntar.',
          },
        ])
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
      const res = await api.post('/pipeline/upload', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      if (res.data.blocked) {
        setMessages((m) => [
          ...m,
          {
            role: 'assistant',
            text: 'No pude leer bien ese documento. Un abogado lo revisará manualmente. Te avisaremos pronto.',
          },
        ])
      } else {
        setCaseId(res.data.case_id)
        setStage('COMPLETE')
        setMessages((m) => [
          ...m,
          {
            role: 'assistant',
            text: res.data.simple_explanation || `¡Tu caso fue procesado! Número de referencia: ${res.data.case_id}`,
          },
        ])
      }
    } catch {
      setMessages((m) => [...m, { role: 'assistant', text: 'Error al subir el documento. Por favor intenta de nuevo.' }])
    }
    setUploading(false)
    if (fileRef.current) fileRef.current.value = ''
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div style={styles.logo}>JusticIA</div>
        <div style={styles.subtitle}>Clínica Jurídica ICESI • Protección al Consumidor</div>
      </div>

      <div style={styles.chat}>
        {messages.map((m, i) => (
          <div key={i} style={bubbleStyle(m.role)}>
            {m.text}
          </div>
        ))}
        {loading && (
          <div style={bubbleStyle('assistant')}>
            <span style={{ color: '#64748b' }}>Escribiendo...</span>
          </div>
        )}
        {caseId && (
          <div style={styles.caseIdBox}>
            ✅ Caso registrado: <strong>{caseId}</strong><br />
            Un abogado revisará tu reclamación. Te avisaremos por WhatsApp.
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {stage !== 'COMPLETE' && (
        <>
          {(stage === 'DOCS_NEEDED' || stage === 'INTAKE') && (
            <div style={{ width: '100%', maxWidth: 640, padding: '0 20px' }}>
              <div style={styles.fileHint}>
                {stage === 'DOCS_NEEDED' ? '📎 Necesitamos un documento — usa el botón de adjuntar' : ''}
              </div>
            </div>
          )}
          <div style={styles.inputBar}>
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,.jpg,.jpeg,.png"
              style={{ display: 'none' }}
              onChange={handleFileUpload}
            />
            <button
              style={styles.uploadBtn}
              onClick={() => fileRef.current?.click()}
              disabled={uploading}
              title="Adjuntar documento"
            >
              {uploading ? '⏳' : '📎'}
            </button>
            <input
              style={styles.input}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Escribe tu mensaje..."
              onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
              disabled={loading}
            />
            <button style={styles.sendBtn} onClick={sendMessage} disabled={loading || !input.trim()}>
              Enviar
            </button>
          </div>
        </>
      )}
    </div>
  )
}
