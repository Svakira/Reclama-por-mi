// frontend/src/admin/CaseDetail.tsx
import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import api from '../api/client'
import AdminLayout from './AdminLayout'
import Badge from '../components/Badge'
import { colors, shadows } from '../styles/tokens'

type Tab = 'draft' | 'transcript' | 'documents' | 'analysis'
type BadgeStatus = 'pending' | 'active' | 'approved' | 'rejected' | 'ready' | 'blocked' | 'info'

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
  messages?: { role: string; text: string }[]
  documents?: { name: string; doc_type: string; confidence: number }[]
}

const SCENARIO_LABEL: Record<string, string> = {
  A: 'Producto defectuoso (Ley 1480 arts. 7, 10, 11)',
  B: 'Cobro indebido financiero (Ley 1480 + Ley 45/1990)',
  C: 'Telecomunicaciones con PQR previa (Ley 1341)',
  UNKNOWN: 'Sin clasificar',
}

function statusToBadge(status: string): { status: BadgeStatus; label: string } {
  const map: Record<string, { status: BadgeStatus; label: string }> = {
    PENDING_REVIEW: { status: 'pending', label: 'Pendiente revisión' },
    LAWYER_REVIEWING: { status: 'active', label: 'En revisión' },
    APPROVED: { status: 'approved', label: 'Aprobado' },
    SUBMITTED_TO_SIC: { status: 'ready', label: 'Enviado SIC' },
    PENDING_CLAIM_DECISION: { status: 'blocked', label: 'Decisión requerida' },
    ILLEGIBLE_DOCUMENT_BLOCKED: { status: 'blocked', label: 'Doc. ilegible' },
    DOCS_REQUESTED: { status: 'info', label: 'Docs. solicitados' },
    CLOSED: { status: 'info', label: 'Cerrado' },
  }
  return map[status] || { status: 'info', label: status.replace(/_/g, ' ') }
}

const toastStyle = (ok: boolean): React.CSSProperties => ({
  position: 'fixed',
  bottom: 24,
  right: 24,
  background: ok ? colors.success : colors.danger,
  color: '#fff',
  borderRadius: 8,
  padding: '12px 20px',
  fontWeight: 600,
  fontSize: 14,
  zIndex: 999,
  boxShadow: shadows.modal,
})

export default function CaseDetail() {
  const { caseId } = useParams<{ caseId: string }>()
  const navigate = useNavigate()
  const [caseData, setCaseData] = useState<CaseData | null>(null)
  const [draft, setDraft] = useState('')
  const [draftLoading, setDraftLoading] = useState(false)
  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<Tab>('draft')

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
      setTimeout(() => navigate('/admin'), 2000)
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
      setTimeout(() => navigate('/admin'), 2000)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Error'
      showToast(msg, false)
    }
  }

  if (loading) return (
    <AdminLayout>
      <div style={{ padding: 40, color: colors.textMuted }}>Cargando caso...</div>
    </AdminLayout>
  )
  if (!caseData) return (
    <AdminLayout>
      <div style={{ padding: 40, color: colors.danger }}>Caso no encontrado</div>
    </AdminLayout>
  )

  const isPendingClaim = caseData.status === 'PENDING_CLAIM_DECISION'
  const canAct = isPendingClaim || (!caseData.lawyer_approved && caseData.status !== 'CLOSED')
  const badgeInfo = statusToBadge(caseData.status)
  const docs = caseData.documents || []
  const hasIllegible = docs.some((d) => d.confidence < 0.7)

  const s: Record<string, React.CSSProperties> = {
    page: { display: 'flex', flexDirection: 'column', height: '100%' },
    caseHeader: {
      background: colors.surface,
      borderBottom: `1px solid ${colors.border}`,
      padding: '16px 28px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: 16,
      flexShrink: 0,
    },
    caseHeaderLeft: { display: 'flex', flexDirection: 'column', gap: 4 },
    caseName: { fontSize: 20, fontWeight: 700, color: colors.text, margin: 0 },
    caseMeta: { display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: colors.textMuted },
    caseHeaderRight: { display: 'flex', gap: 10, alignItems: 'center', flexShrink: 0 },
    backBtn: {
      background: 'transparent',
      border: `1px solid ${colors.border}`,
      borderRadius: 6,
      padding: '7px 14px',
      color: colors.textMuted,
      cursor: 'pointer',
      fontSize: 13,
    },
    tabBar: {
      background: colors.surface,
      borderBottom: `1px solid ${colors.border}`,
      display: 'flex',
      padding: '0 28px',
      flexShrink: 0,
    },
    tabContent: {
      flex: 1,
      padding: '24px 28px',
      overflowY: 'auto' as const,
    },
    draftArea: {
      width: '100%',
      minHeight: 480,
      background: '#f8f9fa',
      border: `1px solid ${colors.border}`,
      borderRadius: 8,
      padding: 20,
      color: colors.text,
      fontSize: 14,
      lineHeight: 1.7,
      fontFamily: 'monospace',
      resize: 'vertical' as const,
      outline: 'none',
      boxSizing: 'border-box' as const,
    },
    saveBtn: {
      marginTop: 12,
      background: colors.primary,
      border: 'none',
      borderRadius: 6,
      padding: '8px 18px',
      color: '#fff',
      fontWeight: 600,
      cursor: 'pointer',
      fontSize: 13,
    },
    infoCard: {
      background: colors.surface,
      border: `1px solid ${colors.border}`,
      borderRadius: 8,
      padding: 20,
      marginBottom: 16,
    },
    infoTitle: {
      fontSize: 12,
      fontWeight: 700,
      color: colors.primary,
      textTransform: 'uppercase' as const,
      letterSpacing: '0.05em',
      marginBottom: 12,
    },
    articleItem: {
      background: colors.bg,
      border: `1px solid ${colors.border}`,
      borderRadius: 6,
      padding: '8px 12px',
      marginBottom: 6,
      fontSize: 13,
      color: colors.text,
    },
    docItem: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      background: colors.surface,
      border: `1px solid ${colors.border}`,
      borderRadius: 6,
      padding: '10px 16px',
      marginBottom: 8,
    },
  }

  const approveBtnStyle = (enabled: boolean): React.CSSProperties => ({
    background: colors.success,
    border: 'none',
    borderRadius: 6,
    padding: '8px 18px',
    color: '#fff',
    fontWeight: 700,
    cursor: enabled ? 'pointer' : 'not-allowed',
    fontSize: 14,
    opacity: enabled ? 1 : 0.4,
  })

  const rejectBtnStyle = (enabled: boolean): React.CSSProperties => ({
    background: colors.danger,
    border: 'none',
    borderRadius: 6,
    padding: '8px 18px',
    color: '#fff',
    fontWeight: 700,
    cursor: enabled ? 'pointer' : 'not-allowed',
    fontSize: 14,
    opacity: enabled ? 1 : 0.4,
  })

  const tabStyle = (tab: Tab): React.CSSProperties => ({
    padding: '12px 20px',
    cursor: 'pointer',
    fontSize: 14,
    fontWeight: activeTab === tab ? 600 : 400,
    color: activeTab === tab ? colors.primary : colors.textMuted,
    background: 'transparent',
    border: 'none',
    borderBottom: activeTab === tab ? `2px solid ${colors.primary}` : '2px solid transparent',
    outline: 'none',
  })

  const bubbleBotStyle: React.CSSProperties = {
    maxWidth: '80%',
    padding: '10px 14px',
    borderRadius: '18px 18px 18px 4px',
    background: colors.surface,
    border: `1px solid ${colors.border}`,
    color: colors.text,
    fontSize: 14,
    lineHeight: 1.5,
    alignSelf: 'flex-start',
    marginBottom: 8,
    whiteSpace: 'pre-wrap',
  }

  const bubbleUserStyle: React.CSSProperties = {
    maxWidth: '80%',
    padding: '10px 14px',
    borderRadius: '18px 18px 4px 18px',
    background: colors.primary,
    color: '#fff',
    fontSize: 14,
    lineHeight: 1.5,
    alignSelf: 'flex-end',
    marginBottom: 8,
    whiteSpace: 'pre-wrap',
  }

  const progressBarStyle = (pct: number): React.CSSProperties => ({
    height: 8,
    borderRadius: 4,
    background: `linear-gradient(90deg, ${colors.success} ${pct}%, ${colors.border} ${pct}%)`,
    marginTop: 6,
  })

  const flagItemStyle = (severity: string): React.CSSProperties => ({
    background: severity === 'warning' ? '#fff8e1' : '#e8f5e9',
    border: `1px solid ${severity === 'warning' ? '#f59e0b55' : '#2d6a4f55'}`,
    borderRadius: 6,
    padding: '8px 12px',
    marginBottom: 6,
    fontSize: 13,
    color: severity === 'warning' ? '#b45309' : colors.success,
  })

  const TAB_LABELS: Record<Tab, string> = {
    draft: 'Borrador SIC',
    transcript: 'Relato Original',
    documents: hasIllegible ? '⚠ Documentos' : 'Documentos',
    analysis: 'Análisis IA',
  }

  return (
    <AdminLayout>
      <div style={s.page}>
        {/* Case header */}
        <div style={s.caseHeader}>
          <div style={s.caseHeaderLeft}>
            <h2 style={s.caseName}>{caseData.consumer_name}</h2>
            <div style={s.caseMeta}>
              <span>Escenario {caseData.case_type} — {SCENARIO_LABEL[caseData.case_type] || caseData.case_type}</span>
              <span>·</span>
              <Badge status={badgeInfo.status} label={badgeInfo.label} />
            </div>
          </div>
          <div style={s.caseHeaderRight}>
            <button style={s.backBtn} onClick={() => navigate('/admin')}>← Volver</button>
            {isPendingClaim ? (
              <>
                <button style={approveBtnStyle(true)} onClick={() => handleClaimDecision('OVERRIDE_CLAIM_VALID')}>
                  ✓ Reactivar como válido
                </button>
                <button style={rejectBtnStyle(true)} onClick={() => handleClaimDecision('CONFIRM_NO_CLAIM')}>
                  ✗ Confirmar NO CLAIM
                </button>
              </>
            ) : caseData.lawyer_approved ? (
              <span style={{ fontSize: 13, color: colors.success, fontWeight: 600 }}>✓ Ya aprobado</span>
            ) : (
              <>
                <button style={approveBtnStyle(canAct)} disabled={!canAct} onClick={approveCase}>
                  ✓ Aprobar y enviar a SIC
                </button>
                <button
                  style={rejectBtnStyle(canAct)}
                  disabled={!canAct}
                  onClick={async () => {
                    await api.post(`/cases/${caseId}/request-docs`, { message: 'El abogado necesita documentos adicionales.' })
                    showToast('Solicitud de documentos enviada', true)
                  }}
                >
                  Pedir más docs
                </button>
              </>
            )}
          </div>
        </div>

        {/* Tab bar */}
        <div style={s.tabBar}>
          {(['draft', 'transcript', 'documents', 'analysis'] as Tab[]).map((tab) => (
            <button key={tab} style={tabStyle(tab)} onClick={() => setActiveTab(tab)}>
              {TAB_LABELS[tab]}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div style={s.tabContent}>
          {activeTab === 'draft' && (
            <>
              <textarea
                style={s.draftArea}
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                placeholder="Cargando borrador..."
              />
              <button style={s.saveBtn} onClick={saveDraft} disabled={draftLoading}>
                {draftLoading ? 'Guardando...' : 'Guardar borrador'}
              </button>
            </>
          )}

          {activeTab === 'transcript' && (
            <div style={{ display: 'flex', flexDirection: 'column', maxWidth: 680 }}>
              {caseData.messages && caseData.messages.length > 0 ? (
                caseData.messages.map((m, i) => (
                  <div key={i} style={m.role === 'user' ? bubbleUserStyle : bubbleBotStyle}>
                    {m.text}
                  </div>
                ))
              ) : caseData.ai_summary && caseData.ai_summary.length > 0 ? (
                <div style={s.infoCard}>
                  <div style={s.infoTitle}>Resumen del caso</div>
                  {caseData.ai_summary.map((item, i) => (
                    <div key={i} style={s.articleItem}>{item}</div>
                  ))}
                </div>
              ) : (
                <p style={{ color: colors.textMuted }}>No hay transcripción disponible.</p>
              )}
            </div>
          )}

          {activeTab === 'documents' && (
            <>
              {hasIllegible && (
                <div style={{ background: '#fff8e1', border: `1px solid ${colors.warning}55`, borderRadius: 8, padding: '12px 16px', marginBottom: 16, color: '#b45309', fontSize: 14 }}>
                  ⚠ Uno o más documentos tienen baja calidad (confianza &lt; 70%). El pipeline está bloqueado hasta que el abogado decida.
                </div>
              )}
              {docs.length === 0 ? (
                <p style={{ color: colors.textMuted }}>No hay documentos adjuntos.</p>
              ) : docs.map((doc, i) => {
                const isOk = doc.confidence >= 0.7
                return (
                  <div key={i} style={s.docItem}>
                    <div>
                      <div style={{ fontWeight: 500, fontSize: 14 }}>{doc.name}</div>
                      <div style={{ fontSize: 12, color: colors.textMuted, marginTop: 2 }}>{doc.doc_type}</div>
                    </div>
                    <Badge
                      status={isOk ? 'approved' : 'blocked'}
                      label={isOk ? `Válido (${Math.round(doc.confidence * 100)}%)` : `Ilegible (${Math.round(doc.confidence * 100)}%)`}
                    />
                  </div>
                )
              })}
            </>
          )}

          {activeTab === 'analysis' && (
            <>
              <div style={s.infoCard}>
                <div style={s.infoTitle}>Clasificación del caso</div>
                <div style={{ fontSize: 14, color: colors.text, marginBottom: 8 }}>
                  <strong>Escenario {caseData.case_type}:</strong> {SCENARIO_LABEL[caseData.case_type] || caseData.case_type}
                </div>
                {caseData.legal_classification && (
                  <>
                    <div style={{ fontSize: 13, color: colors.textMuted }}>
                      Confianza del clasificador: <strong>{Math.round((caseData.legal_classification.confidence || 0) * 100)}%</strong>
                    </div>
                    <div style={progressBarStyle(Math.round((caseData.legal_classification.confidence || 0) * 100))} />
                  </>
                )}
              </div>

              {caseData.legal_classification?.applicable_articles && caseData.legal_classification.applicable_articles.length > 0 && (
                <div style={s.infoCard}>
                  <div style={s.infoTitle}>Artículos legales aplicables</div>
                  {caseData.legal_classification.applicable_articles.map((art, i) => (
                    <div key={i} style={s.articleItem}>📖 {art}</div>
                  ))}
                </div>
              )}

              {caseData.validation_flags && caseData.validation_flags.length > 0 && (
                <div style={s.infoCard}>
                  <div style={s.infoTitle}>Validación del borrador</div>
                  {caseData.validation_flags.map((f, i) => (
                    <div key={i} style={flagItemStyle(f.severity)}>
                      <strong>{f.field}</strong>: {f.message}
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {toast && <div style={toastStyle(toast.ok)}>{toast.msg}</div>}
    </AdminLayout>
  )
}
