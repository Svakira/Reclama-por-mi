# RECLAMA POR MI — Reclamaciones Legales Automaticas

Semillero LegalTech · Universidad ICESI

---

## Resumen

RECLAMA POR MI es una plataforma para ayudar a personas consumidoras a:

1. Contar su caso por chat
2. Subir documentos de soporte
3. Obtener un borrador formal de reclamacion
4. Recibir validacion de abogado
5. Recibir por WhatsApp el PDF final + enlace de recursos SIC

Importante: **no existe envio automatico a la SIC** en la version actual. El producto entrega a Rosa el documento final listo para presentar.

---

## Arquitectura actual (funcional)

La arquitectura en este repositorio es:

- Backend: FastAPI (pipeline + panel abogado)
- LLM/ASR/Vision: Groq
  - chat: modelos Llama via Groq
  - transcripcion: Whisper via Groq
  - vision: modelos vision via Groq
- Knowledge Graph legal: **archivo local JSON** ([backend/kg/legal_graph.json](backend/kg/legal_graph.json))
- Estado/casos: Firestore (o memoria local fallback)
- Frontend: React (vista Rosa + Admin abogado)
- Notificaciones: Twilio WhatsApp (con modo mock cuando no hay credenciales)

No se usa Neo4j/LlamaIndex en runtime de esta version.

---

## Pipeline implementado

Pipeline backend:

1. IntakeInterviewer
2. DocumentParser
3. EvidenceCrossValidator
4. LegalClassifier
5. ComplaintDraftGenerator
6. DraftValidator (deterministico)
7. VerificationGate (faltantes y consistencia)
8. CasePackager
9. LawyerApprovalGate

Referencias principales:

- [backend/api/pipeline_routes.py](backend/api/pipeline_routes.py)
- [backend/agents/intake_interviewer.py](backend/agents/intake_interviewer.py)
- [backend/agents/document_parser.py](backend/agents/document_parser.py)
- [backend/agents/evidence_cross_validator.py](backend/agents/evidence_cross_validator.py)
- [backend/agents/legal_classifier.py](backend/agents/legal_classifier.py)
- [backend/agents/complaint_draft_generator.py](backend/agents/complaint_draft_generator.py)
- [backend/agents/draft_validator.py](backend/agents/draft_validator.py)
- [backend/agents/case_packager.py](backend/agents/case_packager.py)

---

## Hard Gates vigentes

Hard gates operativos en backend:

1. Claim Decision Gate (NO CLAIM)
2. Illegibility Gate (documento ilegible)
3. Lawyer Approval Gate
   - ahora valida antes de aprobar:
   - docs sin revision pendiente
   - claim_valid true
   - draft presente
   - validacion critica aprobada
4. Delivery Gate (opciones de entrega; sin envio automatico a SIC)

Referencias:

- [backend/api/cases_routes.py](backend/api/cases_routes.py)
- [backend/api/lawyer_routes.py](backend/api/lawyer_routes.py)

---

Referencias:

- [backend/api/cases_routes.py](backend/api/cases_routes.py)
- [backend/api/notify_routes.py](backend/api/notify_routes.py)

Variables utiles:

- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_WHATSAPP_FROM`
- `PUBLIC_BASE_URL` (base para generar enlace publico de PDF)
- `SIC_VIDEOS_URL` (enlace de recursos SIC)

---

## Audit Log

El pipeline ahora persiste auditoria tecnica por caso:

- evento, etapa, timestamp, payload resumido
- se guarda en `audit_logs` y tambien dentro del caso (`pipeline_audit`)
- endpoint para abogado: `GET /api/cases/{case_id}/audit`

Referencias:

- [backend/api/pipeline_routes.py](backend/api/pipeline_routes.py)
- [backend/api/cases_routes.py](backend/api/cases_routes.py)
- [backend/db/firestore_client.py](backend/db/firestore_client.py)


---

## Desarrollo local

### Backend

```bash
cd backend
pip install -r requirements.txt
```

Ejecutar tests:

```bash
env PYTHONPATH=/home/runner/workspace pytest backend/tests -q -rA
```

### Frontend

```bash
cd frontend
npm install
npm run build
```

---

## Estructura minima relevante

```text
backend/
  api/
    pipeline_routes.py
    cases_routes.py
    lawyer_routes.py
    notify_routes.py
  agents/
    intake_interviewer.py
    document_parser.py
    evidence_cross_validator.py
    legal_classifier.py
    complaint_draft_generator.py
    draft_validator.py
    case_packager.py
  kg/
    legal_graph.json
  db/
    firestore_client.py
frontend/
  src/app/ChatView.tsx
  src/app/StatusView.tsx
  src/admin/CaseDetail.tsx
```

---

## Nota de alcance

El modulo [backend/external/sic_submitter.py](backend/external/sic_submitter.py) queda como componente exploratorio/no integrado al flujo principal en esta version. La operacion oficial del producto actual es: **abogado valida -> Rosa recibe PDF final + recursos SIC por WhatsApp**.
