import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import ChatView from './app/ChatView'
import StatusView from './app/StatusView'
import Login from './admin/Login'
import Queue from './admin/Queue'
import CaseDetail from './admin/CaseDetail'
import PrivateRoute from './admin/PrivateRoute'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        {/* Rosa's public interface */}
        <Route path="/app" element={<ChatView />} />
        <Route path="/app/status/:caseId" element={<StatusView />} />

        {/* Lawyer dashboard */}
        <Route path="/admin/login" element={<Login />} />
        <Route path="/admin" element={<PrivateRoute><Queue /></PrivateRoute>} />
        <Route path="/admin/cases/:caseId" element={<PrivateRoute><CaseDetail /></PrivateRoute>} />

        {/* Default redirect */}
        <Route path="/" element={<Navigate to="/app" replace />} />
        <Route path="*" element={<Navigate to="/app" replace />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
)
