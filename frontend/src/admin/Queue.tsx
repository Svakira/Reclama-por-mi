// frontend/src/admin/Queue.tsx
import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/client'
import AdminLayout from './AdminLayout'
import Badge from '../components/Badge'
import { colors, shadows } from '../styles/tokens'

const SCENARIO_LABEL: Record<string, string> = {
  A: 'Producto defectuoso',
  B: 'Cobro indebido',
  C: 'Telecomunicaciones',
  UNKNOWN: 'Sin clasificar',
}

type BadgeStatus = 'pending' | 'active' | 'approved' | 'rejected' | 'ready' | 'blocked' | 'info'

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

interface Case {
  case_id: string
  consumer_name: string
  status: string
  priority: number
  case_type: string
  created_at: string
  validation_flags?: { severity: string }[]
}

export default function Queue() {
  const [cases, setCases] = useState<Case[]>([])
  const [loading, setLoading] = useState(true)
  const [query, setQuery] = useState('')
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
    } catch {
      // handled by axios interceptor
    }
    setLoading(false)
  }

  const pendingCount = cases.filter((c) =>
    ['PENDING_REVIEW', 'PENDING_CLAIM_DECISION', 'LAWYER_REVIEWING'].includes(c.status)
  ).length

  const filteredCases = cases.filter((c) => {
    const q = query.trim().toLowerCase()
    if (!q) return true
    return [c.case_id, c.consumer_name, c.status, c.case_type].join(' ').toLowerCase().includes(q)
  })

  const formatDate = (iso: string) =>
    new Date(iso).toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: 'numeric' })

  const s: Record<string, React.CSSProperties> = {
    page: { padding: '32px 32px' },
    header: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'flex-start',
      marginBottom: 20,
    },
    title: {
      fontSize: 22,
      fontWeight: 700,
      color: colors.text,
      margin: 0,
    },
    subtitle: {
      marginTop: 6,
      color: colors.textMuted,
      fontSize: 14,
    },
    assignBtn: {
      padding: '10px 20px',
      background: colors.primary,
      color: '#fff',
      border: 'none',
      borderRadius: 8,
      fontWeight: 600,
      cursor: 'pointer',
      fontSize: 13,
    },
    countBadge: {
      background: colors.primary,
      color: '#fff',
      borderRadius: 12,
      padding: '2px 10px',
      fontSize: 13,
      fontWeight: 700,
    },
    card: {
      background: colors.surface,
      border: `1px solid ${colors.border}`,
      borderRadius: 10,
      boxShadow: shadows.card,
      overflow: 'hidden',
    },
    filters: {
      display: 'flex',
      gap: 12,
      marginBottom: 14,
      flexWrap: 'wrap',
    },
    searchInput: {
      minWidth: 360,
      maxWidth: 480,
      width: '100%',
      border: `1px solid ${colors.border}`,
      borderRadius: 8,
      padding: '10px 12px',
      fontSize: 13,
      outline: 'none',
      color: colors.text,
      background: colors.surface,
    },
    th: {
      textAlign: 'left' as const,
      padding: '12px 16px',
      fontSize: 12,
      fontWeight: 600,
      color: colors.textMuted,
      textTransform: 'uppercase' as const,
      letterSpacing: '0.05em',
      borderBottom: `1px solid ${colors.border}`,
      background: colors.bg,
    },
    td: {
      padding: '14px 16px',
      fontSize: 14,
      color: colors.text,
      borderBottom: `1px solid ${colors.border}`,
    },
    reviewBtn: {
      background: 'transparent',
      border: `1px solid ${colors.primary}`,
      borderRadius: 6,
      padding: '6px 14px',
      color: colors.primary,
      cursor: 'pointer',
      fontSize: 13,
      fontWeight: 600,
    },
    empty: { textAlign: 'center' as const, color: colors.textMuted, padding: 48 },
  }

  return (
    <AdminLayout pendingCount={pendingCount}>
      <div style={s.page}>
        <div style={s.header}>
          <div>
            <h1 style={s.title}>Cola de revisión</h1>
            <p style={s.subtitle}>Casos pendientes de evaluación legal</p>
          </div>
          <button style={s.assignBtn}>Asignar caso</button>
        </div>

        <div style={s.filters}>
          <input
            style={s.searchInput}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Buscar por caso, consumidor, estado o escenario"
          />
          {pendingCount > 0 && <span style={s.countBadge}>{pendingCount} pendientes</span>}
        </div>

        <div style={s.card}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={s.th}>Caso</th>
                <th style={s.th}>Consumidora</th>
                <th style={s.th}>Escenario</th>
                <th style={s.th}>Estado</th>
                <th style={s.th}>Fecha</th>
                <th style={s.th}>Acción</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={6} style={s.empty}>Cargando...</td></tr>
              ) : filteredCases.length === 0 ? (
                <tr><td colSpan={6} style={s.empty}>No hay casos en la cola</td></tr>
              ) : (
                filteredCases.map((c) => {
                  const badge = statusToBadge(c.status)
                  return (
                    <tr
                      key={c.case_id}
                      onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(26,58,92,0.04)')}
                      onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                    >
                      <td style={{ ...s.td, fontFamily: 'monospace', fontSize: 12, color: colors.textMuted }}>
                        #{c.case_id.slice(-6)}
                      </td>
                      <td style={{ ...s.td, fontWeight: 500 }}>{c.consumer_name}</td>
                      <td style={s.td}>
                        <span style={{ fontSize: 13, color: colors.textMuted }}>
                          {SCENARIO_LABEL[c.case_type] || c.case_type}
                        </span>
                      </td>
                      <td style={s.td}>
                        <Badge status={badge.status} label={badge.label} />
                      </td>
                      <td style={{ ...s.td, color: colors.textMuted, fontSize: 13 }}>{formatDate(c.created_at)}</td>
                      <td style={s.td}>
                        <button
                          style={s.reviewBtn}
                          onClick={() => navigate(`/admin/cases/${c.case_id}`)}
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
