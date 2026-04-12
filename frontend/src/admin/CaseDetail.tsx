import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import api from '../api/client'
import AdminLayout from './AdminLayout'
import Badge from '../components/Badge'
import { colors, shadows, typography } from '../styles/tokens'

type Tab = 'draft' | 'transcript' | 'documents' | 'analysis'
type BadgeStatus = 'pending' | 'active' | 'approved' | 'rejected' | 'ready' | 'blocked' | 'info'

interface ArticleAnalysis {
  article_id: string
  confidence_by_article: number
  relevant_excerpt: string
  reasoning_summary: string
}

interface CaseData {
  case_id: string
  consumer_name: string
  consumer_cedula?: string
  consumer_address?: string
  consumer_phone?: string
  consumer_email?: string
  provider_name?: string
  provider_nit?: string
  provider_address?: string
  status: string
  case_type: string
  priority: number
  ai_summary?: string[]
  validation_flags?: { severity: string; field: string; message: string }[]
  legal_classification?: {
    scenario: string
    confidence: number
    applicable_articles: string[]
    article_analysis?: ArticleAnalysis[]
  }
  lawyer_approved: boolean
  created_at: string
  messages?: { role: string; text: string }[]
  documents?: { name: string; doc_type: string; confidence: number }[]
  document_confidence?: number
}

const SCENARIO_LABEL: Record<string, string> = {
  A: 'Producto defectuoso (Ley 1480)',
  B: 'Cobro indebido (Ley 1480 + Ley 45/1990)',
  C: 'Telecomunicaciones (Ley 1341)',
  UNKNOWN: 'Sin clasificar',
}

function statusToBadge(status: string): { status: BadgeStatus; label: string } {
  const map: Record<string, { status: BadgeStatus; label: string }> = {
    PENDING_REVIEW: { status: 'pending', label: 'Pendiente revisión' },
    LAWYER_REVIEWING: { status: 'active', label: 'En revisión' },
    APPROVED: { status: 'approved', label: 'Aprobado' },
    SUBMITTED_TO_SIC: { status: 'ready', label: 'Enviado SIC' },
    PENDING_CLAIM_DECISION: { status: 'blocked', label: 'Decisión requerida' },
    ILLEGIBLE_DOCUMENT_BLOCKED: { status: 'blocked', label: 'Documento ilegible' },
    DOCS_REQUESTED: { status: 'info', label: 'Documentos solicitados' },
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
  const [expandedArticle, setExpandedArticle] = useState<string | null>(null)

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
      showToast('Caso aprobado. Se presentará ante la SIC.', true)
      setTimeout(() => navigate('/admin'), 1500)
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
          ? 'Confirmado como NO CLAIM. Se generará documento de cierre.'
          : 'Caso reactivado como válido.',
        true
      )
      setTimeout(() => navigate('/admin'), 1500)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Error'
      showToast(msg, false)
    }
  }

  if (loading) {
    return (
      <AdminLayout>
        <div style={{ padding: 36, color: colors.textMuted }}>Cargando caso...</div>
      </AdminLayout>
    )
  }

  if (!caseData) {
    return (
      <AdminLayout>
        <div style={{ padding: 36, color: colors.danger }}>Caso no encontrado</div>
      </AdminLayout>
    )
  }

  const isPendingClaim = caseData.status === 'PENDING_CLAIM_DECISION'
  const canAct = isPendingClaim || (!caseData.lawyer_approved && caseData.status !== 'CLOSED')
  const badgeInfo = statusToBadge(caseData.status)
  const docs = caseData.documents || []
  const hasIllegible = docs.some((d) => d.confidence < 0.7)
  const articleAnalysis = caseData.legal_classification?.article_analysis || []
  const completeness = useMemo(() => {
    const base = Math.round((caseData.document_confidence || 0.72) * 100)
    return Math.max(35, Math.min(100, base))
  }, [caseData.document_confidence])

  const s: Record<string, React.CSSProperties> = {
    page: { display: 'flex', flexDirection: 'column', height: '100%' },
    header: {
      background: colors.surface,
      borderBottom: `1px solid ${colors.border}`,
      padding: '22px 28px',
    },
    back: {
      border: 'none',
      background: 'transparent',
      color: colors.primary,
      cursor: 'pointer',
      fontSize: 13,
      fontWeight: 600,
      padding: 0,
      marginBottom: 10,
    },
    headerMain: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'flex-start',
      gap: 16,
      marginBottom: 14,
    },
    title: { margin: 0, fontSize: 28, fontWeight: 700, color: colors.text },
    headerActions: { display: 'flex', gap: 10, flexWrap: 'wrap', justifyContent: 'flex-end' },
    metaGrid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
      gap: 14,
    },
    metaLabel: {
      fontSize: 11,
      fontWeight: 700,
      textTransform: 'uppercase',
      color: colors.textMuted,
      letterSpacing: '0.05em',
    },
    metaValue: { fontSize: 13, color: colors.text, fontWeight: 600, marginTop: 2 },
    tabs: {
      display: 'flex',
      borderBottom: `1px solid ${colors.border}`,
      background: colors.surface,
      padding: '0 20px',
      gap: 2,
      overflowX: 'auto',
    },
    tabPanel: {
      display: 'grid',
      gridTemplateColumns: '2fr 1fr',
      gap: 20,
      padding: 20,
      overflowY: 'auto',
      flex: 1,
    },
    leftCol: { minWidth: 0 },
    rightCol: { minWidth: 250 },
    card: {
      background: colors.surface,
      border: `1px solid ${colors.border}`,
      borderRadius: 8,
      padding: 18,
      marginBottom: 16,
      boxShadow: shadows.card,
    },
    cardTitle: {
      margin: '0 0 10px 0',
      fontSize: 14,
      fontWeight: 700,
      color: colors.text,
      textTransform: 'uppercase',
      letterSpacing: '0.03em',
    },
    draftArea: {
      width: '100%',
      minHeight: 460,
      background: '#fff',
      border: `1px solid ${colors.border}`,
      borderRadius: 8,
      padding: 16,
      color: colors.text,
      fontSize: 14,
      lineHeight: 1.7,
      fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
      resize: 'vertical' as const,
      outline: 'none',
      boxSizing: 'border-box' as const,
    },
    saveBtn: {
      marginTop: 10,
      background: colors.primary,
      border: 'none',
      borderRadius: 6,
      padding: '9px 18px',
      color: '#fff',
      fontWeight: 600,
      cursor: 'pointer',
      fontSize: 13,
    },
    bubbleBot: {
      maxWidth: '85%',
      padding: '10px 14px',
      borderRadius: '16px 16px 16px 5px',
      background: '#fff',
      border: `1px solid ${colors.border}`,
      color: colors.text,
      fontSize: 13,
      lineHeight: 1.55,
      marginBottom: 8,
      whiteSpace: 'pre-wrap',
    },
    bubbleUser: {
      maxWidth: '85%',
      padding: '10px 14px',
      borderRadius: '16px 16px 5px 16px',
      background: colors.primary,
      color: '#fff',
      fontSize: 13,
      lineHeight: 1.55,
      marginLeft: 'auto',
      marginBottom: 8,
      whiteSpace: 'pre-wrap',
    },
    docRow: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      border: `1px solid ${colors.border}`,
      borderRadius: 6,
      background: colors.surface,
      padding: '10px 12px',
      marginBottom: 8,
    },
    articleBtn: {
      width: '100%',
      textAlign: 'left' as const,
      border: `1px solid ${colors.border}`,
      borderRadius: 6,
      background: '#F8FAFC',
      padding: '10px 12px',
      marginBottom: 8,
      fontSize: 13,
      fontWeight: 600,
      color: colors.text,
      cursor: 'pointer',
    },
    articlePanel: {
      border: `1px solid ${colors.border}`,
      borderRadius: 6,
      background: '#fff',
      padding: '10px 12px',
      marginBottom: 10,
      fontSize: 13,
      color: colors.textMuted,
      lineHeight: 1.55,
    },
    progressBar: {
      height: 8,
      borderRadius: 4,
      background: `linear-gradient(90deg, ${colors.primary} ${completeness}%, ${colors.border} ${completeness}%)`,
      marginTop: 6,
    },
    timelineItem: { marginBottom: 12, paddingBottom: 10, borderBottom: `1px solid ${colors.border}` },
    timelineTime: { fontSize: 11, color: colors.textMuted, fontWeight: 700 },
    timelineTitle: { fontSize: 13, color: colors.text, fontWeight: 600, marginTop: 2 },
  }

  const approveBtnStyle = (enabled: boolean): React.CSSProperties => ({
    background: colors.success,
    border: 'none',
    borderRadius: 6,
    padding: '10px 16px',
    color: '#fff',
    fontWeight: 700,
    cursor: enabled ? 'pointer' : 'not-allowed',
    fontSize: 13,
    opacity: enabled ? 1 : 0.5,
    fontFamily: typography.body,
  })

  const secondaryBtnStyle = (enabled: boolean, danger = false): React.CSSProperties => ({
    background: '#fff',
    border: `1px solid ${danger ? colors.danger : colors.primary}`,
    borderRadius: 6,
    padding: '10px 16px',
    color: danger ? colors.danger : colors.primary,
    fontWeight: 600,
    cursor: enabled ? 'pointer' : 'not-allowed',
    fontSize: 13,
    opacity: enabled ? 1 : 0.5,
    fontFamily: typography.body,
  })

  const tabStyle = (tab: Tab): React.CSSProperties => ({
    padding: '12px 16px',
    cursor: 'pointer',
    fontSize: 13,
    fontWeight: activeTab === tab ? 700 : 600,
    color: activeTab === tab ? colors.primary : colors.textMuted,
    background: 'transparent',
    border: 'none',
    borderBottom: activeTab === tab ? `2px solid ${colors.primary}` : '2px solid transparent',
    outline: 'none',
    whiteSpace: 'nowrap',
    fontFamily: typography.body,
  })

  const TAB_LABELS: Record<Tab, string> = {
    draft: 'Borrador SIC',
    transcript: 'Relato Original',
    documents: 'Documentos',
    analysis: 'Análisis IA',
  }

  return (
    <AdminLayout>
      <div style={s.page}>
        <header style={s.header}>
          <button style={s.back} onClick={() => navigate('/admin')}>← Volver</button>

          <div style={s.headerMain}>
            <div>
              <h1 style={s.title}>{caseData.consumer_name}</h1>
              <Badge status={badgeInfo.status} label={badgeInfo.label} />
            </div>

            <div style={s.headerActions}>
              {isPendingClaim ? (
                <>
                  <button style={approveBtnStyle(true)} onClick={() => handleClaimDecision('OVERRIDE_CLAIM_VALID')}>
                    Reactivar como válido
                  </button>
                  <button style={secondaryBtnStyle(true, true)} onClick={() => handleClaimDecision('CONFIRM_NO_CLAIM')}>
                    Confirmar NO CLAIM
                  </button>
                </>
              ) : caseData.lawyer_approved ? (
                <span style={{ fontSize: 13, color: colors.success, fontWeight: 700 }}>Caso aprobado</span>
              ) : (
                <>
                  <button style={approveBtnStyle(canAct)} disabled={!canAct} onClick={approveCase}>
                    Aprobar y enviar SIC
                  </button>
                  <button
                    style={secondaryBtnStyle(canAct)}
                    disabled={!canAct}
                    onClick={async () => {
                      await api.post(`/cases/${caseId}/request-docs`, { message: 'El abogado necesita documentos adicionales.' })
                      showToast('Solicitud de documentos enviada', true)
                    }}
                  >
                    Pedir más documentos
                  </button>
                </>
              )}
            </div>
          </div>

          <div style={s.metaGrid}>
            <div>
              <div style={s.metaLabel}>Caso ID</div>
              <div style={s.metaValue}>{caseData.case_id}</div>
            </div>
            <div>
              <div style={s.metaLabel}>Tipo de reclamación</div>
              <div style={s.metaValue}>{SCENARIO_LABEL[caseData.case_type] || caseData.case_type}</div>
            </div>
            <div>
              <div style={s.metaLabel}>Fecha de creación</div>
              <div style={s.metaValue}>{new Date(caseData.created_at).toLocaleDateString('es-CO')}</div>
            </div>
            <div>
              <div style={s.metaLabel}>Proveedor</div>
              <div style={s.metaValue}>{caseData.provider_name || 'N/D'}</div>
            </div>
          </div>
        </header>

        <div style={s.tabs}>
          {(['draft', 'transcript', 'documents', 'analysis'] as Tab[]).map((tab) => (
            <button key={tab} style={tabStyle(tab)} onClick={() => setActiveTab(tab)}>
              {TAB_LABELS[tab]}
            </button>
          ))}
        </div>

        <div style={s.tabPanel}>
          <div style={s.leftCol}>
            {activeTab === 'draft' && (
              <div style={s.card}>
                <h3 style={s.cardTitle}>Borrador de reclamación</h3>
                <textarea
                  style={s.draftArea}
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  placeholder="Cargando borrador..."
                />
                <button style={s.saveBtn} onClick={saveDraft} disabled={draftLoading}>
                  {draftLoading ? 'Guardando...' : 'Guardar borrador'}
                </button>
              </div>
            )}

            {activeTab === 'transcript' && (
              <div style={s.card}>
                <h3 style={s.cardTitle}>Relato original</h3>
                {caseData.messages && caseData.messages.length > 0 ? (
                  caseData.messages.map((m, i) => (
                    <div key={i} style={m.role === 'user' ? s.bubbleUser : s.bubbleBot}>{m.text}</div>
                  ))
                ) : caseData.ai_summary && caseData.ai_summary.length > 0 ? (
                  caseData.ai_summary.map((item, i) => <div key={i} style={s.bubbleBot}>{item}</div>)
                ) : (
                  <p style={{ color: colors.textMuted }}>No hay transcripción disponible.</p>
                )}
              </div>
            )}

            {activeTab === 'documents' && (
              <div style={s.card}>
                <h3 style={s.cardTitle}>Documentos adjuntos</h3>
                {hasIllegible && (
                  <div style={{ ...s.articlePanel, borderColor: `${colors.warning}55`, color: '#8A5A15' }}>
                    Uno o más documentos tienen baja calidad (confianza &lt; 70%).
                  </div>
                )}
                {docs.length === 0 ? (
                  <p style={{ color: colors.textMuted }}>No hay documentos adjuntos.</p>
                ) : docs.map((doc, i) => {
                  const ok = doc.confidence >= 0.7
                  return (
                    <div key={i} style={s.docRow}>
                      <div>
                        <div style={{ fontSize: 13, fontWeight: 600 }}>{doc.name}</div>
                        <div style={{ fontSize: 12, color: colors.textMuted }}>{doc.doc_type}</div>
                      </div>
                      <Badge status={ok ? 'approved' : 'blocked'} label={`${Math.round(doc.confidence * 100)}%`} />
                    </div>
                  )
                })}
              </div>
            )}

            {activeTab === 'analysis' && (
              <>
                <div style={s.card}>
                  <h3 style={s.cardTitle}>Clasificación legal</h3>
                  <div style={{ fontSize: 13, color: colors.text, marginBottom: 8 }}>
                    Escenario: <strong>{caseData.case_type}</strong>
                  </div>
                  <div style={{ fontSize: 13, color: colors.textMuted }}>
                    Confianza global: <strong>{Math.round((caseData.legal_classification?.confidence || 0) * 100)}%</strong>
                  </div>
                </div>

                {(caseData.legal_classification?.article_analysis || []).length > 0 && (
                  <div style={s.card}>
                    <h3 style={s.cardTitle}>Análisis por artículo</h3>
                    {articleAnalysis.map((a) => {
                      const active = expandedArticle === a.article_id
                      return (
                        <div key={a.article_id}>
                          <button
                            style={s.articleBtn}
                            onClick={() => setExpandedArticle(active ? null : a.article_id)}
                          >
                            {a.article_id} · Confianza {Math.round((a.confidence_by_article || 0) * 100)}%
                          </button>
                          {active && (
                            <div style={s.articlePanel}>
                              <div><strong>Extracto relevante:</strong> {a.relevant_excerpt || 'Sin extracto.'}</div>
                              <div style={{ marginTop: 8 }}><strong>Razonamiento:</strong> {a.reasoning_summary || 'Sin resumen.'}</div>
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                )}

                {caseData.validation_flags && caseData.validation_flags.length > 0 && (
                  <div style={s.card}>
                    <h3 style={s.cardTitle}>Validaciones</h3>
                    {caseData.validation_flags.map((f, i) => (
                      <div key={i} style={s.articlePanel}>
                        <strong>{f.field}</strong>: {f.message}
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>

          <aside style={s.rightCol}>
            <div style={s.card}>
              <h3 style={s.cardTitle}>Información del proveedor</h3>
              <div style={{ fontSize: 13, color: colors.textMuted, lineHeight: 1.7 }}>
                <div><strong>Razón social:</strong> {caseData.provider_name || 'N/D'}</div>
                <div><strong>NIT:</strong> {caseData.provider_nit || 'N/D'}</div>
                <div><strong>Dirección:</strong> {caseData.provider_address || 'N/D'}</div>
              </div>
            </div>

            <div style={s.card}>
              <h3 style={s.cardTitle}>Progreso del caso</h3>
              <div style={{ fontSize: 13, color: colors.textMuted }}>
                Completitud: <strong style={{ color: colors.primary }}>{completeness}%</strong>
              </div>
              <div style={s.progressBar} />
              <div style={{ marginTop: 12 }}>
                <div style={s.timelineItem}>
                  <div style={s.timelineTime}>Actual</div>
                  <div style={s.timelineTitle}>{badgeInfo.label}</div>
                </div>
                <div style={s.timelineItem}>
                  <div style={s.timelineTime}>Creación</div>
                  <div style={s.timelineTitle}>{new Date(caseData.created_at).toLocaleDateString('es-CO')}</div>
                </div>
              </div>
            </div>

            <div style={s.card}>
              <h3 style={s.cardTitle}>Indicadores</h3>
              <div style={{ fontSize: 13, color: colors.textMuted, lineHeight: 1.7 }}>
                <div>Prioridad: <strong>{caseData.priority}</strong></div>
                <div>Escenario: <strong>{caseData.case_type}</strong></div>
                <div>Confianza legal: <strong>{Math.round((caseData.legal_classification?.confidence || 0) * 100)}%</strong></div>
              </div>
            </div>
          </aside>
        </div>
      </div>

      {toast && <div style={toastStyle(toast.ok)}>{toast.msg}</div>}
    </AdminLayout>
  )
}
