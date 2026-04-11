# JusticIA — B2B Analysis & Business Viability

**Semillero LegalTech — Universidad ICESI**
**Simulacro Hack the Law Cambridge 2026**
*Version: 2026-04-11*

---

## Executive Summary

JusticIA is a B2B SaaS platform that deploys AI-assisted consumer complaint intake to law clinics, legal aid organizations, and public defenders in Colombia. The product does not sell to individual consumers (Rosa never pays). It sells to the institutions whose staff serve those consumers — converting a time-limited professional resource (the lawyer's attention) into a scalable pipeline.

The core value proposition: **one lawyer using JusticIA processes 3–4× more cases per week than one lawyer without it**, with equal or higher complaint quality. This is the economic lever.

---

## 1. The Market

### Demand-Side

| Metric | Source / Basis |
|---|---|
| SIC complaints received per year | ~400,000 (SIC annual reports) |
| % of complainants without legal assistance | ~70% (Access to Justice Index Colombia 2023) |
| % of complaints rejected for procedural errors | Not publicly disaggregated; estimated 20–35% based on SIC admissibility data |
| Law clinics in Colombian universities | ~40–60 (ACOFADE member institutions) |
| Average cases per clinic lawyer per week | ~15–25 (consultorio jurídico typical load) |
| Defensorías del Consumidor (departmental) | 32 (one per department) + municipal offices |

### Supply-Side (Addressable Buyers)

| Buyer type | Count (est.) | Willingness to pay | Decision-maker |
|---|---|---|---|
| University law clinics (consultorios jurídicos) | 40–60 | Low-Medium (budget constrained) | Dean of Law / clinic director |
| Defensorías del Pueblo (consumer rights) | 32 departmental + ~180 municipal | Medium (public budget) | Defensor del Pueblo |
| SIC itself | 1 (national regulator) | High (institutional budget) | SIC Director / MinComercio |
| Consumer NGOs (e.g., Ligas de Consumidores) | ~15–20 active | Low-Medium | Executive Director |
| Ministerio de Justicia / Acceso a la Justicia programs | 1 + regional | Medium-High | Ministry budget |
| Large law firms with pro bono programs | ~10 relevant | Medium | Pro bono partner |

**Total addressable market (TAM):** ~300 potential institutional seats (lawyers using the system).

**Serviceable addressable market (SAM) for Y1:** University law clinics + 3–5 Defensorías = ~80–120 lawyer seats.

---

## 2. Business Model

### Primary: B2B SaaS for Institutional Legal Aid

**Model:** Monthly subscription per active lawyer seat, billed to the institution.

| Tier | Target | Price/seat/month | Included |
|---|---|---|---|
| **Clinic** | University law clinics, ≤5 lawyers | $20 USD | Full pipeline, 200 cases/month, Spanish UI, standard KG |
| **Defensoría** | Public defenders, 5–20 lawyers | $35 USD | Full pipeline, 1,000 cases/month, custom KG updates, priority support |
| **Institutional** | SIC, MinJusticia, large deployments | Custom (≥$50 USD) | White-label, API access, data export, SLA, onboarding |

**Onboarding fee:** $300–800 USD per institution (one-time), covering data migration, staff training, and KG customization for the institution's specific case mix.

### Secondary: Knowledge Graph Licensing

The Neo4j Knowledge Graph encoding Law 1480/2011 + SIC procedures is a standalone asset. It can be licensed separately to:

- Other LegalTech companies building on Colombian consumer law
- Research institutions studying access to justice
- Government agencies updating their own intake systems

**Price:** $500–2,000 USD/year for read API access to the graph.

### Tertiary: Anonymized Data for Research

Aggregated, anonymized case metadata (complaint type, claim amounts, document types, outcomes) is valuable for:

- Academic research on access-to-justice patterns
- Policy advocacy (SIC lobbying for form simplification)
- Legal AI model fine-tuning (Colombian Spanish legal domain)

**Price:** $1,000–5,000 USD/year per research institution, under a data use agreement.

### Out of scope (for now)

- Direct-to-consumer (B2C) model: Rosa never pays. This is a principled choice, not just a business one — charging users who are seeking justice for consumer rights violations undermines the access-to-justice mission and creates perverse incentives.
- Advertising or monetization of individual case data: prohibited by architecture (PII is Firestore-isolated per institution).

---

## 3. Unit Economics

### Cost per Case (Variable Costs)

| Component | Cost basis | Cost per case (est.) |
|---|---|---|
| Groq LLaMA 3.3-70b inference | Free tier (demo/pilot); $0.59/M tokens at scale | $0.02–0.05 |
| Groq Whisper | Free tier; ~$0.0001/min at scale | $0.001–0.003 |
| Firestore reads/writes | ~$0.06/100K ops | $0.001 |
| Google Cloud Run | ~$0.000024/vCPU-second | $0.01–0.03 |
| Twilio WhatsApp | $0.005/message (sandbox free) | $0.005–0.015 |
| Neo4j Aura | Free tier (demo); ~$65/month for 4GB at scale | amortized ~$0.01 |
| **Total variable cost per case** | | **~$0.04–0.10 USD** |

### Revenue per Seat per Month

At the Clinic tier ($20/seat/month), with 200 cases/month per seat:
- Revenue per case: $0.10
- Variable cost per case: ~$0.07 (midpoint)
- **Gross margin per case: ~$0.03 (30%)**

At the Defensoría tier ($35/seat/month), with 400 cases/month per seat:
- Revenue per case: $0.0875
- Variable cost per case: ~$0.07
- **Gross margin per case: ~28%**

These are lean margins at the case level. The model is defensible because:

1. **Fixed costs dominate early-stage:** The KG build, backend, and frontend are built once. Marginal cost of adding a new institution is near zero after infrastructure is in place.
2. **Groq free tier covers the entire hackathon and early pilot:** Real variable costs only materialize at scale (>10K cases/month).
3. **The real value is time, not compute:** A lawyer whose case prep time drops from 40 min to 10 min saves 30 min × 80 cases/month = 40 hours/month. At even $15/hour (Colombian junior lawyer rate), that is $600/month in saved labor — against a $20–35/month subscription. ROI > 20× for the institution.

### Break-Even

Assuming:
- Fixed costs (infra + maintenance): ~$500/month post-hackathon pilot
- Average revenue per seat: $28/month
- Break-even: **~18 active lawyer seats**

At 3 mid-size law clinics (6 lawyers each), break-even is reached. This is achievable in the first 6 months post-hackathon.

---

## 4. Go-to-Market Strategy

### Phase 1 — Hackathon + University Pilot (Months 0–3)
- Present at Simulacro Hack the Law Cambridge 2026.
- Leverage ICESI relationship: propose a 90-day pilot with the ICESI Clínica Jurídica.
- Collect real case data (anonymized), measure time-per-case before/after, document admissibility outcomes.
- Target: 1 institutional pilot, 3–6 active lawyer users, 100–300 real cases.

### Phase 2 — ACOFADE Expansion (Months 3–9)
- ACOFADE (Asociación Colombiana de Facultades de Derecho) has ~50 member institutions.
- Present pilot results at ACOFADE annual meeting.
- Offer 3-month free trial to 5 additional clinics.
- Target: 5–8 institutions, 20–40 lawyer seats.

### Phase 3 — Defensorías + Institutional (Months 9–18)
- Approach Defensoría del Pueblo Nacional for a public-sector pilot.
- Frame as a public-interest technology: the system improves SIC complaint quality, benefiting the regulator.
- Explore MinJusticia "Acceso a la Justicia" program grants.
- Target: 1–2 public-sector contracts, 40–80 additional seats.

---

## 5. Competitive Differentiation

| Dimension | JusticIA | Generic LLM chatbot | Docassemble / form tools | vLex / legal research |
|---|---|---|---|---|
| **Consumer-facing intake** | Voice + text + file, adaptive | Text only, no document handling | Form-based, no AI | Not consumer-facing |
| **Document parsing + cross-validation** | Built-in, deterministic | None | Limited | None |
| **Knowledge Graph grounding** | Law 1480 + KG, no hallucination | Prompt-only, hallucination risk | Static rules | Citation lookup only |
| **Lawyer hard gates** | Enforced (LawyerApprovalGate) | None — AI can act autonomously | None | N/A |
| **Draft generation** | Dual-layer (Rosa + SIC formal) | Single output, no legal structure | Template only | None |
| **Colombian Spanish** | Native (Groq Whisper + LLaMA) | Variable | None | Spanish, not Colombian-specific |
| **Rejection document** | Always generated on NO CLAIM | Never | Never | N/A |
| **Price for clinics** | $20–35/lawyer/month | API costs uncontrolled | Free or $50–200/month | $200–500/month |

**Sustainable differentiation sources:**

1. **The Knowledge Graph:** Building a high-quality, legally accurate KG for Colombian consumer law takes months of expert work. This is the highest barrier to replication.
2. **The hard-gate architecture:** Competitors using generic LLMs cannot credibly claim the same legal safety guarantees. Our architecture is auditable and demonstrable.
3. **Institutional data flywheel:** Each case processed improves the system's calibration. Institutions that adopt early accumulate a competitive advantage in case data.
4. **Domain focus:** We do one thing (SIC consumer complaints) extremely well before expanding. Generalist competitors cannot match this depth.

---

## 6. Risks

| Risk | Severity | Probability | Mitigation |
|---|---|---|---|
| **Groq free tier throttling at scale** | High | Medium | Architecture is model-agnostic. Migrate to paid Groq or alternative (Mistral, Claude) with config change. Budget $50–200/month at 1,000 cases/month. |
| **SIC changes its complaint form or procedures** | High | Low-Medium | KG is modular — new articles are new nodes, not application changes. Designate one lawyer as "KG maintainer." |
| **Colombian regulation of AI in legal services** | High | Low (2–3 year horizon) | Hard gates and lawyer-in-the-loop are already the strongest possible compliance posture. System is explicitly NOT an autonomous legal actor. |
| **OCR quality on Colombian physical documents** | Medium | High | Tesseract + OpenCV handles most cases. Illegibility gate (confidence < 0.70) blocks the pipeline rather than silently failing. Manual verification path already built. |
| **Law clinics lack budget for SaaS** | Medium | Medium | Approach MinJusticia and Colciencias for grant funding. Offer deferred-payment or grant-subsidized pricing for public-interest pilots. |
| **Privacy / data protection (Ley 1581/2012)** | High | Low | Data minimization by design: PII isolated per institution in Firestore, no cross-institutional data sharing, case data never used for model training without explicit consent. |
| **Team dependency (post-hackathon)** | Medium | High | Document everything. The plan (Tasks 1–26) is the handoff artifact. Any developer can continue from the plan. |

---

## 7. Agent's Opinion on Viability

**Short assessment: viable for a sustainable small-scale impact organization. Not a venture-scale unicorn. Both are fine given the mission.**

**Why it works:**

The economics are sound at the institutional level. The ROI for a law clinic is unambiguous — the subscription costs less than one hour of lawyer time per month, and saves 40+ hours. The product solves a real, measurable bottleneck (intake + document handling + draft generation) rather than a vague efficiency aspiration.

The access-to-justice angle is not just mission-washing. It is the go-to-market. Colombia's legal aid ecosystem is specifically resource-constrained, which means a tool that multiplies lawyer capacity without multiplying headcount has a clear institutional buyer. And the institutional buyer (the law clinic director) and the operational user (the clinic lawyer) are perfectly aligned — the director wants more cases handled; the lawyer wants less intake drudgery.

**Where it is weak:**

The margins are thin at the case level. This is not a high-margin SaaS product. It requires institutional sales (slow cycles, committee decisions, public procurement) rather than bottom-up product-led growth. And the Knowledge Graph — which is the real defensible asset — requires ongoing legal expert maintenance, which is a hidden cost not captured in the compute cost model above.

**The honest risk:**

The most likely failure mode is not technical. It is institutional inertia. Colombian law clinics are conservative organizations with limited IT budgets and long procurement cycles. A technically excellent product that cannot get a purchasing decision made in a university committee is a technically excellent product that goes unused.

**Recommendation:**

Lead with the ICESI pilot. Generate concrete before/after data (time per case, admissibility rate, lawyer satisfaction). Use that data to approach ACOFADE. Avoid the temptation to pitch to the SIC or MinJusticia in Year 1 — institutional sales to government take 18–36 months and consume resources that would be better spent on 10 more law clinic pilots.

The B2C upgrade path (offering a lighter version directly to Rosa without a lawyer intermediary) is worth exploring in Year 2, but only after the core institutional model is proven. Removing the lawyer from the loop too early would undermine both the legal safety architecture and the primary market.

**Net verdict: build it, ship the pilot, collect the data, then decide.**

---

*B2B Analysis version: 2026-04-11 | JusticIA — Semillero LegalTech ICESI*
*This analysis represents the agent's assessment based on publicly available market data and the system architecture as specified. It is not a formal business plan or financial projection.*
