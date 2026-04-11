import React from 'react'
import { Navigate } from 'react-router-dom'

export default function PrivateRoute({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('justicia_token')
  if (!token) return <Navigate to="/admin/login" replace />
  return <>{children}</>
}
