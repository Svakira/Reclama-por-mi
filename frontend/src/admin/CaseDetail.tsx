import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import api from '../api/client'

const s: Record<string, React.CSSProperties> = {
  page: { minHeight: '100vh', background: '#0f172a', padding: '24px 20px' },
  back: {
    background: 'transparent',
    border: '1px solid #334155',
    borderRadius: 8,
    padding: '6px 14px',
    color: '#94a3b8',
    cursor: 'pointer',
    fontSize: 13,
    marginBottom: 20,
  },
  layout: {
    display: 'grid',
    gridTemplateColumns: '340px 1fr',
    gap: 16,
    maxWidth: 1100,
    margin: '0 auto',
    alignItems: 'start',
  },
  panel: {
    background: '#1e293b',
    border: '1px solid #334155',
    borderRadius: 12,
    padding: 20,
  },
  panelTitle: { fontSize: 13, fontWeight: 700, color: '#64748b', textTransform: 'uppercase' as const, letterSpacing: 1, marginBottom: 12 },
  field: { marginBottom: 12 },
  fieldLabel: { fontSize: 11, color: '#64748b', marginBottom: 2 },
  fieldValue: { fontSize: 14, color: '#e2e8f0' },
  summaryItem: {
    background: '#0f172a',
    borderRadius: 8,
    padding: '8px 12px',
    fontSize: 13,
    color: '#94a3b8',
    marginBottom: 6,
  },
  draft: {
    width: '100%',
    minHeight: 480,
    background: '#0f172a',
    border: '1px solid #334155',
    borderRadius: 8,
    padding: 16,
    color: '#e2e8f0',
    fontSize: 13,
    lineHeight: 1.7,
    fontFamily: 'monospace',
    resize: 'vertical' as const,
    outline: 'none',
  },
  actionBar: {
    display: 'flex',
    gap: 8,
    marginTop: 12,
    flexWrap: 'wrap' as const,
  },
  btnOutline: {
    background: 'transparent',
    border: '1px solid #334155',
    borderRadius: 8,
    padding: '10px 18px',
    color: '#94a3b8',
    cursor: 'pointer',
    fontSize: 13,
  },
}

const flagStyle = (severity: string): React.CSSProperties => ({
  background: severity === 'warning' ? '#451a0322' : '#0f2d1a22',
  border: `1px solid ${severity === 'warning' ? '#fb923c44' : '#22c55e44'}`,
  borderRadius: 8,
  padding: '8px 12px',
  fontSize: 12,
  color: severity === 'warning' ? '#fb923c' : '#86efac',
  marginBottom: 6,
})

const btnStyle = (color: string): React.CSSProperties => ({
  background: color,
  border: 'none',
  borderRadius: 8,
  padding: '10px 18px',
  color: '#fff',
  fontWeight: 700,
  cursor: 'pointer',
  fontSize: 13,
})

const toastStyle = (ok: boolean): React.CSSProperties => ({
  position: 'fixed' as const,
  bottom: 24,
  right: 24,
  background: ok ? '#22c55e' : '#f87171',
  color: '#fff',
  borderRadius: 10,
  padding: '12px 20px',
  fontWeight: 600,
  fontSize: 14,
  zIndex: 999,
  boxShadow: '0 4px 20px rgba(0,0,0,0.4)',
})

interface CaseData {
  case_id: string
  consumer_name: string
  consumer_cedula?: string
  consumer_address?: string
  status: string
  case_type: string
  priority: number
  ai_summary?: string[]
  validation_flags?: { severity: string; field: string; message: string }[]
  legal_classification?: { scenario: string; confidence: number; applicable_articles: string[] }
  lawyer_approved: boolean
  created_at: string
}

export default function CaseDetail() {
  const { caseId } = useParams<{ caseId: string }>()
  const navigate = useNavigate()
  const [caseData, setCaseData] = useState<CaseData | null>(null)
  const [draft, setDraft] = useState('')
  const [draftLoading, setDraftLoading] = useState(false)
  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!caseId) return
    Promise.all([
      api.get(`/cases/${caseId}`),
      api.get(`/drafts/${caseId}/current`),
    ]).then(([caseRes, draftRes]) => {
      setCaseData(caseRes.data)
      setDraft(draftRes.data.content || '')
    }).catch(() => {
      showToast('Error al cargar el caso', false)
    }).finally(() => setLoading(false))
  }, [caseId])

  function showToast(msg: string, ok: boolean) {
    setToast({ msg, ok })
    setTimeout(() => setToast(null), 3500)
  }

  async function saveDraft() {
    setDraftLoading(true)
    try {
      await api.put(`/drafts/${caseId}/current`, { content: draft, is_auto_save: false })
      showToast('Borrador guardado', true)
    } catch {
      showToast('Error al guardar', false)
    }
    setDraftLoading(false)
  }

  async function approveCase() {
    try {
      await api.post(`/cases/${caseId}/approve`)
      showToast('¡Caso aprobado! Se presentará ante la SIC.', true)
      navigate('/admin')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Error al aprobar'
      showToast(msg, false)
    }
  }

  async function handleClaimDecision(decision: 'CONFIRM_NO_CLAIM' | 'OVERRIDE_CLAIM_VALID') {
    try {
      await api.post(`/lawyer/claim-decision/${caseId}`, { decision })
      showToast(
        decision === 'CONFIRM_NO_CLAIM'
          ? 'Confirmado como NO CLAIM. Se generará documento de rechazo.'
          : 'Caso reactivado como válido.',
        true
      )
      navigate('/admin')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Error'
      showToast(msg, false)
    }
  }

  if (loading) return <div style={{ color: '#94a3b8', padding: 40 }}>Cargando...</div>
  if (!caseData) return <div style={{ color: '#f87171', padding: 40 }}>Caso no encontrado</div>

  const isPendingClaim = caseData.status === 'PENDING_CLAIM_DECISION'

  return (
    <div style={s.page}>
      <button style={s.back} onClick={() => navigate('/admin')}>← Volver a la cola</button>

      <div style={s.layout}>
        {/* Left panel — case info */}
        <div>
          <div style={s.panel}>
            <div style={s.panelTitle}>Información del caso</div>
            <div style={s.field}>
              <div style={s.fieldLabel}>ID del caso</div>
              <div style={{ ...s.fieldValue, fontFamily: 'monospace', color: '#94a3b8' }}>{caseData.case_id}</div>
            </div>
            <div style={s.field}>
              <div style={s.fieldLabel}>Consumidor</div>
              <div style={s.fieldValue}>{caseData.consumer_name}</div>
            </div>
            {caseData.consumer_cedula && (
              <div style={s.field}>
                <div style={s.fieldLabel}>Cédula</div>
                <div style={s.fieldValue}>{caseData.consumer_cedula}</div>
              </div>
            )}
            <div style={s.field}>
              <div style={s.fieldLabel}>Tipo de caso</div>
              <div style={s.fieldValue}>Escenario {caseData.case_type}</div>
            </div>
            <div style={s.field}>
              <div style={s.fieldLabel}>Estado</div>
              <div style={{ ...s.fieldValue, color: '#fbbf24' }}>{caseData.status.replace(/_/g, ' ')}</div>
            </div>
            {caseData.legal_classification && (
              <div style={s.field}>
                <div style={s.fieldLabel}>Confianza IA</div>
                <div style={s.fieldValue}>
                  {Math.round((caseData.legal_classification.confidence || 0) * 100)}%
                </div>
              </div>
            )}
          </div>

          {/* AI Summary */}
          {caseData.ai_summary && caseData.ai_summary.length > 0 && (
            <div style={{ ...s.panel, marginTop: 12 }}>
              <div style={s.panelTitle}>Resumen IA</div>
              {caseData.ai_summary.map((item, i) => (
                <div key={i} style={s.summaryItem}>{item}</div>
              ))}
            </div>
          )}

          {/* Validation flags */}
          {caseData.validation_flags && caseData.validation_flags.length > 0 && (
            <div style={{ ...s.panel, marginTop: 12 }}>
              <div style={s.panelTitle}>Alertas de validación</div>
              {caseData.validation_flags.map((f, i) => (
                <div key={i} style={flagStyle(f.severity)}>
                  <strong>{f.field}</strong>: {f.message}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right panel — draft editor + actions */}
        <div>
          <div style={s.panel}>
            <div style={s.panelTitle}>Borrador de reclamación</div>
            <textarea
              style={s.draft}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
            />
            <div style={s.actionBar}>
              <button style={btnStyle('#0ea5e9')} onClick={saveDraft} disabled={draftLoading}>
                {draftLoading ? 'Guardando...' : 'Guardar borrador'}
              </button>

              {/* Hard gate actions depending on status */}
              {isPendingClaim ? (
                <>
                  <button style={btnStyle('#22c55e')} onClick={() => handleClaimDecision('OVERRIDE_CLAIM_VALID')}>
                    ✅ Reactivar como válido
                  </button>
                  <button style={btnStyle('#f87171')} onClick={() => handleClaimDecision('CONFIRM_NO_CLAIM')}>
                    ❌ Confirmar NO CLAIM
                  </button>
                </>
              ) : !caseData.lawyer_approved ? (
                <button style={btnStyle('#22c55e')} onClick={approveCase}>
                  ✅ Aprobar y enviar a SIC
                </button>
              ) : (
                <span style={{ color: '#86efac', fontSize: 13, padding: '10px 0' }}>
                  ✅ Ya aprobado
                </span>
              )}

              <button
                style={s.btnOutline}
                onClick={async () => {
                  await api.post(`/cases/${caseId}/request-docs`, { message: 'El abogado necesita documentos adicionales.' })
                  showToast('Solicitud de documentos enviada', true)
                }}
              >
                📎 Pedir más documentos
              </button>
            </div>
          </div>
        </div>
      </div>

      {toast && (
        <div style={toastStyle(toast.ok)}>{toast.msg}</div>
      )}
    </div>
  )
}
