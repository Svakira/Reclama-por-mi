# JusticIA — Consumer Rights Pipeline for Low-Income Colombians

**Hack the Law — Simulacro Cambridge 2026**
Semillero LegalTech · Universidad ICESI

---

## What this is

JusticIA is an AI-powered legal intake and complaint preparation engine for Colombian consumers who cannot afford a lawyer. It guides a user ("Rosa") through a structured interview in plain Colombian Spanish, parses uploaded documents, cross-validates evidence, classifies the claim under Law 1480/2011, and generates a formal complaint draft ready to file with the SIC (Superintendencia de Industria y Comercio).

Simultaneously, a second interface — the **Lawyer Command Center** — receives a fully pre-processed case packet in a prioritized queue so a supervising attorney from the legal clinic can review, edit, and approve the draft before delivery. The AI works as a member of the lawyer's team, not just a tool for the end user.

> The system does not file anything autonomously. Lawyer approval is mandatory before any document reaches Rosa.

---

## Challenge context

**"El derecho que no llega"** — Build an LLM assistant that guides low-income Colombian consumers through the SIC complaint process.

Required outputs per case:
1. Legal diagnosis (right to file + applicable law)
2. Step-by-step SIC procedure guide
3. Formal complaint draft with correct legal language (all 14 SIC form fields)

Three case types: (A) defective product, (B) unauthorized financial charge, (C) telecom service breach.

---

## Architecture overview

```
┌─────────────────────────────────────────────────┐
│              ROSA-FACING LAYER                  │
│  PWA Chat (React) — text, voice, file upload    │
└──────────────────────┬──────────────────────────┘
                       │ HTTPS / WebSocket
┌──────────────────────▼──────────────────────────┐
│           ORCHESTRATION LAYER                   │
│   LangChain multi-agent pipeline                │
│   (Google Cloud Run — containerized)            │
│                                                 │
│  1. IntakeInterviewer                           │
│  2. DocumentRequestPlanner                      │
│  3. DocumentParser                              │
│  4. EvidenceCrossValidator                      │
│  5. LegalClassifier          ──── RAG/KG ───►  │
│  6. ComplaintDraftGenerator  ──── RAG/KG ───►  │
│  7. DraftValidator (deterministic)              │
│  8. DeadEndNavigator                            │
│  9. CasePackager (deterministic)                │
└──────────┬──────────────────────────────────────┘
           │                   │
┌──────────▼──────┐   ┌────────▼─────────────────┐
│  RAG / KG       │   │  External services        │
│  Neo4j + Llama  │   │  vLex · RUES · Whisper    │
│  Index          │   │  Cloud Storage · Firestore│
└─────────────────┘   └───────────────────────────┘
           │
┌──────────▼──────────────────────────────────────┐
│          LAWYER COMMAND CENTER                  │
│  Separate React dashboard                       │
│  Queue · AI assistant · Audit log · Actions     │
└─────────────────────────────────────────────────┘
```

---

## Agent pipeline

| # | Agent | Tool | Role |
|---|---|---|---|
| 0 | `IntakeInterviewer` | Claude API (claude-3-5-sonnet) | Progressive-disclosure interview in plain Colombian Spanish |
| 1 | _(RAG step)_ | LlamaIndex + Neo4j | Semantic search → case pattern match → retrieve articles + SIC template |
| 2 | `DocumentRequestPlanner` | Claude API | Infers which document to request based on the matched case pattern |
| 3 | `DocumentParser` | pdfplumber + PyMuPDF + Claude Vision | Extracts structured fields from PDFs and photos |
| 4 | `EvidenceCrossValidator` | Claude API | Compares narrative facts vs. extracted document fields; flags discrepancies |
| 5 | `LegalClassifier` | Claude API + RAG context | Evaluates legal conditions using only retrieved articles; outputs `claim_valid` |
| 5b | `DeadEndNavigator` | Claude API | If `claim_valid = false`: plain-language explanation + alternatives |
| 6 | `ComplaintDraftGenerator` | Claude API + RAG context | Fills all 14 SIC form fields using KG templates + validated facts |
| 7 | `DraftValidator` | Python (deterministic) | Checks every cited article against `knowledge_graph.valid_article_ids` |
| 8 | `CasePackager` | Python (deterministic) | Assembles case packet + calculates priority score + pushes to queue |

---

## Knowledge graph structure

The RAG layer is backed by a Neo4j graph with four layers:

| Layer | Node type | Content |
|---|---|---|
| 1 | `Article` | Full text + plain summary + conditions + remedies for Law 1480/2011 articles |
| 2 | `CasePattern` | Repeating complaint structures (A/B/C): required docs, applicable articles, typical pretensions |
| 3 | `SICFormTemplate` | Official SIC form templates with all 14 required fields and required legal language |
| 4 | `DocumentSchema` | Extraction targets and confidence thresholds per document type |

Edges connect `CasePattern → GROUNDED_IN → Article`, `CasePattern → USES_TEMPLATE → SICFormTemplate`, and `CasePattern → REQUIRES_DOC → DocumentType`.

LlamaIndex indexes the graph for semantic retrieval. The `LegalClassifier` and `ComplaintDraftGenerator` agents operate exclusively on retrieved context — they are not permitted to cite any article not present in the retrieval result.

---

## Tech stack

| Layer | Technology |
|---|---|
| Rosa frontend | React PWA (Lovable) |
| Lawyer frontend | React dashboard |
| Backend orchestration | LangChain, Python, Google Cloud Run |
| Primary LLM | Claude API (claude-3-5-sonnet) |
| Voice transcription | Whisper API via Groq |
| PDF extraction | pdfplumber + PyMuPDF |
| Image/photo extraction | Claude API (Vision) |
| Knowledge graph | Neo4j Aura |
| RAG indexing/retrieval | LlamaIndex |
| Seller verification | RUES API |
| Legal articles | vLex API |
| State + queue | Cloud Tasks + Firestore |
| File storage | Google Cloud Storage |

---

## Setup

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker + Docker Compose
- A Google Cloud project with Cloud Run, Cloud Tasks, Firestore, and Cloud Storage enabled
- API keys for: Claude (Anthropic), Groq, vLex, RUES
- Neo4j Aura instance (free tier is sufficient for the demo)

### Local development

```bash
# Clone the repo
git clone https://github.com/semillero-legaltech-icesi/justicia.git
cd justicia

# Copy environment file and fill in your keys
cp .env.example .env

# Start the full stack locally
docker-compose up --build
```

The backend will be available at `http://localhost:8000`.
Rosa's frontend: `http://localhost:3000`.
Lawyer Command Center: `http://localhost:3001`.

### Environment variables

```
ANTHROPIC_API_KEY=           # Claude API
GROQ_API_KEY=                # Whisper via Groq
VLEX_API_KEY=                # Legal article search
RUES_API_KEY=                # Seller NIT verification
NEO4J_URI=                   # Neo4j Aura connection URI
NEO4J_USER=
NEO4J_PASSWORD=
GCP_PROJECT_ID=
GCP_BUCKET_NAME=
FIRESTORE_COLLECTION=cases
```

### Seed the knowledge graph

```bash
python scripts/seed_knowledge_graph.py
```

This loads:
- 47 Law 1480/2011 articles (most relevant to consumer complaints)
- 3 SIC form templates (one per case type A/B/C)
- 3 case patterns (A/B/C) with full document requirements and applicable articles
- 5 document extraction schemas (invoice, bank statement, service contract, telecom invoice, denial letter)
- Sample legal language for all 14 SIC form fields across all 3 case types

### Run tests

```bash
pytest tests/ -v
```

---

## Running the demo

### Sample cases

Three sample PDFs are included in `demo/sample_documents/`:

| File | Case type | Description |
|---|---|---|
| `factura_techstore_cali.pdf` | A — Defective product | Electronic invoice, Samsung Galaxy A15, TechStore Cali S.A.S. |
| `estado_cuenta_cobro_indebido.pdf` | B — Unauthorized charge | Bank statement showing an unauthorized recurring charge |
| `factura_telecom_internet.pdf` | C — Telecom breach | Telecom invoice for an internet plan not delivered at contracted speed |

### Running a case end-to-end

1. Open `http://localhost:3000` (Rosa's interface)
2. Type or speak a complaint in Spanish
3. Upload the relevant sample document when prompted
4. Observe the pipeline process the case
5. Open `http://localhost:3001` (Lawyer Command Center)
6. Review the case packet, validation flags, and draft
7. Approve the draft — the final PDF is delivered to Rosa's interface

Total pipeline processing time (excluding user wait): ~28 seconds.

---

## Pipeline audit log

Every case generates a full audit log stored in Firestore and viewable in the Lawyer Command Center. For each pipeline stage the log records:

- Timestamp
- Agent name
- Input type
- Tool used
- Output summary
- Confidence scores
- Any flags raised

The `DraftValidator` records which articles were verified against the knowledge graph and confirms that zero hallucinated citations are present in the final draft. The jury can query the audit log for any case to verify the legal decision path.

---

## Handling the "no valid claim" case

When `LegalClassifier` returns `claim_valid = false` (e.g., private sale between individuals — no commercial relationship, so Law 1480 does not apply), the `DeadEndNavigator` agent:

1. Explains in plain language why the law does not apply to this specific situation
2. Provides three alternatives with cost and accessibility information:
   - Defensoría del Consumidor (free)
   - Mediation / conciliation (low cost)
   - Small claims civil procedure
3. Still routes the case to the lawyer queue so the lawyer can override the classification if warranted

The system never invents a legal right that does not exist. The `DeadEndNavigator` path is not a failure mode — it is explicit, honest behavior, and it is auditable.

---

## Lawyer Command Center

The Command Center is a functional case management interface, not a demo screen. Key features:

- **Prioritized queue**: cases ranked by deadline urgency × critical flag count
- **Per-case view**: AI summary, validation flags (severity-graded), parsed documents, legal classification with confidence scores, draft validation report
- **AI legal assistant**: the lawyer can ask questions about the case in natural language; the assistant queries the KG + vLex and answers with cited sources
- **Batch approval mode**: for straightforward cases with no flags
- **Full pipeline audit log**: expandable, exportable as PDF
- **Action buttons**: approve, edit draft, request more documents from Rosa, escalate, mark no claim, add legal note

---

## Key design decisions

**Why a knowledge graph instead of plain prompting?**

Without a KG, the LLM generates legal content from parametric memory. This risks citing articles that do not exist, citing the wrong version of an amended law, or using non-compliant language in SIC form fields. The KG stores verified, structured legal content. The LLM is used as a language renderer to fill templates — legal reasoning stays in the graph.

**Why a deterministic `DraftValidator`?**

A prompt instruction ("do not cite articles not in Colombian law") is a soft constraint. The `DraftValidator` is a hard constraint: it iterates over every article citation in the generated draft and checks it against the set of valid article IDs in the KG. Any citation that is not verified is stripped and flagged before the draft reaches the lawyer. This is the architectural answer to hallucination risk in a legal document.

**Why the `EvidenceCrossValidator` as a separate stage?**

If document-extracted facts are passed directly to the draft generator, undetected discrepancies (e.g., user says "last month" but invoice shows five months ago) can corrupt the complaint or delay SIC processing. The `EvidenceCrossValidator` catches these before drafting and resolves them with a targeted question to Rosa.

**Why does the system request documents one at a time?**

Asking Rosa to upload "all your documents" creates a barrier for low-literacy users who may not know what documents are relevant. The `DocumentRequestPlanner` retrieves the required document list from the matched `CasePattern` node and requests documents in legal-importance order, with a plain-language explanation of why each document is needed.

**Automatic SIC submission — why a three-strategy waterfall?**

The SIC does not expose a stable public REST API. Rather than building a brittle single-path integration, `SICSubmitter` tries three channels in order:

1. **Strategy A — Direct API:** If the SIC's institutional partner API (`api.sic.gov.co/v1`) is available and credentials are configured, submit via authenticated REST POST. Fastest, returns radicado immediately.

2. **Strategy B — Browser automation (Playwright):** If the API is unavailable, drive a headless Chromium session through the SIC web portal. CAPTCHA is solved via the 2captcha service. Returns radicado from the confirmation page.

3. **Strategy C — Email to `quejas@sic.gov.co`:** If the portal is also down, send a structured email with the complaint PDF attached. This is a SIC-accepted accessibility channel (Circular Única §3.2.4). The radicado arrives by reply within 3 business days.

If all three fail, Rosa receives the PDF + the manual filing guide. The system never silently drops a case.

**Lawyer approval is a hard gate, not a soft check.** `LawyerApprovalGate.assert_approved()` raises `SubmissionBlockedError` if the case has not been explicitly approved. This is enforced in code — not in policy documentation.

---

## Project structure

```
justicia/
├── backend/
│   ├── agents/
│   │   ├── intake_interviewer.py
│   │   ├── document_request_planner.py
│   │   ├── document_parser.py
│   │   ├── evidence_cross_validator.py
│   │   ├── legal_classifier.py
│   │   ├── complaint_draft_generator.py
│   │   ├── draft_validator.py
│   │   ├── dead_end_navigator.py
│   │   └── case_packager.py
│   ├── kg/
│   │   ├── neo4j_client.py
│   │   ├── llamaindex_retriever.py
│   │   └── schemas/
│   │       ├── article.py
│   │       ├── case_pattern.py
│   │       ├── sic_form_template.py
│   │       └── document_schema.py
│   ├── api/
│   │   ├── rosa_routes.py
│   │   └── lawyer_routes.py
│   ├── queue/
│   │   ├── cloud_tasks.py
│   │   └── priority_scorer.py
│   └── external/
│       ├── rues_client.py
│       ├── vlex_client.py
│       ├── whisper_client.py
│       └── sic_submitter.py        # Automatic SIC submission (3-strategy waterfall)
├── frontend-rosa/          # React PWA
├── frontend-lawyer/        # React dashboard (Command Center)
├── scripts/
│   └── seed_knowledge_graph.py
├── demo/
│   └── sample_documents/
├── docs/
│   ├── SIC_formulario-base-reclamacion.pdf
│   ├── SIC_manual-proceso-reclamacion.pdf
│   ├── Ley-1480-2011_Estatuto-del-Consumidor.pdf
│   ├── Ramirez-Sierra_Responsabilidad-productos-defectuosos-Estatuto-Consumidor.pdf
│   └── Tamayo-Jaramillo_Estatuto-Consumidor-responsabilidad-productos-defectuosos.pdf
├── tests/
├── docker-compose.yml
├── Dockerfile
└── .env.example
```

---

## Legal reference documents

All source documents are in `docs/`. They are used to seed the knowledge graph and as ground-truth references for the RAG layer.

| File | Type | Role in the system |
|---|---|---|
| `docs/SIC_formulario-base-reclamacion.pdf` | Official SIC form | The template the system fills. Its 14 fields are encoded as `SICFormTemplate` nodes in the knowledge graph. The `ComplaintDraftGenerator` agent fills this form using validated facts. |
| `docs/SIC_manual-proceso-reclamacion.pdf` | Official SIC guide | Step-by-step procedure for filing a complaint. Used to generate the procedural guide delivered to Rosa at Stage 10, including office addresses, online portal link, and required attachments. |
| `docs/Ley-1480-2011_Estatuto-del-Consumidor.pdf` | Law 1480/2011 | Primary legal corpus. Articles are parsed and loaded as `Article` nodes in the knowledge graph. The `LegalClassifier` and `ComplaintDraftGenerator` agents retrieve from this corpus — they do not cite anything that is not in it. |
| `docs/Ramirez-Sierra_Responsabilidad-productos-defectuosos-Estatuto-Consumidor.pdf` | Academic chapter | "La responsabilidad por productos defectuosos en el nuevo Estatuto del Consumidor" — Diego Fernando Ramírez Sierra. Provides doctrinal interpretation of Law 1480 for edge cases and warranty analysis. Used to annotate `Article` nodes with doctrinal commentary. |
| `docs/Tamayo-Jaramillo_Estatuto-Consumidor-responsabilidad-productos-defectuosos.pdf` | Academic chapter | "Estatuto del Consumidor y la responsabilidad por productos defectuosos" — Javier Tamayo Jaramillo. Second doctrinal reference; used alongside Ramírez Sierra to cross-validate legal interpretations in the knowledge graph. |

> **Note on document provenance:** These are official SIC documents and academic publications. They are included in this repository strictly for research and educational purposes in the context of the Hack the Law hackathon. They are not redistributed for commercial use.

---

## Documentation

| File | Contents |
|---|---|
| `SOLUTION-TEMPLATE.md` | Full three-proposal analysis, comparative summary, and reusable challenge template |
| `PROPOSAL-1-DEEP-SPEC.md` | Complete technical specification for this implementation: RAG/KG design, all pipeline stages, document flow edge cases, end-to-end example, compliance check |

---

## Team

Semillero LegalTech — Universidad ICESI
Hack the Law · Simulacro Cambridge 2026
