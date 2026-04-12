// frontend/src/admin/Login.tsx
import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/client'
import { colors, shadows } from '../styles/tokens'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const res = await api.post('/auth/login', { email, password })
      localStorage.setItem('justicia_token', res.data.token)
      localStorage.setItem('justicia_lawyer_name', res.data.name)
      localStorage.setItem('justicia_lawyer_email', email)
      navigate('/admin')
    } catch {
      setError('Credenciales incorrectas. Intenta de nuevo.')
    }
    setLoading(false)
  }

  const s: Record<string, React.CSSProperties> = {
    page: {
      minHeight: '100vh',
      background: colors.bg,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: 20,
    },
    card: {
      background: colors.surface,
      border: `1px solid ${colors.border}`,
      borderRadius: 12,
      padding: 40,
      width: '100%',
      maxWidth: 400,
      boxShadow: shadows.modal,
    },
    logoWrap: {
      textAlign: 'center',
      marginBottom: 28,
    },
    logoImgWrap: {
      width: 64,
      height: 64,
      borderRadius: 14,
      overflow: 'hidden',
      margin: '0 auto 12px',
      border: `1px solid ${colors.border}`,
    },
    logoImg: {
      width: '100%',
      height: '100%',
      objectFit: 'cover',
      display: 'block',
    },
    logoText: {
      fontSize: 26,
      fontWeight: 700,
      color: colors.primary,
    },
    logoSub: {
      fontSize: 14,
      color: colors.textMuted,
      marginTop: 4,
    },
    label: {
      fontSize: 13,
      fontWeight: 600,
      color: colors.text,
      marginBottom: 6,
      display: 'block',
    },
    input: {
      width: '100%',
      background: colors.surface,
      border: `1px solid ${colors.border}`,
      borderRadius: 6,
      padding: '10px 14px',
      color: colors.text,
      fontSize: 14,
      marginBottom: 16,
      outline: 'none',
      boxSizing: 'border-box',
    },
    btn: {
      width: '100%',
      background: colors.primary,
      border: 'none',
      borderRadius: 6,
      padding: '12px 0',
      color: '#fff',
      fontWeight: 700,
      fontSize: 15,
      cursor: 'pointer',
    },
    error: {
      color: colors.danger,
      fontSize: 13,
      marginTop: 10,
      textAlign: 'center',
    },
  }

  return (
    <div style={s.page}>
      <div style={s.card}>
        <div style={s.logoWrap}>
          <div style={s.logoImgWrap}>
            <img src="/logo-icon.png" alt="RECLAMA POR MI" style={s.logoImg} />
          </div>
          <div style={s.logoText}>RECLAMA POR MI</div>
          <div style={s.logoSub}>Panel del Abogado — Clínica Jurídica ICESI</div>
        </div>
        <form onSubmit={handleLogin}>
          <label style={s.label}>Correo electrónico</label>
          <input
            style={s.input}
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="abogado@icesi.edu.co"
            required
          />
          <label style={s.label}>Contraseña</label>
          <input
            style={s.input}
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <button style={s.btn} type="submit" disabled={loading}>
            {loading ? 'Ingresando...' : 'Iniciar sesión'}
          </button>
          {error && <div style={s.error}>{error}</div>}
        </form>
      </div>
    </div>
  )
}
