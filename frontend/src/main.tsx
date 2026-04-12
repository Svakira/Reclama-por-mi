import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import ChatView from './app/ChatView'
import LandingView from './app/LandingView'
import StatusView from './app/StatusView'
import Login from './admin/Login'
import Queue from './admin/Queue'
import CaseDetail from './admin/CaseDetail'
import DataExplorer from './admin/DataExplorer'
import ApprovedCases from './admin/ApprovedCases'
import ClosedCases from './admin/ClosedCases'
import MyCases from './admin/MyCases'
import Reports from './admin/Reports'
import Settings from './admin/Settings'
import PrivateRoute from './admin/PrivateRoute'
import './styles/global.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes>
        <Route path="/app" element={<LandingView />} />
        <Route path="/app/chat" element={<ChatView />} />
        <Route path="/app/status/:caseId" element={<StatusView />} />

        <Route path="/admin/login" element={<Login />} />
        <Route path="/admin" element={<PrivateRoute><Queue /></PrivateRoute>} />
        <Route path="/admin/approved" element={<PrivateRoute><ApprovedCases /></PrivateRoute>} />
        <Route path="/admin/closed" element={<PrivateRoute><ClosedCases /></PrivateRoute>} />
        <Route path="/admin/my-cases" element={<PrivateRoute><MyCases /></PrivateRoute>} />
        <Route path="/admin/reports" element={<PrivateRoute><Reports /></PrivateRoute>} />
        <Route path="/admin/settings" element={<PrivateRoute><Settings /></PrivateRoute>} />
        <Route path="/admin/data" element={<PrivateRoute><DataExplorer /></PrivateRoute>} />
        <Route path="/admin/cases/:caseId" element={<PrivateRoute><CaseDetail /></PrivateRoute>} />

        <Route path="/" element={<Navigate to="/app" replace />} />
        <Route path="*" element={<Navigate to="/app" replace />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
)
