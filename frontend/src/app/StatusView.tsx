// frontend/src/app/StatusView.tsx
import React, { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import api from '../api/client'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'
import Badge from '../components/Badge'
import { colors, shadows } from '../styles/tokens'

const STATUS_CONFIG: Record<string, { label: string; badge: 'pending' | 'active' | 'approved' | 'ready' | 'blocked' | 'info' | 'rejected'; hint: string }> = {
  PENDING_REVIEW: { label: 'En revisión por el abogado', badge: 'pending', hint: 'Tu caso está en la cola de revisión. Un abogado lo analizará pronto.' },
  LAWYER_REVIEWING: { label: 'El abogado está revisando tu caso', badge: 'active', hint: 'El abogado de la clínica está analizando tu reclamación.' },
  APPROVED: { label: 'Aprobado — preparando envío', badge: 'approved', hint: 'Tu reclamación fue aprobada y está siendo preparada para enviar a la SIC.' },
  SUBMITTED_TO_SIC: { label: 'Enviado a la SIC', badge: 'ready', hint: 'Tu reclamación fue presentada formalmente ante la Superintendencia de Industria y Comercio.' },
  DOCS_REQUESTED: { label: 'Se necesitan más documentos', badge: 'info', hint: 'El abogado necesita documentos adicionales. Nos comunicaremos contigo pronto.' },
  PENDING_CLAIM_DECISION: { label: 'En revisión especial', badge: 'pending', hint: 'Tu caso está siendo revisado por un abogado. Recibirás una respuesta pronto.' },
  NO_CLAIM_CONFIRMED: { label: 'Análisis completado', badge: 'info', hint: 'El abogado analizó tu caso y tiene una respuesta para ti. Nos comunicaremos contigo.' },
  ILLEGIBLE_DOCUMENT_BLOCKED: { label: 'Revisando documento', badge: 'blocked', hint: 'Un documento no pudo leerse correctamente. El abogado lo revisará manualmente.' },
  CLOSED: { label: 'Caso cerrado', badge: 'info', hint: 'Este caso ha sido cerrado.' },
}

export default function StatusView() {
  const { caseId } = useParams<{ caseId: string }>()
  const [status, setStatus] = useState<string>('...')
  const [error, setError] = useState(false)

  useEffect(() => {
    if (!caseId) return
    const poll = async () => {
      try {
        const res = await api.get(`/cases/${caseId}/status`)
        setStatus(res.data.status)
      } catch {
        setError(true)
      }
    }
    poll()
    const interval = setInterval(poll, 30_000)
    return () => clearInterval(interval)
  }, [caseId])

  const config = STATUS_CONFIG[status]

  const s: Record<string, React.CSSProperties> = {
    page: { minHeight: '100vh', display: 'flex', flexDirection: 'column', background: colors.bg },
    content: { flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '48px 20px' },
    card: {
      background: colors.surface,
      border: `1px solid ${colors.border}`,
      borderRadius: 12,
      padding: 32,
      maxWidth: 520,
      width: '100%',
      boxShadow: shadows.card,
    },
    cardTitle: { fontSize: 20, fontWeight: 700, color: colors.primary, marginBottom: 6 },
    caseIdLabel: { fontSize: 13, color: colors.textMuted, marginBottom: 24 },
    statusRow: { display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 },
    statusLabel: { fontSize: 16, fontWeight: 600, color: colors.text },
    hint: { fontSize: 14, color: colors.textMuted, lineHeight: 1.6, marginBottom: 20 },
    saveNote: {
      background: colors.bg,
      border: `1px solid ${colors.border}`,
      borderRadius: 8,
      padding: '10px 14px',
      fontSize: 13,
      color: colors.textMuted,
    },
    errorText: { color: colors.danger, fontSize: 15 },
  }

  return (
    <div style={s.page}>
      <Navbar />
      <div style={s.content}>
        <div style={s.card}>
          <div style={s.cardTitle}>Estado de tu caso</div>
          <div style={s.caseIdLabel}>Número de referencia: <strong>{caseId}</strong></div>
          {error ? (
            <div style={s.errorText}>No se encontró el caso. Verifica el número.</div>
          ) : (
            <>
              <div style={s.statusRow}>
                {config ? (
                  <Badge status={config.badge} label={config.label} />
                ) : (
                  <span style={s.statusLabel}>{status}</span>
                )}
              </div>
              <p style={s.hint}>{config?.hint || 'Te avisaremos cuando haya novedades.'}</p>
              <div style={s.saveNote}>
                Guarda este número: <strong>{caseId}</strong> · Te notificaremos por WhatsApp cuando haya novedades.
              </div>
            </>
          )}
        </div>
      </div>
      <Footer />
    </div>
  )
}
