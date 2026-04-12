import React, { useEffect, useState } from 'react'
import api from '../api/client'
import AdminLayout from './AdminLayout'
import { colors, typography } from '../styles/tokens'

interface Stats {
  total: number
  pending: number
  reviewing: number
  approved: number
  closed: number
  byType: Record<string, number>
}

export default function Reports() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/cases').then(r => {
      const cases = r.data || []
      const s: Stats = { total: cases.length, pending: 0, reviewing: 0, approved: 0, closed: 0, byType: {} }
      for (const c of cases) {
        if (c.status === 'PENDING_REVIEW' || c.status === 'PENDING_CLAIM_DECISION') s.pending++
        else if (c.status === 'LAWYER_REVIEWING') s.reviewing++
        else if (c.status === 'APPROVED' || c.status === 'DELIVERED_TO_ROSA' || c.status === 'SUBMITTED_TO_SIC') s.approved++
        else if (c.status === 'CLOSED') s.closed++
        s.byType[c.case_type] = (s.byType[c.case_type] || 0) + 1
      }
      setStats(s)
    }).finally(() => setLoading(false))
  }, [])

  const cardStyle: React.CSSProperties = {
    background: colors.surface,
    border: `1px solid ${colors.border}`,
    borderRadius: 8,
    padding: 20,
  }

  const SCENARIO_LABEL: Record<string, string> = {
    A: 'Producto defectuoso',
    B: 'Cobro indebido',
    C: 'Telecomunicaciones',
    UNKNOWN: 'Sin clasificar',
  }

  return (
    <AdminLayout>
      <div style={{ padding: 28 }}>
        <h2 style={{ margin: '0 0 20px', fontSize: 22, fontWeight: 700, color: colors.text, fontFamily: typography.display }}>Reportes</h2>
        {loading || !stats ? (
          <p style={{ color: colors.textMuted }}>Cargando estadísticas...</p>
        ) : (
          <>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16, marginBottom: 28 }}>
              <div style={cardStyle}>
                <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: colors.textMuted }}>Total casos</div>
                <div style={{ fontSize: 32, fontWeight: 700, color: colors.text, marginTop: 6 }}>{stats.total}</div>
              </div>
              <div style={cardStyle}>
                <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: colors.textMuted }}>Pendientes</div>
                <div style={{ fontSize: 32, fontWeight: 700, color: colors.warning, marginTop: 6 }}>{stats.pending}</div>
              </div>
              <div style={cardStyle}>
                <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: colors.textMuted }}>Aprobados</div>
                <div style={{ fontSize: 32, fontWeight: 700, color: colors.success, marginTop: 6 }}>{stats.approved}</div>
              </div>
              <div style={cardStyle}>
                <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: colors.textMuted }}>Cerrados</div>
                <div style={{ fontSize: 32, fontWeight: 700, color: colors.textMuted, marginTop: 6 }}>{stats.closed}</div>
              </div>
            </div>

            <div style={cardStyle}>
              <h3 style={{ margin: '0 0 14px', fontSize: 14, fontWeight: 700, color: colors.text }}>Distribución por tipo</h3>
              {Object.entries(stats.byType).map(([type, count]) => (
                <div key={type} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: `1px solid ${colors.border}`, fontSize: 13 }}>
                  <span style={{ color: colors.text }}>{SCENARIO_LABEL[type] || type}</span>
                  <span style={{ fontWeight: 700, color: colors.primary }}>{count}</span>
                </div>
              ))}
            </div>

            <div style={{ marginTop: 20 }}>
              <div style={cardStyle}>
                <h3 style={{ margin: '0 0 10px', fontSize: 14, fontWeight: 700, color: colors.text }}>Tasa de aprobación</h3>
                <div style={{ fontSize: 24, fontWeight: 700, color: colors.success }}>
                  {stats.total > 0 ? Math.round((stats.approved / stats.total) * 100) : 0}%
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </AdminLayout>
  )
}
