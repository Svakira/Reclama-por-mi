import React from 'react'
import AdminLayout from './AdminLayout'
import { colors, typography } from '../styles/tokens'

export default function Settings() {
  const lawyerName = localStorage.getItem('justicia_lawyer_name') || 'Abogado'
  const lawyerEmail = localStorage.getItem('justicia_lawyer_email') || ''

  const cardStyle: React.CSSProperties = {
    background: colors.surface,
    border: `1px solid ${colors.border}`,
    borderRadius: 8,
    padding: 20,
    marginBottom: 16,
  }

  const labelStyle: React.CSSProperties = {
    fontSize: 11,
    fontWeight: 700,
    textTransform: 'uppercase',
    color: colors.textMuted,
    marginBottom: 4,
  }

  return (
    <AdminLayout>
      <div style={{ padding: 28, maxWidth: 600 }}>
        <h2 style={{ margin: '0 0 20px', fontSize: 22, fontWeight: 700, color: colors.text, fontFamily: typography.display }}>Configuración</h2>

        <div style={cardStyle}>
          <h3 style={{ margin: '0 0 14px', fontSize: 14, fontWeight: 700, color: colors.text }}>Perfil del abogado</h3>
          <div style={{ marginBottom: 12 }}>
            <div style={labelStyle}>Nombre</div>
            <div style={{ fontSize: 14, color: colors.text, fontWeight: 600 }}>{lawyerName}</div>
          </div>
          <div>
            <div style={labelStyle}>Correo</div>
            <div style={{ fontSize: 14, color: colors.text }}>{lawyerEmail || 'No configurado'}</div>
          </div>
        </div>

        <div style={cardStyle}>
          <h3 style={{ margin: '0 0 14px', fontSize: 14, fontWeight: 700, color: colors.text }}>Notificaciones WhatsApp</h3>
          <div style={{ fontSize: 13, color: colors.textMuted, lineHeight: 1.7 }}>
            <div>Estado: <strong style={{ color: colors.success }}>Configurado</strong></div>
            <div>Las notificaciones se envían vía Twilio cuando el consumidor proporciona su número.</div>
          </div>
        </div>

        <div style={cardStyle}>
          <h3 style={{ margin: '0 0 14px', fontSize: 14, fontWeight: 700, color: colors.text }}>Sistema</h3>
          <div style={{ fontSize: 13, color: colors.textMuted, lineHeight: 1.7 }}>
            <div>Version: <strong>RECLAMA POR MI v1.0</strong></div>
            <div>Motor IA: <strong>Groq (Llama 3.3 70B)</strong></div>
            <div>Base de datos: <strong>Firestore (In-memory dev)</strong></div>
          </div>
        </div>
      </div>
    </AdminLayout>
  )
}
