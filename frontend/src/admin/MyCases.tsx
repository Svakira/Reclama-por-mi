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
  lawyer_id?: string
}

const SCENARIO_LABEL: Record<string, string> = {
  A: 'Producto defectuoso',
  B: 'Cobro indebido',
  C: 'Telecomunicaciones',
  UNKNOWN: 'Sin clasificar',
}

const STATUS_LABEL: Record<string, string> = {
  PENDING_REVIEW: 'Pendiente',
  LAWYER_REVIEWING: 'En revisión',
  APPROVED: 'Aprobado',
  SUBMITTED_TO_SIC: 'Enviado SIC',
  PENDING_CLAIM_DECISION: 'Decisión requerida',
  DOCS_REQUESTED: 'Docs. solicitados',
  CLOSED: 'Cerrado',
}

export default function MyCases() {
  const [cases, setCases] = useState<Case[]>([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()
  const lawyerName = localStorage.getItem('justicia_lawyer_name') || ''

  useEffect(() => {
    api.get('/cases').then(r => {
      const allCases = r.data || []
      const mine = allCases.filter((c: Case) =>
        c.status === 'LAWYER_REVIEWING' || c.status === 'APPROVED' || c.status === 'SUBMITTED_TO_SIC'
      )
      setCases(mine)
    }).finally(() => setLoading(false))
  }, [])

  const thStyle: React.CSSProperties = { textAlign: 'left', padding: '14px 16px', fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: colors.textMuted, borderBottom: `1px solid ${colors.border}` }
  const tdStyle: React.CSSProperties = { padding: '14px 16px', borderBottom: `1px solid ${colors.border}`, fontSize: 13 }

  return (
    <AdminLayout>
      <div style={{ padding: 28 }}>
        <h2 style={{ margin: '0 0 20px', fontSize: 22, fontWeight: 700, color: colors.text, fontFamily: typography.heading }}>Mis casos</h2>
        <p style={{ color: colors.textMuted, fontSize: 13, marginBottom: 20 }}>Casos asignados a {lawyerName || 'ti'} o en los que has intervenido.</p>
        {loading ? (
          <p style={{ color: colors.textMuted }}>Cargando...</p>
        ) : cases.length === 0 ? (
          <p style={{ color: colors.textMuted }}>No tienes casos asignados aún.</p>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', background: colors.surface, borderRadius: 8, overflow: 'hidden' }}>
            <thead>
              <tr>
                <th style={thStyle}>Caso</th>
                <th style={thStyle}>Consumidor</th>
                <th style={thStyle}>Tipo</th>
                <th style={thStyle}>Estado</th>
                <th style={thStyle}>Fecha</th>
              </tr>
            </thead>
            <tbody>
              {cases.map(c => (
                <tr key={c.case_id} style={{ cursor: 'pointer' }} onClick={() => navigate(`/admin/cases/${c.case_id}`)}>
                  <td style={tdStyle}><span style={{ fontWeight: 600, color: colors.primary }}>{c.case_id}</span></td>
                  <td style={tdStyle}>{c.consumer_name || 'Sin nombre'}</td>
                  <td style={tdStyle}><span style={{ color: colors.textMuted, fontSize: 12 }}>{SCENARIO_LABEL[c.case_type] || c.case_type}</span></td>
                  <td style={tdStyle}><span style={{ fontSize: 12, color: colors.textMuted }}>{STATUS_LABEL[c.status] || c.status}</span></td>
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
