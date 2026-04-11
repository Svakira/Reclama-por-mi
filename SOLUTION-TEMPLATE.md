# JusticIA — Reference Document
**Semillero LegalTech — Universidad ICESI**
**Simulacro Hack the Law Cambridge 2026**

---

## Challenge

**"El derecho que no llega"** — Access to Justice / Consumer Protection Track

The SIC receives 400,000+ consumer complaints/year. 70% of Colombians have no access to legal advice. The SIC complaint form has 14 technical fields. Users who cannot distinguish *garantía legal* from *garantía contractual* make errors that render their claim inadmissible.

**The gap is not legal. It is linguistic and informational.**

---

## Solution: JusticIA

An adaptive agentic pipeline that converts Rosa's voice into a formally valid SIC consumer complaint — with a lawyer always in the loop.

**Tagline:** *"El derecho que no llega, ahora llega."*

### Users

| User | Profile | Need |
|---|---|---|
| **Rosa** (54) | Informal street vendor, Cali. Defective phone, store refuses to replace. No legal knowledge. | Understand her rights. Get a ready-to-file complaint. |
| **Lawyer** (Clínica Jurídica ICESI) | Law student handling 20 cases/week. | Pre-screened cases, AI draft, hard-gate approval flow. |

---

## Architecture

### Services Map

```
┌─────────────────────────────────────────────────────────────────┐
│                        REPLIT (paid)                            │
│                                                                 │
│  FastAPI (Python)          React SPA (built, served by FastAPI) │
│  ├── /api/*  (backend)     ├── /app    (Rosa — public)          │
│  └── /static (frontend)   └── /admin  (Lawyer — JWT protected) │
│                                                                 │
│  Process:                                                       │
│  ├── Pipeline agents (Groq API calls)                           │
│  ├── pdfplumber + PyMuPDF (PDF extraction)                      │
│  ├── Tesseract + OpenCV (image/scan OCR)                        │
│  └── PDF generator (reportlab)                                  │
└───────────────────────┬─────────────────────────────────────────┘
                        │ HTTPS
        ┌───────────────┼───────────────────────┐
        │               │                       │
        ▼               ▼                       ▼
┌──────────────┐  ┌──────────────┐  ┌─────────────────────┐
│  GROQ API    │  │ NEO4J AURA   │  │  TWILIO WHATSAPP     │
│  (free tier) │  │ (free tier)  │  │  (Sandbox — free)   │
│              │  │              │  │                     │
│  llama-3.3-  │  │  Knowledge   │  │  Notifications to   │
│  70b-        │  │  Graph:      │  │  Rosa (case ready,  │
│  versatile   │  │  Law 1480    │  │  reference number,  │
│              │  │  articles,   │  │  filing reminder)   │
│  whisper-    │  │  case        │  │                     │
│  large-v3    │  │  patterns,   │  │  Used for: Stage 8  │
│              │  │  SIC         │  │  confirmation and   │
│  30 RPM      │  │  templates   │  │  Stage 10 delivery  │
│  100K TPD    │  │              │  │                     │
└──────────────┘  └──────────────┘  └─────────────────────┘
                        │
                        ▼
              ┌──────────────────┐
              │  FIRESTORE       │
              │  (Google — free  │
              │   50K reads/day  │
              │   20K writes/day)│
              │                  │
              │  Case state,     │
              │  audit logs,     │
              │  user sessions   │
              └──────────────────┘
```

### Data Flow (one case, happy path)

```
Rosa speaks / types
      │
      ▼ (voice → Groq Whisper)
IntakeInterviewer (Groq LLaMA)
  → decision tree A/B/C
  → collects minimum variables
      │
      ▼
DocumentRequestPlanner (Groq LLaMA)
  → requests specific doc with reason
      │
Rosa uploads photo/PDF
      │
      ▼
DocumentParser (pdfplumber / Tesseract)
  → structured fact sheet
  → confidence score per field
  → if overall < 0.70 → BLOCKED → lawyer queue
      │
      ▼
EvidenceCrossValidator (Groq LLaMA)
  → narrative vs. document comparison
  → flags discrepancies → asks Rosa to confirm
      │
      ▼
LegalClassifier (Groq LLaMA + Neo4j KG)
  → scenario routing (A / B / C)
  → Superfinanciera bifurcation (B)
  → PQR check (C)
  → claim_valid = true | false
      │
      ├── false → DeadEndNavigator → Stage 5b (Lawyer hard gate)
      │                              ↓
      │                         PENDING_CLAIM_DECISION
      │                         lawyer: CONFIRM or OVERRIDE
      │                              ↓ (confirm)
      │                         RejectionDocGenerator → Stage 5c
      │
      ▼ (claim_valid = true)
ComplaintDraftGenerator (Groq LLaMA + KG templates)
  → OUTPUT A: plain Spanish for Rosa (~200 words)
  → OUTPUT B: formal SIC draft (14 fields)
      │
      ▼
DraftValidator (deterministic Python)
  → every cited article must exist in KG
  → all 14 SIC fields filled
      │
      ▼
CasePackager (deterministic)
  → assembles packet → Firestore
  → priority score
  → Rosa notified (WhatsApp)
      │
      ▼ (lawyer dashboard)
Lawyer reviews in /admin
  → sees: summary, flags, docs, classification, draft
  → actions: APPROVE / EDIT / REQUEST DOCS / ESCALATE / NO CLAIM
      │
      ▼ (lawyer approves)
FilingOptionsGate → 3 options presented to Rosa:
  1. Clinic files on her behalf (requires rosa_document_consent)
  2. Rosa files herself (PDF + guide delivered)
  3. Discard → RejectionDocGenerator
      │
      ▼ (Option 1 + consent)
SICSubmitter
  → Strategy A: REST API (if available)
  → Strategy B: Playwright browser automation
  → Strategy C: email to quejas@sic.gov.co
```

---

## Stack

| Layer | Technology | Cost | Notes |
|---|---|---|---|
| **Hosting** | Replit Core | $20/mo (paid) | FastAPI + React in one Repl |
| **LLM** | Groq `llama-3.3-70b-versatile` | Free | 30 RPM, 100K TPD |
| **Voice** | Groq `whisper-large-v3` | Free | 7,200 audio sec/hour |
| **Knowledge Graph** | Neo4j AuraDB Free | Free | Sufficient for ~100 nodes |
| **KG Indexing** | LlamaIndex (library) | Free | No hosted cost |
| **PDF extraction** | pdfplumber + PyMuPDF | Free | Python libraries |
| **Image OCR** | Tesseract + OpenCV | Free | Python libraries |
| **Case state** | Firestore (Google) | Free tier | 50K reads / 20K writes / day |
| **Auth** | JWT HS256 (local) | Free | No external auth service |
| **Notifications** | Twilio WhatsApp Sandbox | Free | ~1,000 messages/month |
| **PDF generation** | reportlab | Free | Python library |
| **Frontend** | React + Vite | Free | Built to static, served by FastAPI |

**Total external cost: $0** (beyond Replit Core which you already have)

---

## Hard Gates (cannot be bypassed)

1. **LawyerApprovalGate** — no draft reaches Rosa without lawyer approval
2. **rosa_document_consent** — Option 1 (clinic files) requires Rosa's explicit click-through on the exact PDF
3. **PENDING_CLAIM_DECISION** — NO CLAIM cases cannot be communicated to Rosa until lawyer explicitly confirms or overrides
4. **Illegibility gate** — documents with confidence < 0.70 block the pipeline until lawyer manually verifies

---

## Scope Boundaries

**In scope:**
- Cases A (defective product), B (unauthorized financial charge — non-Superfinanciera), C (telecom breach — with prior PQR)
- Voice + text + file upload for Rosa
- Lawyer dashboard with queue, case detail, AI assistant, hard-gate actions
- WhatsApp notifications (Twilio Sandbox)
- SIC submission (Strategy C — email, for demo)
- Rejection document generation

**Out of scope (demo):**
- SIC Strategy A (REST API) — not publicly available
- SIC Strategy B (Playwright) — blocked by CAPTCHA in production
- Real Twilio production (Sandbox only)
- Superfinanciera redirect workflow (classified correctly, redirect message only)
- Multi-lawyer accounts / role management beyond basic JWT
- Mobile app (PWA only)

---

## Repository

`https://github.com/Svakira/xd.git`

*Make private after initial push to protect before the hackathon.*

---

*JusticIA — Semillero LegalTech ICESI — Version 2026-04-11*
