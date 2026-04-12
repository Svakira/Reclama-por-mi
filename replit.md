# JusticIA - AI-Powered Legal Intake Platform

## Overview
JusticIA is an AI-powered legal intake and complaint preparation platform for low-income consumers in Colombia, targeting SIC (Superintendencia de Industria y Comercio) complaints. Handles defective products (Scenario A), unauthorized charges (Scenario B), and telecom breaches (Scenario C).

## Architecture
- **Backend**: FastAPI (Python) on port 5000, serves built React frontend
- **Frontend**: React + Vite (TypeScript), built to `frontend/dist/`
- **LLM**: Groq API (llama-3.3-70b-versatile primary, llama-3.1-8b-instant fallback)
- **Knowledge Graph**: `backend/kg/legal_graph.json` — legal articles, claim templates, scenario definitions
- **Workflow**: Single `Start application` workflow runs uvicorn

## Complete Pipeline Flow
1. **Intake Interview** (`intake_interviewer.py`): Chat agent uses KG to guide conversation, collects user narrative, classifies scenario (A/B/C), tracks documents needed per scenario
2. **Document Upload** (`pipeline_routes.py /upload`): Parses documents, infers doc type from content/fields, tracks what's still needed per scenario
3. **Finalize** (`pipeline_routes.py /finalize`): Runs full pipeline — cross-validation, legal classification, formal draft, simple explanation, draft validation, case packaging
4. **WhatsApp Opt-in** (stage WHATSAPP_OPTIN): After case creation, asks user if they want WhatsApp updates
5. **Notification** (`notify_routes.py`): WhatsApp via Twilio (mock mode if no credentials)

## Session Stages
- INTAKE → DOCS_NEEDED → (finalize) → WHATSAPP_OPTIN → COMPLETE
- SUPERFINANCIERA_REDIRECT (redirected, not SIC competence)
- NO_CLAIM_DETECTED (pending lawyer review)
- ILLEGIBLE_BLOCKED (document quality too low)

## Required Documents by Scenario
- **A** (Defective Product): factura, evidencia_defecto
- **B** (Unauthorized Charge): extracto_bancario, soporte_cobro
- **C** (Telecom Breach): factura_servicio, radicado_pqr

## Key API Endpoints
- `POST /api/pipeline/start` — Start intake session
- `POST /api/pipeline/message` — Send message (handles all stages including WhatsApp opt-in)
- `POST /api/pipeline/upload` — Upload document (parse only)
- `POST /api/pipeline/finalize` — Run full pipeline after docs collected
- `POST /api/pipeline/transcribe` — Transcribe audio

## KG Integration
- **IntakeInterviewer**: Loads KG to build system prompt with document requirements per scenario, PQR requirements for telecom, rejection templates
- **LegalClassifier**: Uses KG articles per scenario for classification prompt
- **ComplaintDraftGenerator**: Uses KG claim templates and article texts for formal draft
- **DraftValidator**: Validates against KG-verified article IDs

## Environment Variables
- `GROQ_API_KEY` — Required for LLM calls
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM` — Optional for WhatsApp
- `DEBUG_VERBOSE` — Enable verbose logging

## Document Parsing
- **Images** (PNG/JPG): Groq Vision model primary (llama-4-scout), Tesseract OCR fallback
- **PDFs**: pdfplumber primary, PyMuPDF fallback, then render-as-image for scanned PDFs
- **Structured extraction**: LLM parses raw text into JSON fields (fecha, monto, cedula, etc.)
- **Confidence gate**: Documents with score < 0.70 are blocked (illegible)

## Admin Panel
- **Login**: `/admin/login` (demo: abogado@icesi.edu.co / icesi2026)
- **Queue**: `/admin` — Stats grid + filterable case table with status badges
- **Case Detail**: `/admin/cases/:id` — Tabbed view (draft, transcript, documents, analysis)
- **Design**: Dark sidebar (0F1419), warm neutrals, Plus Jakarta Sans font

## Key Files
- `backend/main.py` — FastAPI app with SPA catch-all routing
- `backend/api/pipeline_routes.py` — Main pipeline API
- `backend/agents/intake_interviewer.py` — KG-aware chat agent (ONLY collects info, no legal opinions)
- `backend/agents/document_parser.py` — OCR + Vision model document parsing
- `backend/agents/groq_client.py` — Groq client with retry/backoff
- `backend/agents/complaint_draft_generator.py` — Formal draft + simple explanation
- `backend/agents/legal_classifier.py` — KG-powered legal classification
- `backend/agents/draft_validator.py` — Deterministic draft validation
- `backend/agents/case_packager.py` — Case assembly + Firestore save
- `backend/api/notify_routes.py` — WhatsApp/Twilio notifications
- `backend/api/cases_routes.py` — Admin case management API
- `backend/kg/legal_graph.json` — Knowledge graph (articles, templates, scenarios)
- `frontend/src/app/ChatView.tsx` — Main chat UI
- `frontend/src/admin/Queue.tsx` — Admin queue with stats grid
- `frontend/src/admin/CaseDetail.tsx` — Case detail view
- `frontend/src/components/Sidebar.tsx` — Dark sidebar navigation
- `frontend/src/styles/tokens.ts` — Design tokens (colors, typography, shadows)
