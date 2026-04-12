# backend/models/case_models.py
from typing import Any, Optional
from pydantic import BaseModel


class Case(BaseModel):
    case_id: str
    consumer_name: str
    status: str  # PENDING_REVIEW | LAWYER_REVIEWING | APPROVED | DELIVERED_TO_ROSA | CLOSED | PENDING_CLAIM_DECISION
    priority: int
    case_type: str  # A | B | C | UNKNOWN
    created_at: str
    whatsapp_number: Optional[str] = None
    notification_log: list[dict] = []
    lawyer_approved: bool = False
    lawyer_approved_at: Optional[str] = None
    lawyer_id: Optional[str] = None
    ai_summary: Optional[list[str]] = None
    validation_flags: list[dict] = []
    validation_result: Optional[dict] = None
    legal_classification: Optional[dict] = None
    consumer_cedula: Optional[str] = None
    consumer_address: Optional[str] = None
    consumer_phone: Optional[str] = None
    consumer_email: Optional[str] = None
    provider_name: Optional[str] = None
    provider_nit: Optional[str] = None
    provider_address: Optional[str] = None
    product_description: Optional[str] = None
    amount_paid: Optional[str] = None
    purchase_date: Optional[str] = None
    facts_description: Optional[str] = None
    primary_pretension: Optional[str] = None
    secondary_pretension: Optional[str] = None
    tertiary_pretension: Optional[str] = None
    legal_grounds: Optional[str] = None
    complaint_pdf_path: Optional[str] = None
    sic_procedure_guide: Optional[dict] = None
    # Stage 3 gate
    document_illegible: bool = False
    document_confidence: float = 1.0
    # Stage 5b gate
    claim_valid: Optional[bool] = None
    rejection_reason: Optional[str] = None
    # Stage 10 gate
    filing_option_chosen: Optional[int] = None  # 1 | 2 | 3
    rosa_document_consent: bool = False
    delivery_token: Optional[str] = None
    delivered_to_rosa_at: Optional[str] = None


class DraftVersion(BaseModel):
    version_id: str
    case_id: str
    content: str
    saved_at: str
    saved_by_lawyer_id: str
    saved_by_name: str
    is_auto_save: bool
    summary: str = ""


class CurrentDraft(BaseModel):
    content: str
    version_id: str
    last_updated: str


class AuditLog(BaseModel):
    case_id: str
    triggered_by: str
    triggered_at: str
    result: dict[str, Any]
    items: list[dict[str, Any]]
    acknowledged_warnings: list[str] = []


class NotifyRegisterRequest(BaseModel):
    case_id: str
    phone: str  # +573XXXXXXXXX


class NotifySendRequest(BaseModel):
    case_id: str
    event: str  # CASE_CREATED | LAWYER_REVIEWING | DRAFT_APPROVED | CASE_COMPLETED


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    token: str
    lawyer_id: str
    name: str


class IntakeRequest(BaseModel):
    session_id: str
    message: str
    audio_base64: Optional[str] = None  # whisper transcription input


class IntakeResponse(BaseModel):
    session_id: str
    agent_reply: str
    stage: str  # INTAKE | DOCS_NEEDED | PROCESSING | COMPLETE
    case_id: Optional[str] = None
    next_action: Optional[str] = None  # "upload_document" | "confirm" | "wait"


class DocumentUploadResponse(BaseModel):
    session_id: str
    case_id: str
    extraction_summary: dict
    confidence: float
    blocked: bool  # True if confidence < 0.70
    next_action: str


class LawyerClaimDecisionRequest(BaseModel):
    decision: str  # "CONFIRM_NO_CLAIM" | "OVERRIDE_CLAIM_VALID"
    notes: Optional[str] = None


class FilingOptionRequest(BaseModel):
    option: int  # 1 | 2 | 3
    rosa_document_consent: bool = False  # required for option 1
    phone: Optional[str] = None  # for option 1 WhatsApp delivery
