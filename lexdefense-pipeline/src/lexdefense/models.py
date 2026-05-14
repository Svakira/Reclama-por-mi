from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class Party(BaseModel):
    name: str
    role: str
    id_number: Optional[str] = None
    email: Optional[str] = None


class Counsel(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None


class DocumentSource(BaseModel):
    document_name: str
    page: Optional[int] = None
    snippet: Optional[str] = None
    document_type: Optional[str] = None


class PageText(BaseModel):
    page_id: str
    document_name: str
    page_number: int
    text: str
    document_type: str = "otro"


class AtomicClaim(BaseModel):
    claim_id: str
    text: str
    classification: Optional[
        Literal[
            "cierto",
            "no_cierto",
            "no_me_consta",
            "parcialmente_cierto",
            "no_es_hecho",
            "requiere_revision_humana",
        ]
    ] = None
    reason: Optional[str] = None
    evidence_for: List[str] = Field(default_factory=list)
    evidence_against: List[str] = Field(default_factory=list)
    missing_evidence: List[str] = Field(default_factory=list)
    proposed_response: Optional[str] = None
    risk_level: Optional[Literal["bajo", "medio", "alto"]] = None
    human_question: Optional[str] = None


class FactItem(BaseModel):
    fact_id: str
    original_number: str
    original_text: str
    atomic_claims: List[AtomicClaim] = Field(default_factory=list)
    overall_classification: Optional[str] = None
    proposed_response: Optional[str] = None
    sources: List[DocumentSource] = Field(default_factory=list)
    human_review_required: bool = True


class EvidenceItem(BaseModel):
    evidence_id: str
    fact_id: str
    claim_id: Optional[str] = None
    classification: str
    evidence_for: List[str] = Field(default_factory=list)
    evidence_against: List[str] = Field(default_factory=list)
    missing_evidence: List[str] = Field(default_factory=list)
    proposed_response: Optional[str] = None
    risk_level: Literal["bajo", "medio", "alto"] = "medio"
    human_question: Optional[str] = None


class DefenseTheory(BaseModel):
    title: str
    summary: str
    supported_fact_ids: List[str] = Field(default_factory=list)


class InsuranceProfile(BaseModel):
    policy_number: Optional[str] = None
    insurer: Optional[str] = None
    coinsurers: List[str] = Field(default_factory=list)
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None
    event_date: Optional[str] = None
    coverage_admitted: bool = False
    liability_admitted: bool = False
    requires_insured_liability: bool = True
    subject_to_terms_conditions: bool = True
    deductible: Optional[str] = None
    coverage_limit: Optional[str] = None
    exclusions: List[str] = Field(default_factory=list)
    pending_human_review: bool = True


class LegalCitation(BaseModel):
    citation_id: str
    citation_text: str
    status: Literal["UNVERIFIED", "VERIFIED"] = "UNVERIFIED"
    source: Optional[str] = None
    verified_by: Optional[str] = None
    verified_at: Optional[str] = None


class DraftParagraph(BaseModel):
    paragraph_id: str
    section: str
    text: str
    function: str
    related_fact_ids: List[str] = Field(default_factory=list)
    related_evidence_ids: List[str] = Field(default_factory=list)
    legal_citation_ids: List[str] = Field(default_factory=list)
    source_status: Literal[
        "sourced",
        "missing_source",
        "human_instruction",
        "procedural_formula",
    ]
    human_review_required: bool = True


class DraftDocument(BaseModel):
    title: str
    paragraphs: List[DraftParagraph] = Field(default_factory=list)


class ValidationIssue(BaseModel):
    issue_id: str
    severity: Literal["critical", "high", "medium", "low"]
    category: Literal[
        "citation",
        "evidence",
        "contradiction",
        "role",
        "deadline",
        "template_residue",
        "style",
        "insurance",
        "traceability",
        "privacy",
    ]
    location: str
    description: str
    suggested_fix: str
    requires_human: bool = True


class HumanApprovalState(BaseModel):
    facts_review_pending: bool = True
    facts_approved: bool = False
    defense_strategy_pending: bool = True
    defense_strategy_approved: bool = False
    legal_citations_pending: bool = True
    legal_citations_verified: bool = False
    final_review_pending: bool = True
    approved_for_export: bool = False


class PipelineRun(BaseModel):
    run_id: str
    input_dir: str
    output_dir: str
    client_role: Optional[str] = None
    approval_status: HumanApprovalState = Field(default_factory=HumanApprovalState)


class CaseSchema(BaseModel):
    case_id: str
    radicado: Optional[str] = None
    juzgado: Optional[str] = None
    medio_control: Optional[str] = None
    jurisdiccion: str = "Colombia"
    demandantes: List[Party] = Field(default_factory=list)
    demandados: List[Party] = Field(default_factory=list)
    llamados_en_garantia: List[Party] = Field(default_factory=list)
    cliente_representado: Optional[Party] = None
    client_role: Optional[str] = None
    fecha_notificacion: Optional[str] = None
    fecha_vencimiento_estimada: Optional[str] = None
    facts: List[FactItem] = Field(default_factory=list)
    pretensiones: List[Dict] = Field(default_factory=list)
    pruebas: List[Dict] = Field(default_factory=list)
    polizas: List[Dict] = Field(default_factory=list)
    flags: List[str] = Field(default_factory=list)
