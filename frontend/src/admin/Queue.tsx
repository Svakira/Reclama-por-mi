import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/client'
import AdminLayout from './AdminLayout'
import { colors, typography } from '../styles/tokens'

const SCENARIO_LABEL: Record<string, string> = {
  A: 'Producto defectuoso',
  B: 'Cobro indebido',
  C: 'Telecomunicaciones',
  UNKNOWN: 'Sin clasificar',
}

const STATUS_CONFIG: Record<string, { bg: string; color: string; label: string }> = {
  PENDING_REVIEW: { bg: 'rgba(184,134,11,0.15)', color: colors.warning, label: 'Pendiente revisión' },
  LAWYER_REVIEWING: { bg: 'rgba(26,58,92,0.15)', color: colors.primary, label: 'En revisión' },
  APPROVED: { bg: 'rgba(74,103,65,0.15)', color: colors.success, label: 'Aprobado' },
  DELIVERED_TO_ROSA: { bg: 'rgba(74,103,65,0.15)', color: colors.success, label: 'Entregado a Rosa' },
  SUBMITTED_TO_SIC: { bg: 'rgba(74,103,65,0.15)', color: colors.success, label: 'Entregado a Rosa' },
  PENDING_CLAIM_DECISION: { bg: 'rgba(184,134,11,0.15)', color: colors.warning, label: 'Decisión requerida' },
  ILLEGIBLE_DOCUMENT_BLOCKED: { bg: 'rgba(167,62,62,0.15)', color: colors.danger, label: 'Doc. ilegible' },
  DOCS_REQUESTED: { bg: 'rgba(26,58,92,0.15)', color: colors.primary, label: 'Docs. solicitados' },
  CLOSED: { bg: 'rgba(139,134,128,0.15)', color: colors.textMuted, label: 'Cerrado' },
}

interface Case {
  case_id: string
  consumer_name: string
  status: string
  priority: number
  case_type: string
  created_at: string
  product_description?: string
  docs_need_review?: boolean
}

export default function Queue() {
  const [cases, setCases] = useState<Case[]>([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('all')
  const [sortBy, setSortBy] = useState('date')
  const navigate = useNavigate()

  useEffect(() => {
    loadCases()
    const interval = setInterval(loadCases, 30_000)
    return () => clearInterval(interval)
  }, [])

  async function loadCases() {
    try {
      const res = await api.get('/cases')
      setCases(res.data)
    } catch {}
    setLoading(false)
  }

  const pendingCount = cases.filter((c) =>
    ['PENDING_REVIEW', 'PENDING_CLAIM_DECISION', 'LAWYER_REVIEWING'].includes(c.status)
  ).length
  const reviewingCount = cases.filter((c) => c.status === 'LAWYER_REVIEWING').length
  const approvedCount = cases.filter((c) => ['APPROVED', 'DELIVERED_TO_ROSA', 'SUBMITTED_TO_SIC'].includes(c.status)).length
  const approvalRate = cases.length > 0 ? Math.round((approvedCount / cases.length) * 100) : 0

  const filteredCases = cases.filter((c) => {
    if (statusFilter !== 'all' && c.status !== statusFilter) return false
    return true
  })

  const sortedCases = [...filteredCases].sort((a, b) => {
    if (sortBy === 'priority') return b.priority - a.priority
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  })

  const formatDate = (iso: string) =>
    new Date(iso).toLocaleDateString('es-CO', { day: 'numeric', month: 'short', year: 'numeric' })

  return (
    <AdminLayout pendingCount={pendingCount}>
      <div style={{ padding: '32px', fontFamily: typography.body }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 32 }}>
          <div>
            <h1 style={{ fontSize: 28, fontWeight: 700, color: colors.text, margin: 0 }}>Cola de revisión</h1>
            <p style={{ fontSize: 14, color: colors.textMuted, marginTop: 4 }}>Casos pendientes de evaluación legal</p>
          </div>
          <button style={{
            padding: '10px 20px',
            background: colors.primary,
            color: '#fff',
            border: 'none',
            borderRadius: 8,
            fontWeight: 600,
            cursor: 'pointer',
            fontSize: 13,
            fontFamily: typography.body,
          }}>
            Asignar caso
          </button>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 24, marginBottom: 40 }}>
          <StatCard label="Pendientes" value={pendingCount} change={`${cases.filter(c => c.status === 'PENDING_REVIEW').length} nuevos`} positive />
          <StatCard label="En revisión" value={reviewingCount} change={`${reviewingCount} en progreso`} positive />
          <StatCard label="Aprobados" value={approvedCount} change={`${approvedCount} total`} positive />
          <StatCard label="Tasa de aprobación" value={`${approvalRate}%`} change="últimos 30 días" positive={approvalRate >= 70} />
        </div>

        <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 20, color: colors.text }}>Casos pendientes</h2>

        <div style={{ display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap' }}>
          <select
            style={filterStyle}
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="all">Todos los casos</option>
            <option value="PENDING_REVIEW">Pendiente revisión</option>
            <option value="LAWYER_REVIEWING">En revisión</option>
            <option value="APPROVED">Aprobados</option>
            <option value="ILLEGIBLE_DOCUMENT_BLOCKED">Doc. ilegible</option>
          </select>
          <select
            style={filterStyle}
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
          >
            <option value="date">Ordenar por fecha</option>
            <option value="priority">Más urgentes</option>
          </select>
        </div>

        <div style={{
          background: colors.surface,
          borderRadius: 8,
          border: `1px solid ${colors.border}`,
          overflow: 'hidden',
        }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ background: colors.bg, borderBottom: `1px solid ${colors.border}` }}>
                <th style={thStyle}>Caso</th>
                <th style={thStyle}>Consumidor/a</th>
                <th style={thStyle}>Escenario</th>
                <th style={thStyle}>Estado</th>
                <th style={thStyle}>Fecha</th>
                <th style={thStyle}>Acción</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={6} style={emptyStyle}>Cargando...</td></tr>
              ) : sortedCases.length === 0 ? (
                <tr><td colSpan={6} style={emptyStyle}>No hay casos en la cola</td></tr>
              ) : (
                sortedCases.map((c) => {
                  const cfg = STATUS_CONFIG[c.status] || { bg: 'rgba(139,134,128,0.15)', color: colors.textMuted, label: c.status.replace(/_/g, ' ') }
                  return (
                    <tr
                      key={c.case_id}
                      style={{ cursor: 'pointer' }}
                      onMouseEnter={(e) => (e.currentTarget.style.background = colors.bg)}
                      onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                      onClick={() => navigate(`/admin/cases/${c.case_id}`)}
                    >
                      <td style={tdStyle}>
                        <span style={{ fontWeight: 600, color: colors.primary }}>#{c.case_id.slice(-6)}</span>
                      </td>
                      <td style={tdStyle}>
                        <span style={{ fontWeight: 500, color: colors.text }}>{c.consumer_name || 'Sin nombre'}</span>
                      </td>
                      <td style={tdStyle}>
                        <span style={{ color: colors.textMuted, fontSize: 12 }}>
                          {SCENARIO_LABEL[c.case_type] || c.case_type}
                        </span>
                        {c.docs_need_review && (
                          <span style={{
                            display: 'inline-block',
                            marginLeft: 8,
                            background: 'rgba(184,134,11,0.15)',
                            color: '#B8860B',
                            borderRadius: 4,
                            padding: '2px 6px',
                            fontSize: 10,
                            fontWeight: 700,
                          }}>
                            Doc. pendiente
                          </span>
                        )}
                      </td>
                      <td style={tdStyle}>
                        <span style={{
                          display: 'inline-block',
                          padding: '6px 12px',
                          borderRadius: 4,
                          fontSize: 11,
                          fontWeight: 700,
                          textTransform: 'uppercase',
                          background: cfg.bg,
                          color: cfg.color,
                        }}>
                          {cfg.label}
                        </span>
                      </td>
                      <td style={{ ...tdStyle, color: colors.textMuted, fontSize: 12 }}>{formatDate(c.created_at)}</td>
                      <td style={tdStyle}>
                        <button
                          style={actionBtnStyle}
                          onClick={(e) => { e.stopPropagation(); navigate(`/admin/cases/${c.case_id}`) }}
                          onMouseEnter={(e) => { e.currentTarget.style.background = colors.primary; e.currentTarget.style.color = '#fff' }}
                          onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = colors.primary }}
                        >
                          Revisar
                        </button>
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </AdminLayout>
  )
}

function StatCard({ label, value, change, positive }: { label: string; value: string | number; change: string; positive: boolean }) {
  return (
    <div style={{
      background: colors.surface,
      padding: 24,
      borderRadius: 8,
      border: `1px solid ${colors.border}`,
      transition: 'all 0.3s ease',
    }}>
      <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: colors.textMuted, letterSpacing: 0.5, marginBottom: 12 }}>
        {label}
      </div>
      <div style={{ fontSize: 28, fontWeight: 700, color: colors.primary, marginBottom: 8 }}>
        {value}
      </div>
      <div style={{ fontSize: 12, color: positive ? colors.success : colors.danger }}>
        {change}
      </div>
    </div>
  )
}

const thStyle: React.CSSProperties = {
  padding: '16px',
  textAlign: 'left',
  fontWeight: 700,
  color: '#5C5854',
  textTransform: 'uppercase',
  fontSize: 11,
  letterSpacing: 0.5,
}

const tdStyle: React.CSSProperties = {
  padding: '20px 16px',
  borderBottom: `1px solid ${colors.border}`,
}

const emptyStyle: React.CSSProperties = {
  textAlign: 'center',
  color: colors.textMuted,
  padding: 48,
}

const filterStyle: React.CSSProperties = {
  padding: '10px 12px',
  border: `1px solid ${colors.border}`,
  borderRadius: 6,
  fontSize: 13,
  background: colors.surface,
  color: colors.text,
  cursor: 'pointer',
  fontFamily: "'Plus Jakarta Sans', sans-serif",
}

const actionBtnStyle: React.CSSProperties = {
  padding: '8px 16px',
  border: `1px solid ${colors.primary}`,
  background: 'transparent',
  color: colors.primary,
  borderRadius: 4,
  cursor: 'pointer',
  fontSize: 12,
  fontWeight: 600,
  transition: 'all 0.3s ease',
  fontFamily: "'Plus Jakarta Sans', sans-serif",
}
