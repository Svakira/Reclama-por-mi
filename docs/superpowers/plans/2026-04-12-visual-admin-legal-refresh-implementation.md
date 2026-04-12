# Visual + Admin + Legal Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the public and admin UX to the approved visual reference (blue palette), while upgrading legal draft quality, article-level AI explainability, document packaging, and admin operational tooling.

**Architecture:** Keep current React + FastAPI structure, implement UI updates in-place on existing routes/components, and add focused backend extensions for legal output and admin data access. Separate deterministic legal formatting (quantia + annex structure) from LLM-generated prose to improve consistency and auditability.

**Tech Stack:** React + TypeScript + Vite, FastAPI + Pydantic + Firestore, Groq LLM integrations, ReportLab/PyMuPDF for PDF packaging.

---

### Task 1: Visual Foundation (Blue System + Typography)

**Files:**
- Modify: `frontend/src/styles/tokens.ts`
- Modify: `frontend/src/main.tsx`
- Test: `frontend` build output

- [ ] **Step 1: Write the failing UI token usage test (type-level smoke)**

```ts
// Add to a temporary compile check in main.tsx usage:
import { colors, typography } from './styles/tokens'
void colors.primary
void typography.display
```

- [ ] **Step 2: Run frontend type/build to verify it fails first**

Run: `cd frontend && npm run build`
Expected: FAIL if `typography` is not yet exported.

- [ ] **Step 3: Implement token and typography system**

```ts
// frontend/src/styles/tokens.ts
export const colors = {
  primary: '#1F4E79',
  primaryLight: '#2D6A9F',
  primaryDark: '#163754',
  accent: '#4F86C6',
  neutral50: '#F5F7FA',
  neutral100: '#E7ECF2',
  neutral200: '#D6DDE7',
  neutral600: '#6B7280',
  neutral800: '#374151',
  text: '#1F2937',
  bg: '#F5F7FA',
  surface: '#FFFFFF',
  border: '#D6DDE7',
  success: '#2E7D32',
  warning: '#B7791F',
  danger: '#B42318',
}

export const typography = {
  body: "'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
  display: "'DM Serif Display', Georgia, serif",
}

export const shadows = {
  card: '0 2px 12px rgba(22,55,84,0.08)',
  modal: '0 8px 32px rgba(22,55,84,0.16)',
}
```

- [ ] **Step 4: Load Google Fonts and global body font**

```ts
// frontend/src/main.tsx
import './styles/global.css'
```

```css
/* frontend/src/styles/global.css */
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=DM+Serif+Display:wght@400&display=swap');

html, body, #root {
  height: 100%;
}

body {
  margin: 0;
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: #F5F7FA;
  color: #1F2937;
}
```

- [ ] **Step 5: Run build and commit**

Run: `cd frontend && npm run build`
Expected: PASS.

```bash
git add frontend/src/styles/tokens.ts frontend/src/main.tsx frontend/src/styles/global.css
git commit -m "style: add blue design tokens and typography foundation"
```

### Task 2: Public `/app` Visual Reference Implementation

**Files:**
- Modify: `frontend/src/app/ChatView.tsx`
- Modify: `frontend/src/components/Navbar.tsx`
- Modify: `frontend/src/components/Footer.tsx`
- Test: `/app` visual and chat behavior

- [ ] **Step 1: Write failing behavior checks in browser note**

```md
Expected failing checks before implementation:
1) Hero does not match reference hierarchy.
2) Steps/benefits/CTA sections missing.
3) Chat block lacks reference layout styling.
```

- [ ] **Step 2: Implement reference-based layout in `ChatView`**

```tsx
// Keep existing stateful chat logic; replace page layout tree with:
<div>
  <Navbar links={[...]} />
  <section>{/* Hero split: headline + feature box */}</section>
  <section>{/* Steps grid (4 cards) */}</section>
  <section>{/* Benefits grid (6 cards) */}</section>
  <section>{/* Chat container + live messages + input */}</section>
  <section>{/* CTA strip */}</section>
  <Footer />
</div>
```

- [ ] **Step 3: Keep chat interaction semantics unchanged**

```tsx
// Preserve these handlers and call points:
startSession()
sendMessage()
handleFileUpload()
```

- [ ] **Step 4: Implement nav/footer style alignment**

```tsx
// Navbar: white sticky header, dark text links, active accent underline.
// Footer: 4-column informational footer + bottom legal strip.
```

- [ ] **Step 5: Run build and commit**

Run: `cd frontend && npm run build`
Expected: PASS and `/app` still functional.

```bash
git add frontend/src/app/ChatView.tsx frontend/src/components/Navbar.tsx frontend/src/components/Footer.tsx
git commit -m "feat: apply approved visual reference to public app page"
```

### Task 3: Admin Shell and Route Expansion

**Files:**
- Modify: `frontend/src/components/Sidebar.tsx`
- Modify: `frontend/src/admin/AdminLayout.tsx`
- Modify: `frontend/src/main.tsx`
- Create: `frontend/src/admin/DataExplorer.tsx`
- Test: admin navigation behavior

- [ ] **Step 1: Add new route and page wiring (failing first)**

```tsx
// frontend/src/main.tsx (add)
<Route path="/admin/data" element={<PrivateRoute><DataExplorer /></PrivateRoute>} />
```

- [ ] **Step 2: Run build to verify fail if component missing**

Run: `cd frontend && npm run build`
Expected: FAIL `DataExplorer` not found.

- [ ] **Step 3: Create `DataExplorer.tsx` scaffold**

```tsx
export default function DataExplorer() {
  return <AdminLayout><div>Explorador de datos</div></AdminLayout>
}
```

- [ ] **Step 4: Implement sidebar sections and functional links**

```tsx
// Sidebar nav items:
// - /admin (Cola de revision)
// - /admin/data (Datos)
// - disabled placeholders for future reports/settings
```

- [ ] **Step 5: Run build and commit**

Run: `cd frontend && npm run build`
Expected: PASS.

```bash
git add frontend/src/components/Sidebar.tsx frontend/src/admin/AdminLayout.tsx frontend/src/admin/DataExplorer.tsx frontend/src/main.tsx
git commit -m "feat: add functional admin sidebar routes and data explorer page"
```

### Task 4: Queue Search and Professional Table Interaction

**Files:**
- Modify: `frontend/src/admin/Queue.tsx`
- Test: `frontend/src/admin/Queue.tsx` behavior manually

- [ ] **Step 1: Add failing expectation comments**

```md
Search input should filter rows by case id, consumer, status, scenario.
```

- [ ] **Step 2: Implement local search state and filtered list**

```tsx
const [query, setQuery] = useState('')
const filteredCases = cases.filter((c) => {
  const q = query.toLowerCase().trim()
  if (!q) return true
  return [c.case_id, c.consumer_name, c.status, c.case_type]
    .join(' ')
    .toLowerCase()
    .includes(q)
})
```

- [ ] **Step 3: Add search input UI in filters row**

```tsx
<input
  value={query}
  onChange={(e) => setQuery(e.target.value)}
  placeholder="Buscar por caso, consumidor, estado o escenario"
/>
```

- [ ] **Step 4: Replace table map source with `filteredCases`**

```tsx
{filteredCases.map((c) => (...))}
```

- [ ] **Step 5: Build and commit**

Run: `cd frontend && npm run build`
Expected: PASS.

```bash
git add frontend/src/admin/Queue.tsx
git commit -m "feat: add admin queue search and improved table filtering"
```

### Task 5: Case Detail Redesign + Expandable Article Analysis + Emoji Removal

**Files:**
- Modify: `frontend/src/admin/CaseDetail.tsx`
- Test: case detail interaction

- [ ] **Step 1: Remove emoji labels from action buttons**

```tsx
// Before: "✓ Reactivar como valido", "✗ Confirmar NO CLAIM"
// After:  "Reactivar como valido", "Confirmar NO CLAIM"
```

- [ ] **Step 2: Add expandable article analysis accordion**

```tsx
const [expandedArticle, setExpandedArticle] = useState<string | null>(null)
const articleAnalysis = caseData.legal_classification?.article_analysis || []

{articleAnalysis.map((a) => (
  <div key={a.article_id}>
    <button onClick={() => setExpandedArticle(expandedArticle === a.article_id ? null : a.article_id)}>
      {a.article_id} - Confianza {Math.round((a.confidence_by_article || 0) * 100)}%
    </button>
    {expandedArticle === a.article_id && (
      <div>
        <p>{a.relevant_excerpt}</p>
        <p>{a.reasoning_summary}</p>
      </div>
    )}
  </div>
))}
```

- [ ] **Step 3: Restyle page to approved visual language**

```tsx
// Keep existing tabs and API actions, update spacing, card hierarchy,
// right-side progress/timeline cards, and header action grouping.
```

- [ ] **Step 4: Build and commit**

Run: `cd frontend && npm run build`
Expected: PASS.

```bash
git add frontend/src/admin/CaseDetail.tsx
git commit -m "feat: redesign case detail with expandable article analysis and professional actions"
```

### Task 6: Safe-by-Default Agent and Pipeline Logs

**Files:**
- Modify: `backend/api/pipeline_routes.py`
- Modify: `backend/agents/groq_client.py`
- Modify: `backend/agents/intake_interviewer.py`
- Modify: `backend/agents/document_parser.py`
- Modify: `backend/agents/evidence_cross_validator.py`
- Modify: `backend/agents/legal_classifier.py`
- Modify: `backend/agents/complaint_draft_generator.py`
- Modify: `backend/agents/draft_validator.py`
- Modify: `backend/agents/case_packager.py`
- Test: backend compile + manual logs

- [ ] **Step 1: Add `DEBUG_VERBOSE` gate in pipeline logger**

```py
DEBUG_VERBOSE = os.getenv("DEBUG_VERBOSE", "false").lower() in {"1", "true", "yes", "on"}
```

- [ ] **Step 2: Add redacted summarizer and structured logger helper**

```py
def _pipeline_log(session_id: str, stage: str, event: str, **payload):
    ...
```

- [ ] **Step 3: Instrument stage transitions (start/message/upload/stage3-8)**

```py
_pipeline_log(session_id, "STAGE_5_LegalClassifier", "legal.classification.completed", ...)
```

- [ ] **Step 4: Add concise agent-level start/done logs in each agent module**

```py
print("[AGENT][LegalClassifier] done scenario=... claim_valid=...")
```

- [ ] **Step 5: Compile-check and commit**

Run: `python3 -m py_compile backend/api/pipeline_routes.py backend/agents/*.py`
Expected: PASS.

```bash
git add backend/api/pipeline_routes.py backend/agents/groq_client.py backend/agents/intake_interviewer.py backend/agents/document_parser.py backend/agents/evidence_cross_validator.py backend/agents/legal_classifier.py backend/agents/complaint_draft_generator.py backend/agents/draft_validator.py backend/agents/case_packager.py
git commit -m "feat: add safe structured pipeline and agent observability logs"
```

### Task 7: SIC Draft Quality Upgrade (Quantia + Legal Excerpts)

**Files:**
- Modify: `backend/agents/complaint_draft_generator.py`
- Create: `backend/utils/money_format.py`
- Create: `backend/tests/test_money_format.py`
- Test: draft generation + helper tests

- [ ] **Step 1: Write failing tests for number-to-words COP formatting**

```py
def test_cop_words_simple():
    assert number_to_cop_words(1200000) == "un millon doscientos mil pesos colombianos"
```

- [ ] **Step 2: Run test to verify fail**

Run: `python3 -m pytest backend/tests/test_money_format.py -q`
Expected: FAIL module/function missing.

- [ ] **Step 3: Implement money formatting utility**

```py
# backend/utils/money_format.py
def number_to_cop_words(value: int) -> str:
    ...
```

- [ ] **Step 4: Enforce richer draft contract in generator**

```py
# include required sections:
# - Hechos (cronologia amplia)
# - Cuantia por concepto (numero + letras)
# - Fundamentos con extractos relevantes
```

- [ ] **Step 5: Run tests + compile and commit**

Run: `python3 -m pytest backend/tests/test_money_format.py -q && python3 -m py_compile backend/agents/complaint_draft_generator.py backend/utils/money_format.py`
Expected: PASS.

```bash
git add backend/agents/complaint_draft_generator.py backend/utils/money_format.py backend/tests/test_money_format.py
git commit -m "feat: upgrade SIC draft quality with quantified sections and legal excerpts"
```

### Task 8: Article-Level Explainability Contract

**Files:**
- Modify: `backend/agents/legal_classifier.py`
- Create: `backend/tests/test_legal_classifier_schema.py`
- Test: classification schema

- [ ] **Step 1: Write failing schema test for `article_analysis`**

```py
def test_classification_contains_article_analysis_keys():
    sample = parse_or_fallback(...)
    assert isinstance(sample.get("article_analysis", []), list)
```

- [ ] **Step 2: Run to verify fail**

Run: `python3 -m pytest backend/tests/test_legal_classifier_schema.py -q`
Expected: FAIL missing key/shape.

- [ ] **Step 3: Extend system prompt + fallback schema**

```py
"article_analysis": [
  {
    "article_id": "ART_...",
    "confidence_by_article": 0.0,
    "relevant_excerpt": "...",
    "reasoning_summary": "..."
  }
]
```

- [ ] **Step 4: Validate and commit**

Run: `python3 -m pytest backend/tests/test_legal_classifier_schema.py -q`
Expected: PASS.

```bash
git add backend/agents/legal_classifier.py backend/tests/test_legal_classifier_schema.py
git commit -m "feat: add article-level explainability payload to legal classifier"
```

### Task 9: Final PDF Package with Evidence Annexes

**Files:**
- Create: `backend/utils/pdf_package_builder.py`
- Modify: `backend/agents/case_packager.py`
- Modify: `backend/api/pipeline_routes.py`
- Create: `backend/tests/test_pdf_package_builder.py`
- Test: package builder output

- [ ] **Step 1: Write failing package builder test**

```py
def test_package_includes_annex_index_and_files(tmp_path):
    out = build_case_package_pdf(...)
    assert out.exists()
```

- [ ] **Step 2: Run test to verify fail**

Run: `python3 -m pytest backend/tests/test_pdf_package_builder.py -q`
Expected: FAIL function missing.

- [ ] **Step 3: Implement deterministic package builder**

```py
def build_case_package_pdf(case_id: str, formal_draft: str, evidence_files: list[str], output_dir: str) -> str:
    # cover + draft + annex index + each evidence page/merged pdf
    ...
```

- [ ] **Step 4: Persist package path in case payload**

```py
case["final_package_pdf_path"] = package_path
```

- [ ] **Step 5: Run tests and commit**

Run: `python3 -m pytest backend/tests/test_pdf_package_builder.py -q`
Expected: PASS.

```bash
git add backend/utils/pdf_package_builder.py backend/agents/case_packager.py backend/api/pipeline_routes.py backend/tests/test_pdf_package_builder.py
git commit -m "feat: generate final case PDF package with annexed evidence"
```

### Task 10: Decision-Triggered WhatsApp Updates + Data Explorer Backend

**Files:**
- Modify: `backend/api/lawyer_routes.py`
- Modify: `backend/api/notify_routes.py`
- Modify: `backend/api/cases_routes.py`
- Create: `backend/tests/test_lawyer_decision_notifications.py`
- Modify: `frontend/src/admin/DataExplorer.tsx`
- Test: notification and data listing behavior

- [ ] **Step 1: Add failing test for decision event notification gate**

```py
def test_claim_decision_sends_notify_only_when_phone_registered():
    ...
```

- [ ] **Step 2: Run test to verify fail**

Run: `python3 -m pytest backend/tests/test_lawyer_decision_notifications.py -q`
Expected: FAIL behavior missing.

- [ ] **Step 3: Add notification trigger in claim decision endpoints**

```py
# after update_document in lawyer_routes
# call notify sender for events: CLAIM_REACTIVATED / NO_CLAIM_CONFIRMED
# only when whatsapp_number exists
```

- [ ] **Step 4: Add read-only data explorer API endpoint**

```py
@router.get("/cases/documents/index")
async def list_document_index(token: LawyerDep):
    ...
```

- [ ] **Step 5: Implement frontend Data Explorer search table**

```tsx
const [query, setQuery] = useState('')
const [rows, setRows] = useState<DocumentRow[]>([])
```

- [ ] **Step 6: Run tests/build and commit**

Run: `python3 -m pytest backend/tests/test_lawyer_decision_notifications.py -q && cd frontend && npm run build`
Expected: PASS.

```bash
git add backend/api/lawyer_routes.py backend/api/notify_routes.py backend/api/cases_routes.py backend/tests/test_lawyer_decision_notifications.py frontend/src/admin/DataExplorer.tsx
git commit -m "feat: add decision-based WhatsApp updates and admin data explorer backend"
```

### Task 11: Integration Verification and Replit Sync

**Files:**
- Modify: none (verification only)
- Test: end-to-end checks

- [ ] **Step 1: Run backend compile and selected tests**

Run:

```bash
python3 -m py_compile backend/api/*.py backend/agents/*.py backend/utils/*.py
python3 -m pytest backend/tests/test_money_format.py backend/tests/test_legal_classifier_schema.py backend/tests/test_pdf_package_builder.py backend/tests/test_lawyer_decision_notifications.py -q
```

Expected: PASS.

- [ ] **Step 2: Run frontend production build**

Run: `cd frontend && npm run build`
Expected: PASS.

- [ ] **Step 3: Manual admin checks**

Run app and verify:

```txt
1) Queue search filters rows.
2) Sidebar routes navigate correctly.
3) Case detail analysis expands by article and shows confidence.
4) Decision buttons have no emoji.
5) Data Explorer search works.
6) Draft text contains quantia by concept and numbers+words.
```

- [ ] **Step 4: Final commit**

```bash
git add .
git commit -m "feat: complete visual/admin/legal refresh with explainability and packaging"
```

## Spec Coverage Check

1. Visual reference (public/admin/case detail): covered by Tasks 1-5.
2. Queue search + sidebar functionality + third data section: covered by Tasks 3, 4, 10.
3. Draft legal expansion, quantia specifics, legal excerpts: covered by Task 7.
4. Expandable AI article analysis + confidence: covered by Tasks 5 and 8.
5. Final PDF with evidence annexes: covered by Task 9.
6. Emoji removal and lawyer decision WhatsApp updates: covered by Tasks 5 and 10.
7. Observability/logging safe-by-default: covered by Task 6.

No spec requirement is left without a mapped task.

## Placeholder Scan

No TODO/TBD placeholders are left in tasks. All tasks include exact files, concrete code blocks, and explicit commands.

## Type Consistency Check

1. `article_analysis` naming is consistent across backend (`legal_classifier`) and frontend (`CaseDetail`).
2. Notification events are consistently attached to lawyer decision flow.
3. Data Explorer route and component naming are consistent (`/admin/data`, `DataExplorer`).
