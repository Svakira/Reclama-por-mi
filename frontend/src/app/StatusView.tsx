import React, { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import api from '../api/client'

const STATUS_LABELS: Record<string, string> = {
  PENDING_REVIEW: 'En revisión por el abogado',
  LAWYER_REVIEWING: 'El abogado está revisando tu caso',
  APPROVED: 'Aprobado — preparando envío',
  SUBMITTED_TO_SIC: '✅ Enviado a la SIC',
  FILING_OPTION_2_PDF_READY: '✅ Tu PDF está listo para descargar',
  DOCS_REQUESTED: 'El abogado necesita más documentos',
  PENDING_CLAIM_DECISION: 'Revisión especial en progreso',
  NO_CLAIM_CONFIRMED: 'Ver resultado del análisis',
  ILLEGIBLE_DOCUMENT_BLOCKED: 'Revisando documento con el abogado',
  CLOSED: 'Caso cerrado',
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: '100vh',
    background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: '40px 20px',
  },
  card: {
    background: '#1e293b',
    border: '1px solid #334155',
    borderRadius: 16,
    padding: 24,
    maxWidth: 480,
    width: '100%',
  },
  title: { fontSize: 20, fontWeight: 700, color: '#38bdf8', marginBottom: 8 },
  caseId: { fontSize: 13, color: '#64748b', marginBottom: 20 },
  status: {
    background: '#0f2d1a',
    border: '1px solid #22c55e',
    borderRadius: 10,
    padding: '12px 16px',
    color: '#86efac',
    fontSize: 15,
    fontWeight: 600,
  },
  hint: { color: '#94a3b8', fontSize: 13, marginTop: 12, lineHeight: 1.6 },
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

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <div style={styles.title}>Estado de tu caso</div>
        <div style={styles.caseId}>Número: {caseId}</div>
        {error ? (
          <div style={{ color: '#f87171' }}>No se encontró el caso. Verifica el número.</div>
        ) : (
          <>
            <div style={styles.status}>{STATUS_LABELS[status] || status}</div>
            <div style={styles.hint}>
              Te avisaremos por WhatsApp cuando haya novedades.<br />
              Guarda este número de caso: <strong>{caseId}</strong>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
