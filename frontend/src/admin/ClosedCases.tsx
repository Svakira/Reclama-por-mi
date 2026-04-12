import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/client'
import AdminLayout from './AdminLayout'
import { colors, typography } from '../styles/tokens'

interface Case {
  case_id: string
  consumer_name: string
  status: string
  case_type: string
  created_at: string
}

const SCENARIO_LABEL: Record<string, string> = {
  A: 'Producto defectuoso',
  B: 'Cobro indebido',
  C: 'Telecomunicaciones',
  UNKNOWN: 'Sin clasificar',
}

export default function ClosedCases() {
  const [cases, setCases] = useState<Case[]>([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    api.get('/cases').then(r => {
      const closed = (r.data || []).filter((c: Case) => c.status === 'CLOSED')
      setCases(closed)
    }).finally(() => setLoading(false))
  }, [])

  const thStyle: React.CSSProperties = { textAlign: 'left', padding: '14px 16px', fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: colors.textMuted, borderBottom: `1px solid ${colors.border}` }
  const tdStyle: React.CSSProperties = { padding: '14px 16px', borderBottom: `1px solid ${colors.border}`, fontSize: 13 }

  return (
    <AdminLayout>
      <div style={{ padding: 28 }}>
        <h2 style={{ margin: '0 0 20px', fontSize: 22, fontWeight: 700, color: colors.text, fontFamily: typography.heading }}>Casos cerrados / rechazados</h2>
        {loading ? (
          <p style={{ color: colors.textMuted }}>Cargando...</p>
        ) : cases.length === 0 ? (
          <p style={{ color: colors.textMuted }}>No hay casos cerrados.</p>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', background: colors.surface, borderRadius: 8, overflow: 'hidden' }}>
            <thead>
              <tr>
                <th style={thStyle}>Caso</th>
                <th style={thStyle}>Consumidor</th>
                <th style={thStyle}>Tipo</th>
                <th style={thStyle}>Fecha</th>
              </tr>
            </thead>
            <tbody>
              {cases.map(c => (
                <tr key={c.case_id} style={{ cursor: 'pointer' }} onClick={() => navigate(`/admin/cases/${c.case_id}`)}>
                  <td style={tdStyle}><span style={{ fontWeight: 600, color: colors.primary }}>{c.case_id}</span></td>
                  <td style={tdStyle}>{c.consumer_name || 'Sin nombre'}</td>
                  <td style={tdStyle}><span style={{ color: colors.textMuted, fontSize: 12 }}>{SCENARIO_LABEL[c.case_type] || c.case_type}</span></td>
                  <td style={tdStyle}><span style={{ color: colors.textMuted, fontSize: 12 }}>{new Date(c.created_at).toLocaleDateString('es-CO')}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </AdminLayout>
  )
}
