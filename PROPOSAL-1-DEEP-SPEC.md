# PROPOSAL 1 — DEEP SPECIFICATION
## Adaptive Interview + Document Orchestration Pipeline with RAG/Knowledge Graph and Lawyer Command Center

**SEMILLERO LEGALTECH — UNIVERSIDAD ICESI**
**Simulacro Hack the Law Cambridge 2026**

> This document is the full technical and strategic specification for Proposal 1.
> It supersedes and expands the Proposal 1 section in SOLUTION-TEMPLATE.md.

---

## TABLE OF CONTENTS

1. [Core Concept](#1-core-concept)
2. [RAG + Knowledge Graph Layer](#2-rag--knowledge-graph-layer)
3. [Full Stack — Component Map](#3-full-stack--component-map)
4. [AI Tool per Pipeline Stage](#4-ai-tool-per-pipeline-stage)
5. [Full AI Pipeline — All Stages](#5-full-ai-pipeline--all-stages)
6. [Document Processing Flow](#6-document-processing-flow)
7. [Lawyer Command Center Backend](#7-lawyer-command-center-backend)
8. [End-to-End Example: Rosa's Case from First Message to SIC Delivery](#8-end-to-end-example-rosas-case-from-first-message-to-sic-delivery)
9. [Weaknesses and Risks](#9-weaknesses-and-risks)
10. [Copiability Analysis — What Other Teams Will Likely Do](#10-copiability-analysis--what-other-teams-will-likely-do)
11. [Differentiators — What Makes This Architecture Distinctively Hard to Copy](#11-differentiators--what-makes-this-architecture-distinctively-hard-to-copy)
12. [Challenge Requirements Compliance Check](#12-challenge-requirements-compliance-check)

---

## 1. Core Concept

The system is not a chatbot. It is an **AI-powered legal intake and preparation engine** that works simultaneously on two fronts:

- **Front 1 (Rosa-facing):** A guided conversational interface that interviews Rosa in plain Colombian Spanish, dynamically determines which documents are needed, parses those documents, cross-validates the evidence, and produces both a plain-language explanation and a SIC-ready formal complaint.

- **Front 2 (Lawyer-facing):** A Command Center where the supervising lawyer receives fully pre-processed case packets in a prioritized queue, with AI-generated summaries, validation flags, confidence scores, draft complaints, and a legal assistant they can query in real time.

The connective tissue between these two fronts is a **RAG (Retrieval-Augmented Generation) system grounded in a legal knowledge graph** — a structured representation of Law 1480/2011, SIC procedures, official form templates, and past case patterns. This ensures that every draft complaint, every cited article, and every procedural step is retrieved from verified legal sources — not generated from the model's parametric memory.

**The key insight:** Cases repeat. A defective Samsung phone complaint filed in Cali follows the same legal structure as a defective Xiaomi phone complaint filed in Bogotá. The RAG/KG layer captures this repeatability — it stores the legal template, the procedural path, the required documents, and the applicable articles for each case type, so each new case retrieves and fills a proven structure rather than reasoning from scratch.

---

## 2. RAG + Knowledge Graph Layer

### Why RAG is necessary here

Without RAG, the LLM generates legal content from its training data. This creates three problems:
1. **Hallucination risk:** The model may cite articles that do not exist or misstate their content.
2. **Version risk:** Law 1480 has been amended. The model's training data may be outdated.
3. **Template ignorance:** The SIC has specific official form templates with exact field names and accepted legal language. A model generating free-form text will not match these.

RAG solves all three: the LLM retrieves the correct, current text before generating output.

### Knowledge graph structure

The knowledge graph is built in **Neo4j** and indexed by **LlamaIndex** for retrieval. It has four layers:

```
LAYER 1 — LEGAL ARTICLES (Law 1480/2011 + SIC resolutions)
  Node: Article
    Properties:
      - article_id: "Ley1480_Art7"
      - text: "Los productores y proveedores serán responsables..."
      - plain_summary: "Every product sold commercially has a minimum 1-year warranty."
      - applies_to: ["bienes_muebles", "bienes_inmuebles", "servicios"]
      - requires_conditions: ["relacion_de_consumo", "compra_a_proveedor"]
      - exceptions: ["compra_entre_particulares", "bien_sin_defecto"]
      - remedy: ["reparacion", "reposicion", "devolucion_precio"]
      - deadline: "1 año desde entrega del bien"
      - source_url: "https://www.sic.gov.co/ley-1480"
      - last_verified: "2025-01-01"

LAYER 2 — CASE TYPE PATTERNS (repeating complaint structures)
  Node: CasePattern
    Properties:
      - pattern_id: "CASE_A_DEFECTIVE_PRODUCT_PHYSICAL_STORE"
      - case_type: "A"
      - description: "Producto defectuoso comprado en tienda física"
      - primary_articles: ["Ley1480_Art7", "Ley1480_Art11"]
      - secondary_articles: ["Ley1480_Art56", "Ley1480_Art58"]
      - required_documents: ["factura_o_recibo", "garantia_del_fabricante"]
      - optional_documents: ["carta_rechazo_empresa", "evidencia_defecto"]
      - sic_form_template_id: "SIC_FORM_GARANTIA_001"
      - typical_pretensions: ["reparacion", "reposicion_subsidiaria", "devolucion_precio"]
      - estimated_resolution_days: 30
      
  Edges:
    CasePattern → GROUNDED_IN → Article (with condition metadata)
    CasePattern → REQUIRES_DOC → DocumentType
    CasePattern → USES_TEMPLATE → SICFormTemplate

LAYER 3 — SIC FORM TEMPLATES (official complaint structures)
  Node: SICFormTemplate
    Properties:
      - template_id: "SIC_FORM_GARANTIA_001"
      - form_name: "Queja Garantía Legal — Producto Defectuoso"
      - fields: [
          "nombre_consumidor", "cedula", "direccion", "telefono",
          "nombre_proveedor", "nit_proveedor", "direccion_proveedor",
          "descripcion_bien_servicio", "valor_pagado", "fecha_compra",
          "descripcion_hecho", "pretension_principal", "pretension_subsidiaria",
          "fundamentos_de_derecho", "documentos_anexos"
        ]
      - required_fields: [all 14]
      - legal_language_requirements: {
          "descripcion_hecho": "must reference specific defect and timeline",
          "pretension_principal": "must cite specific remedy article",
          "fundamentos_de_derecho": "must cite Ley 1480 articles"
        }
      - sample_language: {
          "pretension_principal": "Se ordene al proveedor [...] la reparación del bien
                                   en los términos del artículo 11 de la Ley 1480 de 2011..."
        }

LAYER 4 — DOCUMENT EXTRACTION SCHEMAS (what to pull from each document type)
  Node: DocumentSchema
    Properties:
      - schema_id: "SCHEMA_FACTURA_ELECTRONICA_COL"
      - document_type: "factura_electronica"
      - extraction_targets: [
          "fecha_emision", "nit_vendedor", "nombre_vendedor",
          "descripcion_producto", "valor_total", "forma_pago",
          "garantia_declarada", "numero_factura"
        ]
      - extraction_confidence_threshold: 0.85
      - fallback_if_unreadable: "request_alternative_document"
```

### How the RAG pipeline works

```
QUERY: "Defective Samsung phone, bought at a physical store, store refuses to replace"

STEP 1 — Semantic search over CasePattern nodes
  LlamaIndex embeds the query → finds CASE_A_DEFECTIVE_PRODUCT_PHYSICAL_STORE (score: 0.94)

STEP 2 — Graph traversal from matched pattern
  CasePattern → GROUNDED_IN → [Ley1480_Art7, Ley1480_Art11]
  CasePattern → USES_TEMPLATE → SIC_FORM_GARANTIA_001
  CasePattern → REQUIRES_DOC → [factura_o_recibo, garantia_del_fabricante]

STEP 3 — Context assembly for LLM
  Retrieved context includes:
    - Full text of Art. 7 and Art. 11
    - SIC form template with all 14 fields and required language
    - Document extraction schema for factura_electronica
    - Sample legal language for pretensiones and fundamentos

STEP 4 — LLM generation (Claude API) with retrieved context
  Prompt structure:
    SYSTEM: "You are a Colombian consumer rights legal assistant. Generate a formal
             SIC complaint using ONLY the legal articles and form structure provided
             in the context below. Do not cite any article not in the context.
             Do not invent legal rights."
    CONTEXT: [retrieved graph content — articles, template, sample language]
    FACTS: [validated fact sheet from DocumentParser + interview]
    TASK: "Fill all 14 fields of SIC_FORM_GARANTIA_001 using the facts provided."

STEP 5 — Output validation
  Post-generation check: every cited article must exist in retrieved context.
  If a citation appears that was not in the retrieval → strip it and flag for lawyer review.
```

### What the knowledge graph enables that plain prompting cannot

| Capability | Without KG (plain prompting) | With KG (RAG) |
|---|---|---|
| Article accuracy | Model may hallucinate | Only retrieved, verified articles used |
| Template compliance | Free-form output may miss required fields | 14 SIC fields filled from template schema |
| Case reuse | Every case reasoned from scratch | Matching case pattern retrieved; proven structure reused |
| Auditability | "The model said so" | "Retrieved from node Ley1480_Art7, path A→B→C" |
| Extensibility | Update training data (impossible) | Add/update graph nodes (minutes) |
| New case type | Needs re-prompting and testing | Add new CasePattern node |

### What gets pre-loaded into the knowledge graph (before the hackathon demo)

- Full text of Ley 1480/2011 (47 articles most relevant to consumer complaints)
- SIC Circular Única relevant sections (procedural rules for complaint filing)
- 3 official SIC form templates (one per case type A/B/C)
- 3 case patterns (A/B/C) with full document requirements, applicable articles, typical pretensions
- Document extraction schemas for: factura electrónica, estado de cuenta bancario, contrato de servicio, última factura de telecomunicaciones, carta de rechazo
- Sample legal language for each of the 14 SIC form fields across all 3 case types

---

## 3. Full Stack — Component Map

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           ROSA-FACING LAYER                                     │
│                                                                                 │
│  PWA Chat Interface (React / Lovable)                                           │
│  ├── Text input                                                                 │
│  ├── Voice input → Whisper API transcription                                    │
│  └── File upload → PDF + photo                                                  │
└────────────────────────────┬────────────────────────────────────────────────────┘
                             │ HTTPS + WebSocket
┌────────────────────────────▼────────────────────────────────────────────────────┐
│                         ORCHESTRATION LAYER                                     │
│                    LangChain multi-agent pipeline                               │
│                    (Google Cloud Run — containerized)                           │
│                                                                                 │
│  Agents:                                                                        │
│  ├── IntakeInterviewer          (Claude API)                                    │
│  ├── DocumentRequestPlanner     (Claude API)                                    │
│  ├── DocumentParser             (PyMuPDF + pdfplumber + Claude Vision)          │
│  ├── EvidenceCrossValidator     (Claude API)                                    │
│  ├── LegalClassifier            (Claude API + RAG)                              │
│  ├── ComplaintDraftGenerator    (Claude API + RAG)                              │
│  ├── DraftValidator             (Claude API — post-generation check)            │
│  ├── DeadEndNavigator           (Claude API)                                    │
│  └── CasePackager               (deterministic — no LLM)                       │
│                                                                                 │
│  State management: Cloud Tasks queue + Firestore case state                     │
└──────────────┬────────────────────────────────────────┬────────────────────────┘
               │                                        │
┌──────────────▼──────────────┐         ┌──────────────▼────────────────────────┐
│      RAG / KG LAYER         │         │           EXTERNAL SERVICES            │
│                             │         │                                        │
│  Neo4j Aura (graph DB)      │         │  vLex API — article text & precedents  │
│  LlamaIndex (indexing +     │         │  RUES API — seller NIT verification    │
│    retrieval over Neo4j)    │         │  Whisper API — voice transcription     │
│                             │         │  Google Cloud Storage — case files     │
│  Graph contents:            │         │  Firestore — case state + audit log    │
│  - Law 1480 articles        │         │                                        │
│  - SIC form templates       │         └────────────────────────────────────────┘
│  - Case patterns (A/B/C)    │
│  - Document schemas         │
│  - Sample legal language    │
└─────────────────────────────┘
               │
┌──────────────▼────────────────────────────────────────────────────────────────┐
│                        LAWYER COMMAND CENTER LAYER                             │
│                    Separate web dashboard (React)                              │
│                                                                                │
│  ├── Case queue (prioritized by deadline + flags)                              │
│  ├── Per-case view: AI summary, validation flags, documents, draft            │
│  ├── Lawyer AI assistant (Claude API + case context + vLex)                   │
│  ├── Batch approval mode                                                       │
│  ├── Escalation routing                                                        │
│  ├── Audit log viewer (full pipeline trace, exportable PDF)                    │
│  └── Deadline tracker with 30/7/1 day alerts                                  │
└────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. AI Tool per Pipeline Stage

| Stage | Component | AI Tool | Why this tool |
|---|---|---|---|
| Voice transcription | PWA → backend | **Whisper API** (via Groq for speed) | Best-in-class Spanish transcription; Groq provides low-latency inference |
| Image/photo document extraction | DocumentParser | **Claude API (Vision)** | Handles Colombian-format receipts, handwritten notes, screenshots |
| PDF text extraction | DocumentParser | **pdfplumber + PyMuPDF** | No LLM needed; deterministic extraction is faster and cheaper |
| Intake interview | IntakeInterviewer | **Claude API (claude-3-5-sonnet)** | Best-in-class conversational Spanish; follows complex multi-turn instructions |
| Document request planning | DocumentRequestPlanner | **Claude API** | Needs to reason about what evidence is legally sufficient per case type |
| Evidence cross-validation | EvidenceCrossValidator | **Claude API** | Semantic comparison between narrative and extracted facts |
| Legal RAG retrieval | LegalClassifier → retrieval step | **LlamaIndex + Neo4j** | Structured graph traversal + semantic vector search over legal corpus |
| Legal classification | LegalClassifier → synthesis step | **Claude API** with retrieved context | Grounded synthesis from retrieved articles; Claude follows "do not invent" instruction reliably |
| Complaint draft generation | ComplaintDraftGenerator | **Claude API** with RAG context | Fills SIC form template fields using retrieved sample language + validated facts |
| Post-generation article validation | DraftValidator | **Deterministic check** (Python) | Every cited article ID in draft is checked against a set of valid article IDs — no LLM needed |
| No-claim path | DeadEndNavigator | **Claude API** | Plain-language explanation generation; alternative routing |
| Case packet assembly | CasePackager | **No LLM** (deterministic) | JSON assembly from structured outputs — deterministic is faster and auditable |
| Lawyer AI assistant | Command Center chat | **Claude API + vLex API** | Long-context reasoning over case packet + legal search; Claude handles complex legal Q&A |
| Priority scoring | Queue manager | **No LLM** (formula-based) | Priority = deadline urgency + flag count + claim amount; no LLM needed |

**Why Claude API as the primary LLM (not Mistral or other options):**
- Claude 3.5 Sonnet has the strongest performance on instruction-following in Spanish
- Critical for "do not cite articles not in context" — Claude follows this constraint more reliably than alternatives
- Multimodal (Vision) eliminates need for a separate vision model
- Available in the hackathon tool list

**Where Groq is used:**
- Whisper transcription (low latency, important for voice UX)
- Any real-time inference path where speed is user-facing (e.g., first response to Rosa's message)

**Where Mistral could substitute:**
- Any non-critical synthesis step if Claude API rate limits are hit during the 24h sprint

---

## 5. Full AI Pipeline — All Stages

```
═══════════════════════════════════════════════════════════════════════════════
                        ROSA-FACING PIPELINE
═══════════════════════════════════════════════════════════════════════════════

STAGE 0 — MULTIMODAL INTAKE
─────────────────────────────────────────────────────────────────────────────
INPUT:   Rosa's first message (voice or text)
TOOL:    Whisper API (if voice) → raw transcript
         Groq API / llama-3.3-70b-versatile (IntakeInterviewer)

PROCESS:
  IntakeInterviewer receives the raw input.

  PHASE A — Minimum variables (Nodo 0, árbol de decisiones):
    Always collect first, regardless of case type:
    - nombre_consumidor, cédula, domicilio
    - nombre_proveedor, dirección_proveedor
    Evidence required: cédula + factura/contrato/extracto

  PHASE B — Case type triage:
    "¿El problema fue con un producto físico, con un cobro financiero o bancario,
     o con un servicio de internet o telefonía?"
    → Routes to Scenario A, B, or C branch

  PHASE C — Scenario-specific questions (following arboldecisionesdereclamacion.txt):

    SCENARIO A (bien defectuoso / publucidad engañosa — Nodo 2A/2B):
      The interviewer MUST capture these minimum variables:
        1. ¿Qué producto compraste? (tipo: celular, electrodoméstico, etc.)
        2. ¿Cuál es la marca y modelo? / ¿Tiene número IMEI o serial?
        3. ¿Dónde lo compraste? (tienda física, internet, mercado)
        4. ¿A quién se lo compraste? (nombre del vendedor/tienda)
        5. ¿Cuánto pagaste?
        6. ¿Qué defecto tiene? ¿Qué es lo que le pasa exactamente?
        7. ¿Desde cuándo presentó el problema?
        8. ¿Cuándo lo compraste aproximadamente?
        9. ¿Qué solución estás buscando? (reparación, cambio, devolución de dinero)
      Documents to request: factura, soporte IMEI/serial, fotos/videos,
        chats con tienda, tarjeta de garantía
      System may ask additional questions it deems pertinent beyond this minimum.

    SCENARIO B (cobro financiero — Nodo 3A):
      The interviewer MUST capture these minimum variables:
        1. ¿Con qué entidad tienes el producto financiero?
        2. ¿Es un banco, aseguradora, o fintech / empresa de financiación?
           [CRITICAL BIFURCATION — determines competent authority]
           → Si entidad vigilada por Superfinanciera → ruta Superfinanciera, NO SIC
           → Si fintech o financiación no vigilada → ruta SIC
        3. ¿Qué tipo de cobro fue? (cargo no autorizado, interés excesivo,
           cláusula abusiva, publicidad engañosa sobre condiciones)
        4. ¿De cuánto fue el cobro? ¿En qué fecha apareció?
        5. ¿Ya reclamaste ante la entidad? ¿Qué te respondieron?
        6. ¿Tienes el contrato o las condiciones que te ofrecieron?
        7. ¿Qué solución buscas?
      Documents to request: extracto bancario, contrato del servicio financiero,
        publicidad/oferta recibida, comunicación de rechazo de la entidad
      System may ask additional questions it deems pertinent beyond this minimum.

    SCENARIO C (telecomunicaciones — Nodo 3B):
      The interviewer MUST capture these minimum variables:
        1. ¿Con qué operador tienes el servicio? (Claro, Movistar, Tigo, ETB, etc.)
        2. ¿Qué tipo de servicio? (internet, telefonía móvil, TV, paquete)
        3. ¿Cuál es el número de línea o contrato?
        4. ¿Qué problema tienes? (corte, velocidad inferior a la contratada,
           cobros incorrectos, publicidad engañosa sobre el plan)
        5. ¿Cuándo empezó el problema?
        6. ¿Ya hiciste una PQR ante el operador? ¿Cuándo? ¿Tienes el número de radicado?
           [CRITICAL — mandatory prior step before SIC complaint for telecom]
        7. ¿Qué solución buscas?
      Documents to request: factura del servicio, contrato/plan contratado,
        número de línea, radicados PQR previos, chats o correos con el operador
      System may ask additional questions it deems pertinent beyond this minimum.

  TRANSVERSAL NODE — Pretensiones:
    After scenario-specific questions, always ask:
    - "¿Qué solución exactamente estás buscando?"
    - "¿Es una solución económica (quieres que te devuelvan o paguen dinero)?
       Si es así, ¿a cuánto aproximadamente asciende?"

  After all minimum variables collected + pretensiones, produces:
  {
    "intake_summary": {
      "case_type_hypothesis": "A" | "B" | "C",
      "confidence": 0.87,
      "scenario_b_entity_type": null | "vigilada_superfinanciera" | "no_vigilada",
      "scenario_c_pqr_filed": null | true | false,
      "facts_identified": { ... },
      "missing_facts": [...],
      "pretension_type": "economic" | "repair" | "replacement" | "other",
      "pretension_amount": null | "COP 890.000",
      "notes": "..."
    }
  }

OUTPUT:  Structured intake summary JSON + conversation transcript
─────────────────────────────────────────────────────────────────────────────

STAGE 1 — RAG CASE PATTERN MATCHING
─────────────────────────────────────────────────────────────────────────────
INPUT:   Intake summary JSON
TOOL:    LlamaIndex semantic search over Neo4j CasePattern nodes

PROCESS:
  Query: embed intake_summary facts → search CasePattern layer of knowledge graph
  Best match: CASE_A_DEFECTIVE_PRODUCT_PHYSICAL_STORE (score: 0.91)

  Graph traversal from matched pattern retrieves:
    - Primary articles: [Ley1480_Art7, Ley1480_Art11]
    - Secondary articles: [Ley1480_Art56]
    - Required documents: [factura_o_recibo]
    - Optional documents: [garantia_fabricante, carta_rechazo]
    - SIC form template: SIC_FORM_GARANTIA_001
    - Sample legal language: {pretension_principal, fundamentos_de_derecho}
    - Applicable deadline: "1 año desde la compra o descubrimiento del vicio"

OUTPUT:  Retrieved legal context bundle (articles + template + document list)
─────────────────────────────────────────────────────────────────────────────

STAGE 2 — DOCUMENT REQUEST PLANNING
─────────────────────────────────────────────────────────────────────────────
INPUT:   Retrieved document requirements from Stage 1
TOOL:    Claude API (DocumentRequestPlanner)

PROCESS:
  Agent reads: required_documents from CasePattern node
  Generates plain-language request for the FIRST required document:

  "Para ayudarte con tu reclamación, necesito que me subas el recibo o
   la factura de cuando compraste el celular.
   
   Esto es importante porque la SIC necesita saber el nombre de la tienda,
   cuánto pagaste y la fecha de compra.
   
   Puedes:
   → Tomar una foto del recibo con tu celular
   → Subir un PDF si te lo enviaron por correo
   → Decirme si no tienes el recibo (buscaremos otra solución)"

  After Rosa uploads: request next document (if applicable)
  After all requested: proceed to Stage 3

OUTPUT:  Document request messages (one at a time) + Rosa's uploaded files
─────────────────────────────────────────────────────────────────────────────

STAGE 3 — DOCUMENT EXTRACTION
─────────────────────────────────────────────────────────────────────────────
INPUT:   Uploaded files (PDF or image) + DocumentSchema from KG
TOOL:    pdfplumber (PDF text) + PyMuPDF (PDF structure) + Tesseract+OpenCV (scans/photos)

PROCESS:
  For each uploaded file:
    1. Detect file type and document category
    2. Load DocumentSchema from KG for that document type
    3. Extract each target field using pdfplumber / PyMuPDF
    4. For fields that failed text extraction → Tesseract+OpenCV on the page image
    5. Assign confidence score per field
    6. If overall document confidence < 0.70 (illegible threshold):
       → Mark document as ILLEGIBLE
       → DO NOT proceed with incomplete extraction
       → Mandatory: push document to lawyer dashboard for manual verification
         (status: BLOCKED_PENDING_MANUAL_REVIEW)
       → Notify Rosa: "Uno de tus documentos no se pudo leer bien. Un abogado
         lo va a revisar manualmente."
       → Pipeline HALTS at Stage 3 for this case until lawyer clears the document
       → Lawyer dashboard shows the document in a "Documentos ilegibles" queue
         with an image preview and manual field entry form
       → Lawyer manually enters or confirms extracted fields → marks as VERIFIED
       → Pipeline resumes from Stage 3 with lawyer-verified fields
    7. For fields below per-field threshold (0.85) but document overall >= 0.70:
       → Flag individual field for lawyer attention (non-blocking warning)

  Produces document fact sheet:
  {
    "document_type": "factura_electronica",
    "extracted_fields": {
      "fecha_compra": {"value": "2025-11-14", "confidence": 0.97, "source": "pdfplumber"},
      "nombre_vendedor": {"value": "TechStore Cali S.A.S.", "confidence": 0.99, "source": "pdfplumber"},
      "nit_vendedor": {"value": "900.123.456-7", "confidence": 0.98, "source": "pdfplumber"},
      "producto": {"value": "Samsung Galaxy A15", "confidence": 0.95, "source": "pdfplumber"},
      "valor_pagado": {"value": "COP 890.000", "confidence": 0.99, "source": "pdfplumber"},
      "forma_pago": {"value": "cuotas", "confidence": 0.87, "source": "pdfplumber"},
      "garantia_declarada": {"value": "6 meses", "confidence": 0.72, "source": "tesseract",
                             "flag": "BELOW_THRESHOLD — lawyer should verify"}
    },
    "document_confidence_overall": 0.93,
    "illegible": false,
    "unreadable_pages": [],
    "rues_verification": "PENDING"
  }

  Parallel: NIT → RUES API call → verify seller is a registered commercial entity
  (This is the relación_de_consumo verification — key legal condition)

OUTPUT:  Structured document fact sheet per uploaded document
         OR: BLOCKED status → lawyer manual review queue entry
─────────────────────────────────────────────────────────────────────────────

STAGE 4 — EVIDENCE CROSS-VALIDATION
─────────────────────────────────────────────────────────────────────────────
INPUT:   Intake summary + document fact sheet(s) + RUES verification result
TOOL:    Claude API (EvidenceCrossValidator)

PROCESS:
  Compare intake summary facts vs. document fact sheet fields:

  CRITICAL checks:
    ✓ Seller type = physical store AND RUES shows registered company → relación de consumo confirmed
    ✓ Product description consistent across narrative and invoice

  WARNING checks:
    ⚠ Intake says "hace dos meses" → invoice shows Nov 14, 2025 → that's ~5 months ago
      FLAG: Date discrepancy — narrative timeline does not match document
      ACTION: Generate clarification question for Rosa:
        "El recibo dice que compraste el celular el 14 de noviembre de 2025,
         pero antes me dijiste 'hace como dos meses'. ¿Cuál es la fecha correcta?"
    ⚠ Stated warranty on invoice: "6 meses" — but Law 1480 Art. 7 guarantees 1 year minimum
      FLAG: INFO — seller stated warranty is shorter than statutory minimum
      NOTE: This actually HELPS Rosa — statutory warranty overrides stated warranty

  INFO checks:
    ℹ No denial letter uploaded — complaint can still proceed (verbal refusal is sufficient)
    ℹ Payment method is "cuotas" — flag for lawyer (potential financial services angle)

OUTPUT:  Validation report with all flags, resolved discrepancies, and updated fact set
─────────────────────────────────────────────────────────────────────────────

STAGE 5 — LEGAL CLASSIFICATION
─────────────────────────────────────────────────────────────────────────────
INPUT:   Validated fact set + retrieved legal context from Stage 1
TOOL:    Groq API / llama-3.3-70b-versatile (LegalClassifier) — on retrieved context only

PROCESS:
  Using ONLY articles retrieved from the knowledge graph:

  SCENARIO ROUTING — applies applicable law per case type:

    SCENARIO A (defective product / Ley 1480):
      Primary articles:
        - Art. 7 Ley 1480/2011 — garantía legal mínima (1 año productos nuevos)
        - Art. 10 Ley 1480/2011 — idoneidad y calidad
        - Art. 11 Ley 1480/2011 — efectividad de la garantía (remedies)
        - Art. 16 Ley 1480/2011 — responsabilidad solidaria productor/expendedor
        - Art. 58 Ley 1480/2011 — acciones ante SIC
      Conditions to verify:
        - relación de consumo (RUES verified)
        - bien mueble comprado a proveedor comercial
        - dentro del plazo de garantía (< 1 año desde compra)
        - vicio o defecto en el bien
      Note: carga de prueba en el consumidor para demostrar el defecto

    SCENARIO B (cobro financiero) — CRITICAL BIFURCATION:
      FIRST check: ¿La entidad está vigilada por la Superfinanciera?
        → IF YES (banco, aseguradora, fiduciaria, etc.):
             AUTHORITY: Superfinanciera de Colombia, NOT SIC
             Applicable law: Ley 1328/2009 (derechos del consumidor financiero)
                              + Decreto 2555/2010
             DeadEndNavigator informs: "Esta reclamación no va ante la SIC.
               La entidad es vigilada por la Superfinanciera. Te guiamos
               al procedimiento correcto."
             claim_valid = false (for SIC), but redirect = "Superfinanciera"
        → IF NO (fintech, plataforma de financiación, comercio con crédito propio):
             AUTHORITY: SIC
             Applicable law:
               - Ley 1480/2011 (Estatuto del Consumidor) — primary
               - Ley 45/1990 — seguros y normas financieras complementarias
               - Decreto 1074/2015 (DUR Sector Comercio) — regulatory
             Check for sub-scenarios:
               - Cláusula abusiva (Nodo 3A.1): Art. 42-43 Ley 1480
               - Publicidad engañosa (Nodo 3A.2): Art. 29-30 Ley 1480

    SCENARIO C (telecomunicaciones):
      PROCEDURAL PREREQUISITE: Verify PQR was filed with operator first.
        If PQR NOT filed: DeadEndNavigator informs mandatory prior step.
          "Antes de ir a la SIC debes presentar una PQR ante el operador.
           La SIC solo puede actuar después de que el operador responda
           (o no responda en 15 días hábiles). ¿Quieres que te ayudemos
           a preparar la PQR?"
        If PQR filed but no resolution yet: same — must wait for operator response.
        If PQR resolved unsatisfactorily OR no response: proceed to SIC complaint.
          → Resource path: reposición y en subsidio apelación ante el operador
                            → SIC resuelve la apelación
      Primary law:
        - Ley 1341/2009 arts. 54+ — régimen telecomunicaciones (PRINCIPAL)
        - Resolución CRC 5050/2016 — regulación CRC (PRINCIPAL)
      Supplementary law:
        - Ley 1480/2011 — supletoria (only when Ley 1341 does not resolve)
      Sub-scenarios:
        - Publicidad engañosa plan (Nodo 3B.1): Art. 29-30 Ley 1480 supletorio
        - Cláusula abusiva contrato (Nodo 3B.2): Art. 42-43 Ley 1480 supletorio

  CONDITION CHECK (scenario-adapted):
    [✓/✗] Relación de consumo
    [✓/✗] Competencia SIC (vs. Superfinanciera for Scenario B)
    [✓/✗] Prerequisitos procedimentales (PQR for Scenario C)
    [✓/✗] Dentro del plazo aplicable
    [✓/✗] Hecho generador verificado

  CLASSIFICATION OUTPUT:
  {
    "applicable_law": "Ley 1480/2011" | "Ley 1341/2009 + CRC" | "Ley 1328/2009",
    "competent_authority": "SIC" | "Superfinanciera",
    "applicable_articles": [
      {"id": "Ley1480_Art7", "role": "primary", "confidence": 0.93},
      ...
    ],
    "rights_established": [...],
    "procedural_route": "...",
    "procedural_prerequisites_met": true | false,
    "prerequisite_note": null | "Must file PQR with operator first",
    "deadline": "...",
    "overall_confidence": 0.91,
    "uncertainty_notes": "...",
    "claim_valid": true | false,
    "no_claim_reason": null | "entidad_vigilada_superfinanciera" | "sin_pqr_previa" | ...
  }

  BRANCH: If claim_valid = false → Stage 5b (DeadEndNavigator + Lawyer Review Gate)

OUTPUT:  Legal classification JSON with cited articles and confidence scores
─────────────────────────────────────────────────────────────────────────────

STAGE 5b — NO-CLAIM PATH (DeadEndNavigator + Mandatory Lawyer Review Gate)
─────────────────────────────────────────────────────────────────────────────
INPUT:   Validated facts where claim_valid = false (e.g., private sale,
         entity is Superfinanciera-regulated, mandatory PQR not filed, etc.)
TOOL:    Groq API / llama-3.3-70b-versatile (DeadEndNavigator)

PROCESS:
  DeadEndNavigator generates plain-language explanation of why the claim
  is not actionable before SIC (or not actionable at all).

  Provides alternatives based on no_claim_reason:
    - entidad_vigilada_superfinanciera → redirect to Superfinanciera procedure
    - sin_pqr_previa → guide Rosa to file PQR with operator first
    - compra_entre_particulares → civil court / small claims
    - fuera_de_plazo → limitation expired, explain honestly
    - sin_relacion_de_consumo → explain, offer Defensoría del Pueblo

  LAWYER REVIEW GATE (mandatory — cannot be skipped):
    Case enters a dedicated "PENDING_CLAIM_DECISION" queue in the lawyer dashboard.
    The lawyer sees:
      - DeadEndNavigator's reason and explanation draft
      - Full case facts and documents
      - Action required: explicit binary decision
        [CONFIRM: NO CLAIM — send explanation to Rosa]
        [OVERRIDE: YES CLAIM — send case back to Stage 5 for reclassification]
    
    This gate is a HARD GATE:
      → System does NOT notify Rosa with the dead-end result until the lawyer
        has reviewed and explicitly selected one of the two options.
      → If lawyer confirms NO CLAIM: generate Rejection Document (Stage 5c)
      → If lawyer overrides to CLAIM: re-enter Stage 5 with lawyer's notes

  Rosa is told: "Tu caso está siendo revisado por un abogado antes de darte
    una respuesta final." (no dead-end language until lawyer confirms)

OUTPUT:  Plain-language dead-end explanation + alternatives + referral summary
         + PENDING_CLAIM_DECISION entry in lawyer dashboard
─────────────────────────────────────────────────────────────────────────────

STAGE 5c — REJECTION DOCUMENT GENERATION (when lawyer confirms NO CLAIM)
─────────────────────────────────────────────────────────────────────────────
INPUT:   Lawyer-confirmed NO CLAIM decision + case facts + no_claim_reason
TOOL:    Groq API / llama-3.3-70b-versatile + deterministic clinic rules checker

PROCESS:
  System generates a formal rejection document explaining in detail why the
  case cannot be carried forward. This document must cover:

  SECTION 1 — Legal grounds for rejection:
    - Why Ley 1480 / SIC jurisdiction does not apply in this case
    - Applicable legal basis for the determination
    - Whether any alternative route exists (Superfinanciera, CRC, civil court)

  SECTION 2 — Clinic eligibility rules (deterministic check):
    The system verifies and documents which clinic operational rules apply:
    - Reparto electrónico: lunes y jueves (2 veces/semana)
    - Plazo revisión estudiante: 1 día hábil para verificar información suficiente
    - Plazo carga TAREAS: 3 días hábiles (revisadas por asesora, hasta 5pm)
    - Plazo carga PROCESOS: 5 días hábiles (revisados por asesora, hasta 5pm)
    - Fecha entrega al usuario: 10 días hábiles desde día siguiente a fecha de atención
    - Casos NO recibidos por la clínica:
        * Con poder dado a otro abogado
        * Con términos de garantía o vencimiento muy cercanos (< 15 días hábiles)
        * Fuera del ámbito de la clínica
    If any exclusion criterion applies → documented explicitly in the rejection

  SECTION 3 — Alternatives and referral:
    Specific alternative routes the user CAN pursue with contact information

  LAWYER VALIDATION:
    The generated rejection document is sent to the lawyer for review and editing
    before delivery. Lawyer must explicitly approve the rejection document.
    (This is an additional validation step — not automatic.)

  OUTPUT: Formal rejection document (PDF-ready) + lawyer review request
─────────────────────────────────────────────────────────────────────────────

STAGE 6 — COMPLAINT DRAFT GENERATION
─────────────────────────────────────────────────────────────────────────────
INPUT:   Validated fact set + legal classification + SIC form template from KG
TOOL:    Claude API (ComplaintDraftGenerator) — operating on RAG context

PROCESS:
  Claude receives:
    - All 14 SIC form fields from SIC_FORM_GARANTIA_001 template
    - Required legal language patterns for each field
    - Validated facts (date, seller, product, price, defect, NIT)
    - Retrieved article texts (Art. 7, Art. 11)
    - Sample pretension and fundamentos language from KG

  Generates OUTPUT A — Rosa's plain summary:
    "Según lo que nos contaste y los documentos que subiste, tienes derecho
     a pedir que te arreglen el celular, te lo cambien, o te devuelvan la plata.
     Esto es según la Ley del Consumidor (Ley 1480 de 2011).
     
     Tu reclamación ha quedado lista. Un abogado la va a revisar antes de enviarla."

  Generates OUTPUT B — SIC formal complaint (all 14 fields):
    DATOS DEL CONSUMIDOR: [Rosa's name, ID, address, phone]
    DATOS DEL PROVEEDOR: TechStore Cali S.A.S., NIT 900.123.456-7, dirección...
    DESCRIPCIÓN DEL BIEN/SERVICIO: Samsung Galaxy A15, COP 890.000, factura #X...
    DESCRIPCIÓN DE LOS HECHOS:
      1. El 14 de noviembre de 2025, la señora [...] adquirió un bien denominado
         Samsung Galaxy A15, según consta en la Factura Electrónica No. [X] expedida
         por TechStore Cali S.A.S. (NIT 900.123.456-7), por valor de COP 890.000,
         mediante pago en cuotas.
      2. Desde la fecha de adquisición, el bien presentó falla funcional consistente
         en apagado espontáneo, constituyendo un vicio que afecta su uso normal,
         en los términos del artículo 7 de la Ley 1480 de 2011.
      3. La consumidora se presentó ante el proveedor para solicitar solución,
         siendo su reclamación rechazada verbalmente sin fundamentación.
    PRETENSIÓN PRINCIPAL:
      Se ordene al proveedor TechStore Cali S.A.S. la reparación del bien Samsung
      Galaxy A15 en los términos del artículo 11 de la Ley 1480 de 2011, dentro
      del plazo de treinta (30) días calendario contados a partir de la notificación.
    PRETENSIÓN SUBSIDIARIA:
      En caso de que la reparación no sea posible en el plazo señalado, se ordene
      la reposición del bien por otro de idénticas o similares características.
    PRETENSIÓN SUBSIDIARIA DE LA SUBSIDIARIA:
      En caso de que la reposición no sea posible, se ordene la devolución del precio
      pagado (COP 890.000) en los términos del artículo 11 ibídem.
    FUNDAMENTOS DE DERECHO:
      Ley 1480 de 2011, artículos 5 (definiciones), 7 (garantía legal mínima),
      11 (efectividad de la garantía) y 56 (derecho a recibir información).
    DOCUMENTOS ANEXOS: [Factura Electrónica No. X — TechStore Cali — 2025-11-14]

─────────────────────────────────────────────────────────────────────────────

STAGE 7 — DRAFT VALIDATION (post-generation check)
─────────────────────────────────────────────────────────────────────────────
INPUT:   Generated draft + set of valid article IDs from KG
TOOL:    Deterministic Python script (no LLM)

PROCESS:
  For every article citation in the draft:
    assert article_id in knowledge_graph.valid_article_ids

  If any citation is NOT in the KG:
    → Strip the citation from the draft
    → Add flag: "INVALID_CITATION_REMOVED — article not found in verified corpus"
    → Lawyer must review before approval

  All 14 SIC form fields present? → assert all 14 filled
  Any field empty? → flag as INCOMPLETE_FIELD

OUTPUT:  Validated draft + validation pass/fail report
─────────────────────────────────────────────────────────────────────────────

STAGE 8 — CASE PACKET ASSEMBLY + QUEUE ENTRY
─────────────────────────────────────────────────────────────────────────────
INPUT:   All stage outputs
TOOL:    Deterministic CasePackager (no LLM)

PROCESS:
  Assembles:
    - Intake transcript (anonymized)
    - Document fact sheet (per document)
    - RUES verification result
    - Cross-validation report (all flags)
    - Legal classification JSON
    - Draft validation report
    - Both draft outputs (plain + formal)
    - Pipeline audit log (all stage outputs, timestamped)

  Calculates priority score:
    priority = (days_to_deadline < 30 ? 3 : 1) × (critical_flags × 2 + warning_flags)

  Pushes to Firestore with:
    case_id: "#2026-0471"
    status: "PENDING_REVIEW"
    priority: [calculated]
    assigned_lawyer: [auto-assigned from queue capacity]

  Sends Rosa:
    "Tu caso fue recibido. Número de referencia: #2026-0471.
     Un abogado lo va a revisar en las próximas 24 horas.
     Te avisaremos cuando esté listo."

═══════════════════════════════════════════════════════════════════════════════
                    LAWYER COMMAND CENTER PIPELINE
═══════════════════════════════════════════════════════════════════════════════

STAGE 9 — LAWYER REVIEW
─────────────────────────────────────────────────────────────────────────────
INPUT:   Case packet from Firestore
TOOL:    Lawyer dashboard (React) + Claude API (LawyerAssistant)

PROCESS:
  Lawyer opens case. Sees:
    - AI summary (2–3 sentences)
    - Validation flags (severity-graded)
    - Parsed documents with extracted fields
    - Legal classification with confidence scores and article citations
    - Draft validation report (were any citations removed?)
    - Full pipeline audit log (expandable)
    - Both draft versions (plain + formal)

  Lawyer actions available:
    [APPROVE] → moves to Stage 10
    [EDIT DRAFT] → lawyer edits directly; changes logged
    [REQUEST MORE DOCS] → system sends Rosa a new document request message
    [ESCALATE] → routes to senior lawyer / professor
    [MARK NO CLAIM] → overrides AI classification; system sends Rosa alternative options
    [ADD LEGAL NOTE] → lawyer adds note visible to future reviewer

  Lawyer AI assistant (LawyerAssistant):
    Lawyer can ask:
    > "What SIC resolutions exist for spontaneous-shutdown defects in the last 2 years?"
      → LawyerAssistant queries vLex API → returns relevant precedents
    > "Can Rosa also claim moral damages in this case type?"
      → LawyerAssistant queries KG + Claude → "Art. 16 Ley 1480 allows it in egregious cases;
         this case does not yet show the threshold — recommend not including"
    > "The invoice warranty says 6 months — does this affect Art. 7?"
      → "No. Art. 7 para. 3 explicitly states the statutory warranty cannot be reduced
         by contractual terms. The 6-month stated warranty is unenforceable against Rosa."

─────────────────────────────────────────────────────────────────────────────

STAGE 10 — POST-APPROVAL: FILING OPTIONS PRESENTED TO ROSA
─────────────────────────────────────────────────────────────────────────────
INPUT:   Lawyer-approved draft + case packet
TOOL:    PDF generator + notification system

PROCESS:
  After lawyer approves, generate the final complaint PDF.
  
  STEP A — Generate deliverables:
    1. Final formal complaint PDF (all 14 fields filled, lawyer-edited)
    2. Plain-language summary for Rosa
  
  STEP B — Present 3 filing options to Rosa (MANDATORY USER CHOICE):
    Rosa must explicitly choose one of three options before the system proceeds.
    The system does NOT auto-file without Rosa's explicit selection.

    OPTION 1 — La clínica jurídica radica por ti:
      - "La clínica enviará tu reclamación a la SIC en tu nombre."
      - Requires: Rosa reviews the exact document that will be sent
                  (PDF shown inline for review)
      - Requires: Rosa clicks explicit approval: "Sí, autorizo el envío de este documento"
      - If Rosa approves → LawyerApprovalGate already cleared → SICSubmitter activates
        (Strategy A → B → C waterfall from Stage 10b)
      - If Rosa wants changes → back to lawyer for revision
      
    OPTION 2 — Tú radicas con el documento que te enviamos:
      - "Te damos el PDF listo. Tú lo radicas en el portal de la SIC o en persona."
      - Requires: Lawyer has already approved the case (already done at this stage)
      - System provides:
          * The approved PDF for download
          * Step-by-step filing guide (online portal + in-person Cali office)
          * Deadline reminder
      - Case status: CLOSED_DELIVERED_FOR_MANUAL_FILING

    OPTION 3 — Descartar el caso:
      - "El caso no puede avanzar."
      - Requires: Detailed explanation of why (system generates this, lawyer validates)
      - This triggers the Rejection Document generation flow (Stage 5c logic):
          → System generates formal rejection document
          → Lawyer validates rejection document before delivery to Rosa
          → Rosa receives the rejection document with full explanation
      - Case status: CLOSED_REJECTED

  STEP C — After option selection:
    Option 1 path → proceeds to Stage 10b (SICSubmitter)
    Option 2 path → delivers PDF + filing guide → closes case
    Option 3 path → triggers rejection document generation → lawyer validates → delivers to Rosa

─────────────────────────────────────────────────────────────────────────────

STAGE 10b — AUTOMATIC SIC SUBMISSION (Option 1 path — Plus feature)
─────────────────────────────────────────────────────────────────────────────
INPUT:   Lawyer-approved CasePacket + complaint PDF path + Rosa's explicit consent
TOOL:    SICSubmitter (backend/external/sic_submitter.py)

PRECONDITIONS (all three are hard gates — cannot be bypassed):
  1. LawyerApprovalGate.assert_approved(case_packet)
     → raises SubmissionBlockedError if lawyer_approved=False
  2. Rosa has explicitly selected Option 1 (clinic files on her behalf)
  3. Rosa has explicitly approved the exact document to be sent
     (rosa_document_consent=True stored in Firestore)
  → The system NEVER submits to the SIC without both lawyer approval AND
    Rosa's explicit document consent. This is enforced in code, not policy.

SUBMISSION STRATEGY WATERFALL:
  The SICSubmitter tries three strategies in order, stopping at the first
  that succeeds:

  STRATEGY A — Direct REST API (if SIC API credentials are configured)
  ─────────────────────────────────────────────────────────────────────
    Endpoint:  POST https://api.sic.gov.co/v1/quejas
    Auth:      OAuth2 client_credentials (institutional partner token)
    Payload:   JSON with all 14 SIC form fields + multipart PDF upload
    Returns:   radicado number + confirmation URL
    Use case:  Primary path if the SIC API is available (Canal Institucional)

  STRATEGY B — Browser automation via Playwright (fallback)
  ─────────────────────────────────────────────────────────────────────
    Tool:      Playwright + headless Chromium
    Portal:    https://www.sic.gov.co/quejas
    CAPTCHA:   Solved via 2captcha API (reCAPTCHA v2)
    Process:
      1. Navigate to portal → select complaint type
      2. Fill consumer data fields
      3. Fill provider data fields
      4. Fill product + facts + pretensiones
      5. Upload complaint PDF + attachments
      6. Solve CAPTCHA via 2captcha API
      7. Submit → extract radicado from confirmation page
    Use case:  When direct API is unavailable; portal still works

  STRATEGY C — Email to quejas@sic.gov.co (last resort)
  ─────────────────────────────────────────────────────────────────────
    Channel:   SMTP → quejas@sic.gov.co
    Content:   Structured email body (all formal complaint fields) +
               complaint PDF attached + supporting documents attached
    Returns:   Internal tracking ID (SIC radicado arrives by email in 3 days)
    Use case:  SIC-accepted accessibility channel (Circular Única §3.2.4)
               Valid when portal is down or API unavailable

RESULT:
  SICSubmissionResult {
    submission_id:         "2026-SIC-0471234"  (or internal EMAIL-* ID)
    submission_channel:    "api" | "browser" | "email"
    submitted_at:          ISO 8601 timestamp
    confirmation_document: URL or base64 PDF receipt (when available)
  }

  → Written to Firestore: case status = SUBMITTED_TO_SIC
  → Rosa notified:
      If API/browser success:
        "¡Tu reclamación ya fue radicada ante la SIC!
         Número de radicado: 2026-SIC-0471234
         La SIC te contactará en los próximos 10 días hábiles."
      If email only:
        "Tu reclamación fue enviada a la SIC por correo.
         Recibirás el número de radicado en los próximos 3 días hábiles.
         Guarda el PDF adjunto como respaldo."
      If all strategies fail:
        PDF delivered to Rosa + manual filing guide shown (3 options above)

  → Lawyer notified in Command Center with submission result + channel used

AUDIT LOG ENTRY (Stage 10b):
  {timestamp}  STAGE 10b  SICSubmitter START
  {timestamp}  STAGE 10b  Strategy A: [available/unavailable]
  {timestamp}  STAGE 10b  Strategy A result: [SUCCESS radicado=X | FAILED reason=Y]
  {timestamp}  STAGE 10b  Strategy B: [attempted/skipped]
  {timestamp}  STAGE 10b  Strategy B result: [SUCCESS radicado=X | FAILED reason=Y]
  {timestamp}  STAGE 10b  Strategy C: [attempted/skipped]
  {timestamp}  STAGE 10b  Strategy C result: [SUCCESS internal_id=X | FAILED reason=Y]
  {timestamp}  STAGE 10b  Final status: SUBMITTED_TO_SIC | PENDING_MANUAL_FILING
```

---

## 6. Document Processing Flow

### The governing principle

**The system never shows Rosa a form. It infers what it needs from what she says, then asks for specific documents with a reason.** Documents are requested one at a time, in order of legal importance, with a plain-language explanation for each.

### The document request decision tree

```
IntakeInterviewer output
  │
  ├── case_type = "A" (defective product, physical store)
  │     REQUIRED FIRST:  Factura / recibo de compra
  │       Reason given:  "Para confirmar la fecha y el vendedor"
  │     REQUIRED SECOND: [if warranty in dispute] Tarjeta de garantía del fabricante
  │       Reason given:  "Para ver qué garantía te ofrecieron"
  │     OPTIONAL:        Carta de rechazo de la tienda
  │       Reason given:  "Si la tienda te rechazó por escrito, eso fortalece tu caso"
  │
  ├── case_type = "B" (unauthorized financial charge)
  │     REQUIRED FIRST:  Estado de cuenta bancario (mostrando el cobro)
  │       Reason given:  "Para ver exactamente qué te cobraron y cuándo"
  │     REQUIRED SECOND: Contrato del servicio financiero
  │       Reason given:  "Para ver qué acordaste pagar"
  │     OPTIONAL:        Comunicación del banco rechazando el reclamo
  │
  └── case_type = "C" (telecom service breach)
        REQUIRED FIRST:  Última factura del servicio
          Reason given:  "Para ver el número de contrato y el servicio que tienes"
        REQUIRED SECOND: Contrato de servicio
          Reason given:  "Para ver qué nivel de servicio te prometieron"
        OPTIONAL:        Registro de fallas reportadas (screenshots, tickets)
```

### Document handling edge cases

| Situation | System response |
|---|---|
| Rosa uploads a blank or corrupted PDF | "Este archivo no se pudo leer. ¿Puedes tomar una foto del documento con tu celular?" |
| Photo is too dark or blurry | Claude Vision confidence < 0.6 → "La foto está un poco oscura. ¿Puedes intentar con más luz?" |
| Rosa says she doesn't have the receipt | System asks: "¿Tienes correo de confirmación, captura del pago, o el nombre exacto de la tienda?" → proceeds with lower confidence + flags for lawyer |
| Document is in English (e.g., product manual) | System extracts what it can; flags non-Spanish content for lawyer review |
| Rosa uploads the wrong document type | "Esto parece ser [X], pero yo necesito [Y]. ¿Tienes [Y]?" |
| Same fact appears in multiple documents with contradictory values | EvidenceCrossValidator flags both values + sources; asks Rosa to confirm; lawyer sees both |

---

## 7. Lawyer Command Center Backend

### Queue view

```
╔══════════════════════════════════════════════════════════════════════════╗
║  COMMAND CENTER — Clínica Jurídica ICESI          Abogado: Juan M.      ║
║  Casos pendientes: 4  |  Casos urgentes: 1  |  Hoy revisados: 7        ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  ⚡ URGENTE   #2026-0471  Rosa G.      Caso A  ⏰ 8 días para vencer    ║
║  ⚠ REVISAR   #2026-0468  Pedro R.     Caso B  ⚠ 1 flag crítico         ║
║  ✓ REVISAR   #2026-0465  María T.     Caso C  ✓ Sin flags               ║
║  ✓ BORRADOR  #2026-0460  Luis C.      Caso A  ✓ Borrador listo          ║
╚══════════════════════════════════════════════════════════════════════════╝
```

### Individual case view (Case #2026-0471)

```
╔══════════════════════════════════════════════════════════════════════════╗
║  CASO #2026-0471 — Rosa García — Tipo A (Producto Defectuoso)          ║
║  Estado: PENDIENTE REVISIÓN  |  Prioridad: URGENTE  |  347 días hábiles ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  RESUMEN IA ─────────────────────────────────────────────────────────── ║
║  Consumidora adquirió Samsung Galaxy A15 el 14/11/2025 en TechStore     ║
║  Cali S.A.S. (NIT 900.123.456-7, verificado RUES ✓) por COP 890.000    ║
║  en cuotas. Reporta apagado espontáneo desde la compra. Tienda rechazó  ║
║  verbalmente. Sin carta de rechazo escrita.                              ║
║  Ley aplicable: Art. 7 Ley 1480/2011 | Confianza: 91%                  ║
║                                                                          ║
║  FLAGS DE VALIDACIÓN ────────────────────────────────────────────────── ║
║  ⚠ ADVERTENCIA: Narrativa dice "hace dos meses" — factura dice          ║
║    14/11/2025 (5 meses). Rosa confirmó: fecha correcta es nov 2025.    ║
║  ✓ NIT verificado en RUES — empresa registrada activa.                  ║
║  ✓ Producto consistente en narrativa y factura.                         ║
║  ℹ Garantía declarada en factura: 6 meses. Art. 7 garantiza 1 año.     ║
║    Nota: garantía contractual no puede ser inferior a la legal.         ║
║  ℹ No hay carta de rechazo escrita — el caso sigue siendo válido.      ║
║                                                                          ║
║  DOCUMENTOS ANALIZADOS ──────────────────────────────────────────────── ║
║  [✓] Factura electrónica — TechStore Cali — 14/11/2025 — COP 890.000   ║
║  [✗] Tarjeta de garantía — NO SUBIDA — considerar solicitar            ║
║  [✗] Carta de rechazo — NO SUBIDA                                      ║
║                                                                          ║
║  VALIDACIÓN DEL BORRADOR ────────────────────────────────────────────── ║
║  Artículos citados: Art. 7, Art. 11, Art. 56 — todos verificados en KG ║
║  Campos SIC: 14/14 completados                                          ║
║  Citas inválidas removidas: 0                                           ║
║  Estado: BORRADOR VÁLIDO ✓                                              ║
║                                                                          ║
║  BORRADOR ───────────────────────────────────────────────────────────── ║
║  [VER VERSIÓN SIMPLE]  [VER VERSIÓN FORMAL SIC]  [EDITAR]              ║
║                                                                          ║
║  ASISTENTE IA ────────────────────────────────────────────────────────  ║
║  > Pregunta al asistente sobre este caso...                             ║
║                                                                          ║
║  ACCIONES ───────────────────────────────────────────────────────────── ║
║  [APROBAR Y ENVIAR A ROSA]  [EDITAR BORRADOR]  [SOLICITAR MÁS DOCS]   ║
║  [ESCALAR A SUPERVISOR]     [MARCAR SIN RECLAMACIÓN]  [AÑADIR NOTA]   ║
╚══════════════════════════════════════════════════════════════════════════╝
```

### Pipeline audit log (expandable by lawyer or jury)

```
AUDIT LOG — Case #2026-0471
────────────────────────────────────────────────────────────────────────
14:32:01  STAGE 0   IntakeInterviewer START
14:32:01  STAGE 0   Input type: voice | Whisper transcription: SUCCESS
14:32:15  STAGE 0   Turn 1 sent | Turn 1 received
14:32:28  STAGE 0   Turn 2 sent | Turn 2 received
14:32:41  STAGE 0   Turn 3 sent | Turn 3 received
14:32:54  STAGE 0   IntakeInterviewer COMPLETE | case_type_hypothesis: A (0.87)
14:32:54  STAGE 1   RAG pattern match: CASE_A_DEFECTIVE_PRODUCT_PHYSICAL_STORE (0.91)
14:32:54  STAGE 1   Retrieved: [Ley1480_Art7, Ley1480_Art11, Ley1480_Art56]
14:32:54  STAGE 1   Template loaded: SIC_FORM_GARANTIA_001
14:32:55  STAGE 2   Document request sent (factura)
14:36:12  STAGE 2   Document received: "factura_techstore.pdf" (1.2MB)
14:36:13  STAGE 3   pdfplumber extraction: 7/8 fields extracted
14:36:14  STAGE 3   Claude Vision: garantia_declarada extracted (confidence: 0.72 — flagged)
14:36:15  STAGE 3   RUES API call: NIT 900.123.456-7 → VERIFIED ACTIVE COMPANY
14:36:17  STAGE 4   Cross-validation: 1 WARNING (date), 2 INFO
14:36:18  STAGE 4   Clarification sent to Rosa re: date discrepancy
14:36:45  STAGE 4   Rosa confirmed: correct date is Nov 14, 2025
14:36:46  STAGE 5   LegalClassifier START | context: retrieved 3 articles
14:36:49  STAGE 5   claim_valid: TRUE | confidence: 0.91
14:36:49  STAGE 6   ComplaintDraftGenerator START
14:36:53  STAGE 6   Draft generated: 14/14 SIC fields filled
14:36:53  STAGE 7   DraftValidator: 0 invalid citations | 0 incomplete fields | PASS
14:36:54  STAGE 8   Case packet assembled | priority_score: 6 | queued as PENDING_REVIEW
14:36:54  STAGE 8   Rosa notified: reference #2026-0471
────────────────────────────────────────────────────────────────────────
Total pipeline time: 4 min 53 sec (including Rosa's response wait time)
Agent processing time (excluding Rosa wait): 28 sec
```

---

## 8. End-to-End Example: Rosa's Case from First Message to SIC Delivery

```
14:32  ROSA opens the app on her phone.
       She taps the microphone and speaks:
       "Bueno, yo compré un celular hace como dos meses en una tienda aquí
        en Cali, y el teléfono desde que lo traje se apaga solo. Fui a la
        tienda y me dijeron que eso no era problema de ellos."

14:32  SYSTEM (Whisper → IntakeInterviewer):
       Transcribes voice → detects Spanish → routes to IntakeInterviewer.
       
       Agent responds in plain Colombian Spanish:
       "Hola, entendí lo que pasó. Para ayudarte mejor, ¿compraste el celular
        en la tienda directamente, o lo pediste por internet?"

14:32  ROSA: "En la tienda, en persona."

14:33  SYSTEM: "¿Recuerdas qué defecto tiene el celular? ¿Qué es lo que
        le pasa exactamente?"

14:33  ROSA: "Se apaga solo, como cada rato. A veces no prende tampoco."

14:33  SYSTEM: "¿Cuándo compraste el celular, aproximadamente?"

14:33  ROSA: "Hace como dos meses."

14:34  SYSTEM: "Cuando fuiste a la tienda a reclamar, ¿qué te dijeron?
        ¿Te dieron algo por escrito, o fue solo de palabra?"

14:34  ROSA: "Solo de palabra. Me dijeron que el teléfono no tenía garantía
        o algo así."

14:34  SYSTEM: "Entendido. Con lo que me contaste, parece que tienes derecho
        a pedir que te arreglen o cambien el celular. Para confirmar eso,
        necesito ver tu factura o recibo de compra.
        
        ¿Tienes la factura? Puedes tomarle una foto ahora mismo."

14:35  ROSA: [Takes photo of invoice with her phone and uploads it]

14:36  SYSTEM (pdfplumber / Claude Vision):
       Extracts: TechStore Cali S.A.S. | NIT 900.123.456-7 | Nov 14, 2025 |
                 Samsung Galaxy A15 | COP 890.000 | cuotas | garantía: 6 meses
       RUES API: NIT 900.123.456-7 → VERIFIED (empresa activa, sector comercio)

14:36  SYSTEM (EvidenceCrossValidator):
       Detects: Rosa said "hace dos meses" but invoice says November 14, 2025.
       
       Sends to Rosa:
       "Vi tu factura. Dice que compraste el celular el 14 de noviembre de 2025.
        Antes me dijiste 'hace como dos meses', pero noviembre fue hace más de
        cuatro meses. ¿Cuál es la fecha correcta: la del recibo (14 nov 2025)
        o fue en otra fecha?"

14:36  ROSA: "Ah sí, fue en noviembre, me confundí."

14:37  SYSTEM (LegalClassifier + RAG):
       Retrieves: CasePattern A → Art. 7, Art. 11 | SIC_FORM_GARANTIA_001
       
       Evaluates:
         relación de consumo: ✓ (RUES verified commercial seller)
         compra a proveedor: ✓ (factura electrónica)
         dentro de garantía: ✓ (purchase Nov 2025, defect ongoing, < 1 year)
         vicio en el bien: ✓ (spontaneous shutdown = functional defect)
       
       Result: CLAIM VALID | confidence: 91%
       Note: Invoice states 6-month warranty, but Art. 7 guarantees 1 year minimum.
       Rosa's statutory right is STRONGER than what the store told her.

14:37  SYSTEM (ComplaintDraftGenerator + RAG):
       Fills all 14 SIC form fields using:
         - Validated facts from invoice + confirmed narrative
         - SIC_FORM_GARANTIA_001 template from KG
         - Art. 7 and Art. 11 text from KG
         - Sample pretension language from KG

14:38  SYSTEM (DraftValidator):
       Checks: Art. 7 in KG ✓ | Art. 11 in KG ✓ | Art. 56 in KG ✓
       All 14 fields present ✓
       PASS.

14:38  SYSTEM → Rosa:
       "¡Listo! Tu reclamación fue preparada.
        
        Tienes derecho a pedir que te arreglen el celular, te lo cambien,
        o te devuelvan la plata — aunque la tienda te haya dicho que no
        tenías garantía, la ley dice que sí tienes derecho por 1 año.
        
        Un abogado va a revisar tu caso antes de que lo envíes.
        Tu número de referencia es #2026-0471.
        Te avisamos en las próximas horas."

14:38  CASE enters lawyer queue as PENDING_REVIEW | Priority: MEDIUM

────────────────────────────────────────────────────────────────────────

15:10  LAWYER (Juan M.) opens the dashboard.
       Sees case #2026-0471 in queue.
       
       Reviews:
         - AI summary: product defect, store refusal, Art. 7 applicable ✓
         - Validation flags: 1 warning (date — resolved by Rosa), 2 info
         - Documents: invoice parsed ✓ | no warranty card | no denial letter
         - Draft validation: 14/14 fields ✓ | 0 invalid citations ✓
         
       Lawyer asks the AI assistant:
       > "La factura dice garantía de 6 meses. ¿Eso afecta el caso?"
       
       AI assistant responds:
       "No. El artículo 7, parágrafo 3 de la Ley 1480/2011 establece
        que la garantía legal mínima no puede ser reducida ni excluida por
        acuerdo entre las partes. La garantía de 6 meses declarada en la
        factura es contractual y no tiene efecto contra la garantía legal.
        El plazo de 1 año del Art. 7 aplica plenamente."
       
       Lawyer: satisfied. Minor edit to the first HECHO paragraph — adds
       "el bien fue adquirido para uso personal" (strengthens relación de consumo).
       
       Lawyer clicks [APROBAR Y ENVIAR A ROSA].

15:12  SYSTEM generates PDF:
         - Final formal complaint (all 14 fields, lawyer-edited)
         - Attachments: invoice PDF
         - Case reference: #2026-0471

15:12  SYSTEM → Rosa (WhatsApp-style notification):
       "Hola Rosa, tu reclamación ante la SIC ya está lista.
        
        Un abogado la revisó y aprobó. Aquí tienes lo que necesitas:
        
        📄 [DESCARGAR RECLAMACIÓN SIC — PDF]
        
        ¿Cómo la radicas?
        
        POR INTERNET (más rápido):
        → Ve a www.sic.gov.co
        → Busca 'Servicios al ciudadano' → 'Quejas'
        → Sube el PDF que te enviamos y una foto de tu cédula
        
        EN PERSONA en Cali:
        → Delegatura SIC Cali: Cra. 4 # 7-36
        → Lunes a viernes, 8am a 5pm
        → Lleva: el PDF impreso, tu cédula, y el recibo de compra
        
        IMPORTANTE: Tienes hasta el 14 de noviembre de 2026 para radicar.
        
        Si tienes preguntas, responde a este mensaje."

════════════════════════════════════════════════════════════════════════
Total elapsed time from Rosa's first message to delivery: ~43 minutes
  → 5 min: Rosa's conversation with the system
  → 32 min: lawyer queue wait
  → 6 min: lawyer review, query, and edit
  → 1 min: PDF generation and delivery
════════════════════════════════════════════════════════════════════════
```

---

## 9. Weaknesses and Risks

### Technical weaknesses

| Weakness | Severity | Mitigation |
|---|---|---|
| **Knowledge graph construction time** | High | Must pre-build before the 24h sprint. Plan: build KG in the days before the hackathon. During the sprint, only load and query it. |
| **PDF quality variance** | Medium | Colombian invoices vary enormously in format. pdfplumber handles structured PDFs well; unstructured ones need Claude Vision fallback. Some invoices may require manual entry. |
| **Whisper accuracy with Colombian regional accents** | Medium | Tested on standard Colombian Spanish. Caleño or coastal accents may reduce accuracy. Mitigation: show transcription to Rosa for confirmation before processing. |
| **RUES API availability** | Low-Medium | RUES is a government API that can be slow or unavailable. Mitigation: build a cache layer; if RUES is down, flag for lawyer manual verification instead of blocking. |
| **Knowledge graph not covering edge cases** | Medium | Law 1480 has 70+ articles. The pre-built KG covers the most common 15–20. Edge cases (e.g., digital goods, marketplace platforms) may not be covered. Mitigation: DeadEndNavigator routes uncovered cases to "consult a lawyer." |
| **Multi-document cross-validation complexity** | Medium | If Rosa uploads 3+ documents with partially conflicting data, the EvidenceCrossValidator may produce ambiguous flags. Mitigation: limit to 2–3 documents per case in the prototype; flag anything beyond that for lawyer review. |

### Legal/design weaknesses

| Weakness | Severity | Mitigation |
|---|---|---|
| **System cannot replace the lawyer's legal judgment** | By design | The system explicitly does not file anything. Lawyer approval is mandatory. This is a feature, not a weakness — but it means the system is not fully autonomous. |
| **Informal oral testimony without written denial** | Medium | A case where Rosa has only her word (no documents) has lower evidentiary weight. The system flags this clearly but still drafts the complaint — the claim is still legally valid. |
| **Deadline errors** | High | If the system miscalculates the statute of limitations deadline, a case could expire. Mitigation: deadline calculation is deterministic (Python, not LLM), and the lawyer sees the calculation + the source rule. |
| **LLM generating subtly wrong legal language** | Medium | Even with RAG, Claude may rephrase retrieved legal language in ways that subtly change meaning. Mitigation: the DraftValidator checks article citations; lawyer reviews full draft. The "sample language" in the KG provides anchor phrases. |

---

## 10. Copiability Analysis — What Other Teams Will Likely Do

### What nearly every team will build

Based on the available tools and the challenge brief, most teams will likely build:

| Likely element | Probability |
|---|---|
| A conversational chatbot for Rosa | Very high |
| Claude API as the main LLM | High |
| LangChain for orchestration | High |
| A basic complaint draft generator | High |
| Voice input (Whisper) | Medium |
| PDF upload + text extraction | Medium |
| vLex API for article lookup | Medium |
| Some form of dual-layer output (plain + formal) | Medium |
| A lawyer review step | Low-Medium |
| Knowledge graph (Neo4j) | Low |
| RAG with LlamaIndex | Low |
| Document cross-validation | Very low |
| Automated case queue with priority scoring | Very low |
| Auditable pipeline log | Low |

### What this proposal has that almost no other team will have

1. **The knowledge graph with SIC form templates encoded as nodes.** Building this requires legal domain knowledge + graph modeling skills + time investment. Most teams will use vLex as a lookup tool, not build a structured graph of the law.

2. **The DraftValidator post-generation check.** A Python script that checks every article citation against a known-valid set. This directly solves the "no invented articles" requirement. Most teams will rely on prompt instructions alone ("don't make up articles") — which is less reliable.

3. **The DocumentRequestPlanner that reasons about what documents to request.** Most teams will either ask Rosa to upload everything upfront, or ask generic questions. The inference step ("from your narrative, we think you need *this specific document* because *this specific legal reason*") is a distinct behavioral layer.

4. **The EvidenceCrossValidator.** Comparing narrative to document data is a separate processing step. Most teams will not build this — they will pass the document content directly to the draft generator, missing discrepancies.

5. **The lawyer Command Center as a separate, functional backend with a case queue, AI assistant, and priority scoring.** Most teams will focus entirely on Rosa's side. The lawyer backend is the "second worker" angle that makes this qualitatively different.

---

## 11. Differentiators — What Makes This Architecture Distinctively Hard to Copy

### Differentiator 1: The knowledge graph IS the legal brain

Most systems use the LLM as the legal brain and documents as context. This system uses the **knowledge graph as the legal brain** and the LLM as the **language renderer.** The LLM fills in templates and writes prose. The legal reasoning happens in the graph — structured, auditable, and traceable to specific nodes.

This means: if the jury asks "why did the system say Art. 7 applies?", the answer is not "because the LLM said so" — it is "because the case facts matched the CasePattern node CASE_A_DEFECTIVE_PRODUCT, which is connected to Ley1480_Art7 with condition relacion_de_consumo, and that condition was verified by the RUES API call at 14:36:15." That is a fundamentally different answer — and a fundamentally harder one to copy in 24 hours.

### Differentiator 2: Case reuse is structurally built in

The challenge says cases repeat. Most teams will handle this at the prompt level ("here are examples of past cases"). This system handles it at the architecture level: **the CasePattern node stores the proven structure for each repeating case type**, and every new case retrieves and fills that structure rather than generating from scratch. This is faster, more consistent, and more legally reliable.

### Differentiator 3: The document request is intelligent, not generic

Most teams: "Please upload your documents."
This system: "Based on what you said, you need a purchase receipt. Here's why. Here's how to get it if you don't have it. Here's what happens if you can't find it."

The DocumentRequestPlanner has legal knowledge (from the KG) about what each document proves and why it matters for each case type. This is a qualitatively different user experience — and a qualitatively different legal product.

### Differentiator 4: Two functional surfaces, not one

The challenge is framed around Rosa, but the **institutional user** (SIC supervisor) and the **secondary user** (law clinic lawyer) are explicitly in the rubric. Most teams will build one interface (Rosa's chat) and mention the other users in the pitch.

This proposal builds **two fully functional interfaces** with different information architectures: Rosa's conversational flow and the lawyer's Command Center. The Command Center is not a demo screen — it is a functional case management system with queue, AI assistant, audit log, and action buttons. The lawyer is a real user of this system, not a footnote.

### Differentiator 5: The pipeline audit log addresses the jury's live question

The challenge explicitly states: *"El árbol de decisión legal debe ser auditable: el jurado puede pedir ver por qué el sistema dijo que aplica o no aplica la Ley 1480."*

The pipeline audit log (Stage 8 output) directly answers this. The jury can see every decision, every timestamp, every confidence score, every retrieved node. The DraftValidator shows which articles were in the retrieved context and confirms none were invented. This is not just a feature — it is a direct response to the explicit requirement, delivered as a functional artifact, not a verbal answer.

---

## 12. Challenge Requirements Compliance Check

### Technical restrictions

| Restriction | Status | Evidence |
|---|---|---|
| At least one LLM agent in the pipeline (not a single prompt) | ✓ COMPLIANT | 7 distinct agents: IntakeInterviewer, DocumentRequestPlanner, DocumentParser, EvidenceCrossValidator, LegalClassifier, ComplaintDraftGenerator, DeadEndNavigator |
| Auditable legal decision tree — jury can ask why Law 1480 applies or not | ✓ COMPLIANT | Pipeline audit log (Stage 8) + KG traversal path + confidence scores per classification decision |
| Draft cannot contain articles or rights not in Colombian law | ✓ COMPLIANT | DraftValidator (Stage 7): deterministic Python check strips any citation not in the KG's verified article set before the draft is approved |
| Demo must work with provided PDFs, not team's own data | ✓ COMPLIANT | DocumentParser + Claude Vision handle arbitrary PDFs. DocumentSchema in KG maps to common Colombian invoice formats. System does not depend on pre-loaded team data. |

### Mission outputs

| Required output | Status | Implementation |
|---|---|---|
| (1) Clear legal diagnosis — right to file and under which law | ✓ COMPLIANT | LegalClassifier Stage 5: outputs claim_valid, applicable_articles, confidence per article, uncertainty_notes |
| (2) Step-by-step SIC procedure guide adapted to the specific case | ✓ COMPLIANT | Stage 10: procedural guide generated per case type, with SIC office addresses, online filing link, required documents, and deadline |
| (3) Formal complaint draft in correct legal language, ready to file | ✓ COMPLIANT | ComplaintDraftGenerator Stage 6: all 14 SIC form fields filled using KG templates + validated facts |

### Three case types

| Case type | Status | Evidence |
|---|---|---|
| (A) Defective product — physical store | ✓ COMPLIANT | CasePattern node CASE_A in KG; DocumentSchema for factura_electronica; Art. 7 + Art. 11 templates |
| (B) Unauthorized financial charge | ✓ COMPLIANT | CasePattern node CASE_B in KG; DocumentSchema for estado_de_cuenta_bancario; applicable articles pre-loaded |
| (C) Telecom service breach | ✓ COMPLIANT | CasePattern node CASE_C in KG; DocumentSchema for factura_telecomunicaciones + contrato_servicio |
| Surprise 4th case (jury-proposed) | ✓ PREPARED | If case matches a KG pattern: routed normally. If outside KG coverage: DeadEndNavigator explains limitation and routes to lawyer. Audit log shows the KG returned no match. This is the correct, honest behavior — not a failure. |

### Technical knots (Nudos)

| Nudo | Status | Implementation |
|---|---|---|
| Nudo 1: Extract legal facts from informal language | ✓ COMPLIANT | IntakeInterviewer maps "se apaga solo" → defect_type. LegalClassifier maps defect_type to Art. 7 using KG edges. |
| Nudo 2: Decision tree + explicit uncertainty | ✓ COMPLIANT | LegalClassifier returns claim_valid=false with reason when conditions not met. DeadEndNavigator explains in plain language. KG structurally prevents inventing rights (only nodes that exist can be traversed). |
| Nudo 3: Dual-layer output | ✓ COMPLIANT | ComplaintDraftGenerator produces two distinct outputs from the same fact set: plain summary (~200 words for Rosa) and formal draft (all 14 SIC fields in technical language). |
| Nudo 4: Equity across input quality | ✓ COMPLIANT | IntakeInterviewer normalizes informal input before any downstream processing. All agents operate on the normalized intake summary, not on Rosa's raw words. The pipeline produces the same quality draft regardless of whether Rosa spoke informally or typed formally. |

### Deliverables

| Deliverable | Status | Notes |
|---|---|---|
| Public GitHub repo, reproducible in < 15 min | ✓ ACHIEVABLE | Standard containerized Python app on Cloud Run. Docker-compose for local run. README with setup steps. |
| Live demo with 3 sample cases | ✓ ACHIEVABLE | System is document-agnostic. Sample PDFs loaded as input → pipeline runs. |
| 4th surprise case from jury | ✓ ACHIEVABLE | System routes to KG match or DeadEndNavigator. Either way, it responds correctly. |
| Slide deck in English (max 6 slides) | — | Not in scope of this document. |
| Prepared answer to "what does the system do when the case has no clear answer?" | ✓ READY | DeadEndNavigator path: explains in plain language why Law 1480 does not apply, offers alternatives (Defensoría, mediation, civil court), routes to lawyer queue where lawyer can override. The system never invents a right; it never leaves Rosa with nothing. |

---

*Proposal 1 Deep Specification — Version 2026-04*
*Semillero LegalTech — Universidad ICESI*
