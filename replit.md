# JusticIA - AI-Powered Legal Intake Platform

## Overview
JusticIA is an AI-powered legal intake and complaint preparation platform for low-income consumers in Colombia, targeting SIC (Superintendencia de Industria y Comercio) complaints. Handles defective products (Scenario A), unauthorized charges (Scenario B), and telecom breaches (Scenario C).

## Architecture
- **Backend**: FastAPI (Python) on port 5000, serves built React frontend
- **Frontend**: React + Vite (TypeScript), built to `frontend/dist/`
- **LLM**: Groq API (llama-3.3-70b-versatile primary, llama-3.1-8b-instant fallback)
- **Vision**: Groq Vision (llama-4-scout primary, llama-3.2-11b-vision fallback) for image classification
- **Knowledge Graph**: `backend/kg/legal_graph.json` — legal articles, claim templates, scenario definitions
- **Workflow**: Single `Start application` workflow runs uvicorn

## Complete Pipeline Flow
1. **Intake Interview** (`intake_interviewer.py`): Chat agent uses KG to guide conversation, collects user narrative, classifies scenario (A/B/C), tracks documents needed per scenario
2. **Document Upload** (`pipeline_routes.py /upload`): Multimodal — classifies images first (evidence photo vs text document), then processes accordingly
3. **Finalize** (`pipeline_routes.py /finalize`): Runs full pipeline — cross-validation, legal classification, formal draft, simple explanation, draft validation, case packaging
4. **WhatsApp Opt-in** (stage WHATSAPP_OPTIN): After case creation, asks user if they want WhatsApp updates
5. **Notification** (`notify_routes.py`): WhatsApp via Twilio

## Session Stages
- INTAKE → DOCS_NEEDED → (finalize) → WHATSAPP_OPTIN → COMPLETE

## Case ID Format
- Sequential: JUS-YYYY-NNN (e.g., JUS-2026-001, JUS-2026-002)
- Counter stored in Firestore/memory `counters` collection

## Required Documents by Scenario
- **A** (Defective Product): factura, evidencia_defecto
- **B** (Unauthorized Charge): extracto_bancario, soporte_cobro
- **C** (Telecom Breach): factura_servicio, radicado_pqr

## Document Parsing (Multimodal)
- **Image classification**: Vision model classifies images as evidence photos vs text documents
  - Evidence photos: described and accepted directly (high confidence, no OCR)
  - Text documents: OCR/vision text extraction + structured field extraction
- **Images**: Groq Vision model primary (llama-4-scout), Tesseract OCR fallback
- **PDFs**: pdfplumber primary, PyMuPDF fallback, then render-as-image for scanned PDFs
- **Low confidence docs**: Flagged `needs_review=True` (never blocked), accepted and shown to lawyer

## PDF Generation
- Uses reportlab for formal SIC complaint PDF
- Includes document evidence table (RELACIÓN DE PRUEBAS DOCUMENTALES ADJUNTAS)
- Lists all uploaded documents with types, filenames, and evidence descriptions

## Key API Endpoints
- `POST /api/pipeline/start` — Start intake session
- `POST /api/pipeline/message` — Send message (handles all stages including WhatsApp opt-in)
- `POST /api/pipeline/upload` — Upload document (parse only)
- `POST /api/pipeline/finalize` — Run full pipeline after docs collected
- `POST /api/pipeline/transcribe` — Transcribe audio

## Admin Panel
- **Login**: `/admin/login` (demo: abogado@icesi.edu.co / icesi2026)
- **Queue**: `/admin` — Stats grid + filterable case table with status badges
- **Approved**: `/admin/approved` — Cases with APPROVED/SUBMITTED_TO_SIC status
- **Closed**: `/admin/closed` — Cases with CLOSED status
- **My Cases**: `/admin/my-cases` — Cases assigned to logged-in lawyer
- **Reports**: `/admin/reports` — Stats dashboard (totals, by type, approval rate)
- **Settings**: `/admin/settings` — Profile info, Twilio status, system info
- **Case Detail**: `/admin/cases/:id` — Tabbed view (draft, transcript, documents, analysis)
- **Design**: Dark sidebar (0F1419), warm neutrals, Plus Jakarta Sans font

## Environment Variables
- `GROQ_API_KEY` — Required for LLM calls
- `TWILIO_ACCOUNT_SID` — Twilio account ID
- `TWILIO_AUTH_TOKEN` — Twilio auth token (secret)
- `TWILIO_WHATSAPP_FROM` — WhatsApp sender number (default: whatsapp:+14155238886)
- `DEBUG_VERBOSE` — Enable verbose logging

## Key Files
- `backend/main.py` — FastAPI app with SPA catch-all routing
- `backend/api/pipeline_routes.py` — Main pipeline API
- `backend/agents/intake_interviewer.py` — KG-aware chat agent (ONLY collects info, no legal opinions)
- `backend/agents/document_parser.py` — Multimodal document parsing (vision classify + OCR/extract)
- `backend/agents/groq_client.py` — Groq client with retry/backoff
- `backend/agents/complaint_draft_generator.py` — Formal draft + simple explanation
- `backend/agents/legal_classifier.py` — KG-powered legal classification
- `backend/agents/draft_validator.py` — Deterministic draft validation
- `backend/agents/case_packager.py` — Case assembly + Firestore save (sequential IDs)
- `backend/external/pdf_generator.py` — SIC complaint PDF with document evidence table
- `backend/api/notify_routes.py` — WhatsApp/Twilio notifications
- `backend/api/cases_routes.py` — Admin case management API
- `backend/db/firestore_client.py` — Firestore/in-memory DB with sequential case counter
- `backend/kg/legal_graph.json` — Knowledge graph (articles, templates, scenarios)
- `frontend/src/app/ChatView.tsx` — Main chat UI
- `frontend/src/admin/Queue.tsx` — Admin queue with stats grid
- `frontend/src/admin/CaseDetail.tsx` — Case detail view
- `frontend/src/admin/ApprovedCases.tsx` — Approved cases list
- `frontend/src/admin/ClosedCases.tsx` — Closed/rejected cases list
- `frontend/src/admin/MyCases.tsx` — Lawyer's assigned cases
- `frontend/src/admin/Reports.tsx` — Stats dashboard
- `frontend/src/admin/Settings.tsx` — System configuration view
- `frontend/src/components/Sidebar.tsx` — Dark sidebar navigation (all options enabled)
- `frontend/src/styles/tokens.ts` — Design tokens (colors, typography, shadows)
