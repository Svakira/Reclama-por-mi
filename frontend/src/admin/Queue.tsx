import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/client'

const SCENARIO_LABEL: Record<string, string> = {
  A: 'Producto defectuoso',
  B: 'Cobro indebido',
  C: 'Telecomunicaciones',
  UNKNOWN: 'Sin clasificar',
}

const STATUS_COLORS: Record<string, string> = {
  PENDING_REVIEW: '#fbbf24',
  LAWYER_REVIEWING: '#60a5fa',
  APPROVED: '#34d399',
  SUBMITTED_TO_SIC: '#86efac',
  PENDING_CLAIM_DECISION: '#f87171',
  ILLEGIBLE_DOCUMENT_BLOCKED: '#fb923c',
  DOCS_REQUESTED: '#a78bfa',
  CLOSED: '#64748b',
}

const s: Record<string, React.CSSProperties> = {
  page: { minHeight: '100vh', background: '#0f172a', padding: '24px 20px' },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    maxWidth: 900,
    margin: '0 auto 24px',
  },
  title: { fontSize: 22, fontWeight: 800, color: '#38bdf8' },
  logout: {
    background: 'transparent',
    border: '1px solid #334155',
    borderRadius: 8,
    padding: '6px 14px',
    color: '#94a3b8',
    cursor: 'pointer',
    fontSize: 13,
  },
  table: {
    width: '100%',
    maxWidth: 900,
    margin: '0 auto',
    background: '#1e293b',
    borderRadius: 12,
    border: '1px solid #334155',
    overflow: 'hidden',
  },
  th: {
    textAlign: 'left' as const,
    padding: '12px 16px',
    fontSize: 12,
    fontWeight: 600,
    color: '#64748b',
    textTransform: 'uppercase' as const,
    borderBottom: '1px solid #334155',
    background: '#0f172a',
  },
  td: {
    padding: '14px 16px',
    fontSize: 14,
    color: '#e2e8f0',
    borderBottom: '1px solid #1e293b',
    cursor: 'pointer',
  },
  empty: { textAlign: 'center' as const, color: '#64748b', padding: 40 },
}

const badgeStyle = (color: string): React.CSSProperties => ({
  display: 'inline-block',
  background: color + '22',
  color,
  border: `1px solid ${color}44`,
  borderRadius: 6,
  padding: '2px 8px',
  fontSize: 11,
  fontWeight: 600,
})

const priorityStyle = (p: number): React.CSSProperties => ({
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  width: 24,
  height: 24,
  borderRadius: '50%',
  background: p >= 4 ? '#f87171' : p >= 3 ? '#fbbf24' : '#334155',
  color: '#fff',
  fontSize: 12,
  fontWeight: 700,
})

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
  const navigate = useNavigate()
  const lawyerName = localStorage.getItem('justicia_lawyer_name') || 'Abogado'

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

  function logout() {
    localStorage.removeItem('justicia_token')
    navigate('/admin/login')
  }

  const formatDate = (iso: string) =>
    new Date(iso).toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: 'numeric' })

  return (
    <div style={s.page}>
      <div style={s.header}>
        <div>
          <div style={s.title}>JusticIA — Panel del Abogado</div>
          <div style={{ fontSize: 13, color: '#64748b', marginTop: 2 }}>Bienvenido, {lawyerName}</div>
        </div>
        <button style={s.logout} onClick={logout}>Cerrar sesión</button>
      </div>

      <div style={s.table}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={s.th}>P</th>
              <th style={s.th}>ID del caso</th>
              <th style={s.th}>Consumidor</th>
              <th style={s.th}>Tipo</th>
              <th style={s.th}>Estado</th>
              <th style={s.th}>Alertas</th>
              <th style={s.th}>Fecha</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={7} style={s.empty}>Cargando...</td></tr>
            ) : cases.length === 0 ? (
              <tr><td colSpan={7} style={s.empty}>No hay casos pendientes</td></tr>
            ) : (
              cases.map((c) => (
                <tr
                  key={c.case_id}
                  onClick={() => navigate(`/admin/cases/${c.case_id}`)}
                  style={{ cursor: 'pointer' }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = '#263045')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                >
                  <td style={s.td}>
                  <span style={priorityStyle(c.priority)}>{c.priority}</span>
                  </td>
                  <td style={{ ...s.td, fontFamily: 'monospace', fontSize: 12, color: '#94a3b8' }}>{c.case_id}</td>
                  <td style={s.td}>{c.consumer_name}</td>
                  <td style={s.td}>
                    <span style={badgeStyle('#60a5fa')}>{SCENARIO_LABEL[c.case_type] || c.case_type}</span>
                  </td>
                  <td style={s.td}>
                    <span style={badgeStyle(STATUS_COLORS[c.status] || '#64748b')}>
                      {c.status.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td style={s.td}>
                    {(c.validation_flags || []).filter((f) => f.severity === 'warning').length > 0 && (
                      <span style={badgeStyle('#fb923c')}>
                        ⚠ {(c.validation_flags || []).filter((f) => f.severity === 'warning').length}
                      </span>
                    )}
                  </td>
                  <td style={{ ...s.td, color: '#64748b', fontSize: 12 }}>{formatDate(c.created_at)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
