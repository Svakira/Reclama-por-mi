import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/client'

const s: Record<string, React.CSSProperties> = {
  page: {
    minHeight: '100vh',
    background: 'linear-gradient(135deg, #0f172a, #1e293b)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 20,
  },
  card: {
    background: '#1e293b',
    border: '1px solid #334155',
    borderRadius: 16,
    padding: 32,
    width: '100%',
    maxWidth: 360,
  },
  title: { fontSize: 24, fontWeight: 800, color: '#38bdf8', marginBottom: 4 },
  sub: { fontSize: 13, color: '#64748b', marginBottom: 24 },
  label: { fontSize: 13, color: '#94a3b8', marginBottom: 6, display: 'block' },
  input: {
    width: '100%',
    background: '#0f172a',
    border: '1px solid #334155',
    borderRadius: 8,
    padding: '10px 14px',
    color: '#f1f5f9',
    fontSize: 14,
    marginBottom: 16,
    outline: 'none',
  },
  btn: {
    width: '100%',
    background: '#0ea5e9',
    border: 'none',
    borderRadius: 8,
    padding: '12px 0',
    color: '#fff',
    fontWeight: 700,
    fontSize: 15,
    cursor: 'pointer',
  },
  error: { color: '#f87171', fontSize: 13, marginTop: 10 },
}

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
      navigate('/admin')
    } catch {
      setError('Credenciales incorrectas. Intenta de nuevo.')
    }
    setLoading(false)
  }

  return (
    <div style={s.page}>
      <div style={s.card}>
        <div style={s.title}>JusticIA</div>
        <div style={s.sub}>Panel del Abogado — Clínica Jurídica ICESI</div>
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
            {loading ? 'Ingresando...' : 'Ingresar'}
          </button>
          {error && <div style={s.error}>{error}</div>}
        </form>
      </div>
    </div>
  )
}
