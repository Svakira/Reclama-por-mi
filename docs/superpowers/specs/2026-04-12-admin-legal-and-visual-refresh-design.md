# JusticIA Visual + Admin + Legal Refresh Design

Date: 2026-04-12
Owner: OpenCode + Semillero LegalTech ICESI
Scope: Public `/app`, admin `/admin` and `/admin/cases/:caseId`, legal draft quality, analysis traceability, evidence packaging, notification behavior.

## 1) Goals

1. Re-apply and stabilize a polished visual language based on the provided references, using a blue palette and preserving current app architecture.
2. Improve lawyer operations in admin with searchable queues, functional sidebar navigation, and a dedicated data explorer for stored documents.
3. Raise legal output quality in SIC drafts (detail, quantia precision, stronger legal grounds with relevant excerpts).
4. Increase explainability by exposing expandable article-based AI analysis with per-article confidence.
5. Package final documents with supporting evidence bundled into the generated PDF flow.
6. Ensure lawyer claim decisions trigger WhatsApp updates only when user notification preference is enabled.

## 2) Non-Goals

1. No framework migration (keep React + existing FastAPI architecture).
2. No replacement of Firestore storage model in this cycle.
3. No redesign of authentication flow beyond UI-level consistency.

## 3) Design Principles

1. Keep existing routes/components/APIs where possible; apply visual and behavioral upgrades in place.
2. Separate visual refresh from legal engine refactors to avoid mixed regressions.
3. Deterministic structure for legal output where precision is required (quantia composition, formatting, appendix ordering).
4. Explainability data must be machine-readable first, then rendered in expandable UI blocks.

## 4) Phase Plan

### Phase A: Visual refresh (public + admin shells)

#### A.1 Public `/app`

- Keep route/component entrypoint (`ChatView`) but restructure view composition to match reference hierarchy:
  - Header/Nav
  - Hero split block
  - Steps section
  - Benefits section
  - Chat section
  - CTA strip
  - Footer
- Typography:
  - Primary UI text: `Plus Jakarta Sans`
  - Display headings (public marketing sections): `DM Serif Display`
- Palette tokens move to blue-first branding while preserving contrast and accessibility:
  - primary, primary-light, primary-dark, accent, neutral scale, success, warning, danger.
- Keep functional chat behavior intact (session start, send message, upload flow).

#### A.2 Admin shell `/admin`

- Keep current admin route structure, but update layout and components to visual reference:
  - Fixed dark sidebar
  - Cleaner metric cards
  - Professional data table styling
  - Consistent action button hierarchy
- Remove emoji-based iconography from critical actions.

#### A.3 Case detail `/admin/cases/:caseId`

- Keep tab model but restyle to reference:
  - Structured case header with status and action buttons
  - Core case metadata strip
  - Main-left content tabs + right insights/timeline cards

### Phase B: Admin operability upgrades

#### B.1 Queue search and filtering

- Add input search to queue page with local filter over fetched cases:
  - `case_id`
  - `consumer_name`
  - `status`
  - `case_type`
- Keep current sort by priority as default; allow quick select sort options if needed.

#### B.2 Functional sidebar

- Expand sidebar nav from a single operational link to stable sections:
  - Queue
  - Data Explorer
  - (Optional placeholder) Reports/Settings disabled-state until implemented.
- Active route highlighting and reliable navigation behavior.

#### B.3 New Data Explorer section

- New admin route/page for searching stored document records and metadata.
- Data columns:
  - file name
  - case id
  - consumer name
  - inferred document type
  - confidence
  - upload timestamp
- Search by consumer/file/doc-type terms.
- Backend endpoint addition (read-only) to aggregate from case/draft/document metadata sources.

### Phase C: Legal/document engine quality

#### C.1 SIC draft quality expansion

- Upgrade draft generation prompt/template contract to enforce richer legal structure:
  - broader factual narrative
  - chronology and evidentiary linkage
  - explicit pretensions and legal rationale
- Add quantia decomposition format:
  - line items by concept
  - subtotal and total
  - value in numbers and words.
- Add stronger legal grounds:
  - relevant article excerpts
  - explicit mapping article -> fact.

#### C.2 Expandable AI analysis by article

- Extend legal classification payload with `article_analysis` list:
  - `article_id`
  - `confidence_by_article`
  - `relevant_excerpt`
  - `reasoning_summary`
- Render in case detail analysis tab with expandable accordion cards.

#### C.3 PDF final with evidence appendix

- Build deterministic final package generator:
  - cover + final draft
  - annex index
  - appended evidence docs/images normalized for PDF merge.
- Persist generated package path and expose for admin preview/download.

#### C.4 Lawyer decision notifications

- On claim decisions (`OVERRIDE_CLAIM_VALID`, `CONFIRM_NO_CLAIM`):
  - notify through existing notify channel only when user preference/phone registration is present.
- Remove emojis from corresponding decision buttons and labels.

## 5) Backend changes (target areas)

1. `backend/agents/complaint_draft_generator.py`
   - enforce richer sections, quantia structure, legal excerpt integration.
2. `backend/agents/legal_classifier.py`
   - extend output schema with per-article analysis list.
3. `backend/agents/case_packager.py`
   - store additional analysis payload and packaged evidence metadata.
4. `backend/api/cases_routes.py` / new admin data endpoint module
   - add read endpoint for Data Explorer.
5. `backend/api/lawyer_routes.py` + `backend/api/notify_routes.py`
   - trigger decision-based notifications with preference checks.
6. PDF packaging utility module (new): merge main draft + attachments.

## 6) Frontend changes (target areas)

1. `frontend/src/styles/tokens.ts`
   - define blue visual system tokens and typography mapping.
2. `frontend/src/app/ChatView.tsx`
   - public landing/chat structure matching visual reference.
3. `frontend/src/components/Navbar.tsx`, `frontend/src/components/Footer.tsx`
   - restyle and align with reference language.
4. `frontend/src/admin/AdminLayout.tsx`, `frontend/src/components/Sidebar.tsx`
   - updated admin shell and route nav.
5. `frontend/src/admin/Queue.tsx`
   - add search input and polished table/filters.
6. `frontend/src/admin/CaseDetail.tsx`
   - redesign layout; add expandable article analysis; remove emoji actions.
7. New `frontend/src/admin/DataExplorer.tsx` + route wiring.

## 7) Data contract updates

### Legal classifier output (extended)

```json
{
  "scenario": "A|B|C|...",
  "claim_valid": true,
  "confidence": 0.9,
  "applicable_articles": ["ART_..."],
  "article_analysis": [
    {
      "article_id": "ART_7_LEY_1480",
      "confidence_by_article": 0.86,
      "relevant_excerpt": "...",
      "reasoning_summary": "..."
    }
  ]
}
```

### Draft quantia structure (embedded in draft metadata)

```json
{
  "quantia": {
    "items": [
      {"concept": "Devolucion valor pagado", "value_number": 1200000, "value_words": "un millon doscientos mil pesos"}
    ],
    "total_number": 1200000,
    "total_words": "un millon doscientos mil pesos"
  }
}
```

## 8) Risks and mitigations

1. Visual regression risk across pages
   - Mitigation: phase-by-phase rollout and route-level verification screenshots.
2. Token/cost increase from richer legal prompts
   - Mitigation: hybrid deterministic scaffolding + focused generation windows.
3. PDF merge failures with mixed file types
   - Mitigation: normalize non-PDF evidence into PDF before merge and fail with clear per-file diagnostics.
4. Notification duplication
   - Mitigation: idempotent event key (`case_id + decision + date-window`) before send.

## 9) Verification strategy

1. Frontend build passes with all route pages.
2. Admin flows:
   - queue search/filter
   - case detail actions
   - data explorer query.
3. Legal generation checks:
   - quantia includes concepts and number+words formatting
   - legal grounds include excerpts
   - analysis tab has per-article confidence entries.
4. Document package checks:
   - generated PDF includes annex index + evidence pages.
5. Notification checks:
   - decision events notify only when user opted in.

## 10) Acceptance criteria

1. Public and admin UIs match reference style language adapted to blue palette.
2. Queue has working search input and sidebar links are functional.
3. Data Explorer exists and supports search by file/consumer/doc type.
4. SIC draft quality visibly improves in breadth and legal precision.
5. Quantia is explicit by concept and in numbers/words.
6. Analysis tab provides expandable article evidence with confidence.
7. Final PDF package includes combined evidence appendices.
8. Lawyer claim decision buttons are emoji-free and can trigger preference-aware WhatsApp updates.
