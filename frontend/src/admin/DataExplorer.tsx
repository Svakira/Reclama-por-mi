import React, { useEffect, useMemo, useState } from 'react'
import api from '../api/client'
import AdminLayout from './AdminLayout'
import { colors, shadows } from '../styles/tokens'

interface DocRow {
  case_id: string
  consumer_name: string
  filename: string
  doc_type: string
  confidence: number
}

export default function DataExplorer() {
  const [rows, setRows] = useState<DocRow[]>([])
  const [loading, setLoading] = useState(true)
  const [query, setQuery] = useState('')

  useEffect(() => {
    loadRows()
  }, [])

  async function loadRows() {
    try {
      const res = await api.get('/cases/documents/index')
      setRows(Array.isArray(res.data) ? res.data : [])
    } catch {
      setRows([])
    }
    setLoading(false)
  }

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return rows
    return rows.filter((r) => [r.case_id, r.consumer_name, r.filename, r.doc_type].join(' ').toLowerCase().includes(q))
  }, [rows, query])

  const s: Record<string, React.CSSProperties> = {
    page: { padding: 32 },
    title: { margin: '0 0 6px 0', fontSize: 28, fontWeight: 700, color: colors.text },
    subtitle: { margin: '0 0 20px 0', color: colors.textMuted, fontSize: 14 },
    input: {
      width: '100%',
      maxWidth: 460,
      border: `1px solid ${colors.border}`,
      borderRadius: 8,
      padding: '10px 12px',
      fontSize: 14,
      marginBottom: 18,
      outline: 'none',
      background: colors.surface,
      color: colors.text,
    },
    card: {
      background: colors.surface,
      border: `1px solid ${colors.border}`,
      borderRadius: 10,
      boxShadow: shadows.card,
      overflow: 'hidden',
    },
    th: {
      textAlign: 'left' as const,
      padding: '12px 14px',
      fontSize: 11,
      fontWeight: 700,
      color: colors.textMuted,
      textTransform: 'uppercase' as const,
      letterSpacing: '0.05em',
      background: colors.neutral50,
      borderBottom: `1px solid ${colors.border}`,
    },
    td: {
      padding: '12px 14px',
      fontSize: 13,
      color: colors.text,
      borderBottom: `1px solid ${colors.border}`,
    },
    empty: { padding: 24, textAlign: 'center' as const, color: colors.textMuted },
  }

  return (
    <AdminLayout>
      <div style={s.page}>
        <h1 style={s.title}>Datos cargados</h1>
        <p style={s.subtitle}>Explora documentos por nombre de archivo, consumidor o tipo.</p>

        <input
          style={s.input}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Buscar por archivo, consumidor, caso o tipo de documento"
        />

        <div style={s.card}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={s.th}>Caso</th>
                <th style={s.th}>Consumidor</th>
                <th style={s.th}>Archivo</th>
                <th style={s.th}>Tipo</th>
                <th style={s.th}>Confianza</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={5} style={s.empty}>Cargando...</td></tr>
              ) : filtered.length === 0 ? (
                <tr><td colSpan={5} style={s.empty}>No hay documentos para mostrar.</td></tr>
              ) : (
                filtered.map((r, i) => (
                  <tr key={`${r.case_id}-${r.filename}-${i}`}>
                    <td style={s.td}>{r.case_id}</td>
                    <td style={s.td}>{r.consumer_name}</td>
                    <td style={{ ...s.td, fontFamily: 'monospace', fontSize: 12 }}>{r.filename}</td>
                    <td style={s.td}>{r.doc_type}</td>
                    <td style={s.td}>{Math.round((r.confidence || 0) * 100)}%</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </AdminLayout>
  )
}
