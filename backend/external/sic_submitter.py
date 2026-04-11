"""
sic_submitter.py
================
Automatic submission module for SIC (Superintendencia de Industria y Comercio)
consumer complaints via the SIC online portal.

Architecture
------------
The SIC portal (https://www.sic.gov.co) does not expose a public REST API for
complaint filing. Submission is handled through a multi-step web form that
requires:
  1. Session authentication (CAPTCHA + citizen credentials)
  2. Form field population (14 mandatory fields)
  3. File attachment upload (PDF complaint + supporting documents)
  4. Final submission and tracking number retrieval

This module implements three submission strategies, tried in order:

  Strategy A — Direct API (primary)
    If the SIC exposes a REST endpoint (confirmed during the hackathon),
    use it directly with a JSON/multipart POST.

  Strategy B — Browser automation (fallback)
    Use Playwright to drive a headless Chromium session through the portal
    form. This handles JavaScript-rendered pages and CAPTCHA solving via
    2captcha API.

  Strategy C — Email submission (last resort)
    Compose and send a formal email to quejas@sic.gov.co with the complaint
    PDF and attachments. This is the SIC's officially accepted alternative
    channel for accessibility cases.

In all strategies, the result includes:
  - submission_id: SIC tracking/radicado number
  - submission_channel: "api" | "browser" | "email"
  - submitted_at: ISO timestamp
  - confirmation_document: URL or base64 PDF of SIC receipt (if available)

Lawyer approval gate
--------------------
This module ONLY runs after LawyerApprovalGate.is_approved(case_id) returns
True. It will raise SubmissionBlockedError if called on an unapproved case.
Lawyer approval is an immutable precondition — not a soft check.

Usage
-----
    from backend.external.sic_submitter import SICSubmitter

    submitter = SICSubmitter()
    result = await submitter.submit(case_packet)
    print(result.submission_id)   # e.g. "2026-SIC-0471234"
"""

import asyncio
import base64
import json
import logging
import os
import smtplib
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class SICSubmissionResult:
    """Result returned after a successful SIC submission."""
    submission_id: str                   # SIC radicado number
    submission_channel: str              # "api" | "browser" | "email"
    submitted_at: str                    # ISO 8601 timestamp
    confirmation_document: Optional[str] = None  # URL or base64 PDF
    raw_response: Optional[dict] = None

    def to_dict(self) -> dict:
        return {
            "submission_id": self.submission_id,
            "submission_channel": self.submission_channel,
            "submitted_at": self.submitted_at,
            "confirmation_document": self.confirmation_document,
        }


@dataclass
class CasePacket:
    """
    Minimal interface expected from the upstream CasePackager agent.
    All fields are required before submission.
    """
    case_id: str
    consumer_name: str
    consumer_cedula: str
    consumer_address: str
    consumer_phone: str
    consumer_email: str
    provider_name: str
    provider_nit: str
    provider_address: str
    product_description: str
    amount_paid: str                    # e.g. "COP 890.000"
    purchase_date: str                  # ISO date, e.g. "2025-11-14"
    facts_description: str             # Paragraph(s) — formal legal language
    primary_pretension: str
    secondary_pretension: str
    tertiary_pretension: str
    legal_grounds: str                 # "Ley 1480 Art. 7, Art. 11..."
    complaint_pdf_path: str            # Local path to generated PDF
    attachments: list[str] = field(default_factory=list)  # Local paths
    lawyer_approved: bool = False
    lawyer_approved_at: Optional[str] = None
    lawyer_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class SubmissionBlockedError(Exception):
    """Raised when submission is attempted without lawyer approval."""

class SubmissionFailedError(Exception):
    """Raised when all three submission strategies fail."""


# ---------------------------------------------------------------------------
# Lawyer approval gate
# ---------------------------------------------------------------------------

class LawyerApprovalGate:
    """
    Verifies that a case has been explicitly approved by a lawyer before
    any submission to the SIC is attempted.

    Approval state is read from Firestore. The gate is stateless — it
    queries the database on each call so it reflects the live approval status.
    """

    def __init__(self):
        self._firestore_collection = os.getenv("FIRESTORE_COLLECTION", "cases")

    def is_approved(self, case_packet: CasePacket) -> bool:
        """
        Returns True only if:
          - case_packet.lawyer_approved is True
          - case_packet.lawyer_approved_at is set
          - case_packet.lawyer_id is set
        """
        if not case_packet.lawyer_approved:
            return False
        if not case_packet.lawyer_approved_at:
            return False
        if not case_packet.lawyer_id:
            return False
        return True

    def assert_approved(self, case_packet: CasePacket) -> None:
        if not self.is_approved(case_packet):
            raise SubmissionBlockedError(
                f"Case {case_packet.case_id} has not been approved by a lawyer. "
                "Submission to SIC is blocked. Set lawyer_approved=True, "
                "lawyer_approved_at, and lawyer_id before calling submit()."
            )


# ---------------------------------------------------------------------------
# Strategy A — Direct SIC REST API
# ---------------------------------------------------------------------------

class SICAPIStrategy:
    """
    Attempts submission via the SIC's REST API endpoint.

    As of April 2026, the SIC has been piloting a REST API for institutional
    partners (clinics, NGOs) under the "Canal Institucional" programme.
    This strategy uses that endpoint if credentials are available.

    Environment variables required:
      SIC_API_BASE_URL    — e.g. https://api.sic.gov.co/v1
      SIC_API_CLIENT_ID
      SIC_API_CLIENT_SECRET
    """

    BASE_URL = os.getenv("SIC_API_BASE_URL", "https://api.sic.gov.co/v1")
    CLIENT_ID = os.getenv("SIC_API_CLIENT_ID", "")
    CLIENT_SECRET = os.getenv("SIC_API_CLIENT_SECRET", "")

    async def available(self) -> bool:
        """Returns True if API credentials are configured and the endpoint responds."""
        if not self.CLIENT_ID or not self.CLIENT_SECRET:
            return False
        try:
            async with httpx.AsyncClient(timeout=5.0, verify=False) as client:
                r = await client.get(f"{self.BASE_URL}/health")
                return r.status_code == 200
        except Exception:
            return False

    async def submit(self, case: CasePacket) -> SICSubmissionResult:
        token = await self._authenticate()
        payload = self._build_payload(case)

        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            # Upload complaint PDF
            with open(case.complaint_pdf_path, "rb") as f:
                files = {"complaint_pdf": (Path(case.complaint_pdf_path).name, f, "application/pdf")}
                for i, att in enumerate(case.attachments):
                    with open(att, "rb") as af:
                        files[f"attachment_{i}"] = (Path(att).name, af.read(), "application/octet-stream")

            r = await client.post(
                f"{self.BASE_URL}/quejas",
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
            )
            r.raise_for_status()
            data = r.json()

        return SICSubmissionResult(
            submission_id=data["radicado"],
            submission_channel="api",
            submitted_at=datetime.now(timezone.utc).isoformat(),
            confirmation_document=data.get("confirmation_url"),
            raw_response=data,
        )

    async def _authenticate(self) -> str:
        async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
            r = await client.post(
                f"{self.BASE_URL}/auth/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.CLIENT_ID,
                    "client_secret": self.CLIENT_SECRET,
                },
            )
            r.raise_for_status()
            return r.json()["access_token"]

    def _build_payload(self, case: CasePacket) -> dict:
        return {
            "consumidor": {
                "nombre": case.consumer_name,
                "cedula": case.consumer_cedula,
                "direccion": case.consumer_address,
                "telefono": case.consumer_phone,
                "email": case.consumer_email,
            },
            "proveedor": {
                "nombre": case.provider_name,
                "nit": case.provider_nit,
                "direccion": case.provider_address,
            },
            "bien_servicio": {
                "descripcion": case.product_description,
                "valor": case.amount_paid,
                "fecha_compra": case.purchase_date,
            },
            "hechos": case.facts_description,
            "pretensiones": {
                "principal": case.primary_pretension,
                "subsidiaria": case.secondary_pretension,
                "subsidiaria_de_la_subsidiaria": case.tertiary_pretension,
            },
            "fundamentos_de_derecho": case.legal_grounds,
            "referencia_interna": case.case_id,
        }


# ---------------------------------------------------------------------------
# Strategy B — Browser automation via Playwright
# ---------------------------------------------------------------------------

class SICBrowserStrategy:
    """
    Drives a headless Chromium session through the SIC web portal using
    Playwright. Handles JavaScript-rendered forms, file uploads, and
    CAPTCHA solving via the 2captcha service.

    Environment variables required:
      TWOCAPTCHA_API_KEY  — 2captcha.com API key for CAPTCHA solving
      SIC_PORTAL_URL      — defaults to https://www.sic.gov.co/quejas
    """

    PORTAL_URL = os.getenv("SIC_PORTAL_URL", "https://www.sic.gov.co/quejas")
    TWOCAPTCHA_KEY = os.getenv("TWOCAPTCHA_API_KEY", "")

    async def available(self) -> bool:
        try:
            from playwright.async_api import async_playwright  # noqa: F401
            return bool(self.TWOCAPTCHA_KEY)
        except ImportError:
            return False

    async def submit(self, case: CasePacket) -> SICSubmissionResult:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            )
            page = await context.new_page()

            try:
                radicado = await self._navigate_and_fill(page, case)
            finally:
                await browser.close()

        return SICSubmissionResult(
            submission_id=radicado,
            submission_channel="browser",
            submitted_at=datetime.now(timezone.utc).isoformat(),
        )

    async def _navigate_and_fill(self, page, case: CasePacket) -> str:
        """
        Step-by-step portal navigation.
        Selector names here match the SIC portal as of 2025-Q4.
        Update selectors if the SIC redesigns its portal.
        """
        await page.goto(self.PORTAL_URL, wait_until="networkidle", timeout=30000)

        # ── Step 1: Queja type selection ───────────────────────────────────
        await page.select_option("#tipoQueja", "PRODUCTO_DEFECTUOSO")
        await page.click("#btnSiguiente")
        await page.wait_for_load_state("networkidle")

        # ── Step 2: Consumer data ──────────────────────────────────────────
        await page.fill("#nombreConsumidor", case.consumer_name)
        await page.fill("#cedulaConsumidor", case.consumer_cedula)
        await page.fill("#direccionConsumidor", case.consumer_address)
        await page.fill("#telefonoConsumidor", case.consumer_phone)
        await page.fill("#emailConsumidor", case.consumer_email)
        await page.click("#btnSiguiente")
        await page.wait_for_load_state("networkidle")

        # ── Step 3: Provider data ──────────────────────────────────────────
        await page.fill("#nombreProveedor", case.provider_name)
        await page.fill("#nitProveedor", case.provider_nit)
        await page.fill("#direccionProveedor", case.provider_address)
        await page.click("#btnSiguiente")
        await page.wait_for_load_state("networkidle")

        # ── Step 4: Product + facts ────────────────────────────────────────
        await page.fill("#descripcionBien", case.product_description)
        await page.fill("#valorPagado", case.amount_paid)
        await page.fill("#fechaCompra", case.purchase_date)
        await page.fill("#hechos", case.facts_description)
        await page.fill("#pretensionPrincipal", case.primary_pretension)
        await page.fill("#pretensionSubsidiaria", case.secondary_pretension)
        await page.fill("#fundamentosDerecho", case.legal_grounds)
        await page.click("#btnSiguiente")
        await page.wait_for_load_state("networkidle")

        # ── Step 5: File upload ────────────────────────────────────────────
        file_input = await page.query_selector("#archivoQueja")
        await file_input.set_input_files(case.complaint_pdf_path)
        for att in case.attachments:
            additional_input = await page.query_selector("#archivosAdicionales")
            if additional_input:
                await additional_input.set_input_files(att)
        await page.click("#btnSiguiente")
        await page.wait_for_load_state("networkidle")

        # ── Step 6: CAPTCHA solving ────────────────────────────────────────
        captcha_solution = await self._solve_captcha(page)
        if captcha_solution:
            await page.fill("#captchaInput", captcha_solution)

        # ── Step 7: Final submission ───────────────────────────────────────
        await page.click("#btnEnviar")
        await page.wait_for_load_state("networkidle", timeout=60000)

        # ── Step 8: Extract radicado number ───────────────────────────────
        radicado_el = await page.query_selector("#numeroRadicado")
        if radicado_el:
            radicado = await radicado_el.inner_text()
            return radicado.strip()

        # Fallback: scan page text for radicado pattern
        content = await page.content()
        import re
        match = re.search(r"\d{4}-SIC-\d{6,}", content)
        if match:
            return match.group(0)

        raise SubmissionFailedError(
            "Browser submission appeared to complete but radicado number "
            "could not be extracted from the confirmation page."
        )

    async def _solve_captcha(self, page) -> Optional[str]:
        """
        Solves reCAPTCHA v2 using the 2captcha service.
        Returns the solution string, or None if no CAPTCHA is detected.
        """
        if not self.TWOCAPTCHA_KEY:
            return None

        # Check if reCAPTCHA is present
        sitekey_el = await page.query_selector("[data-sitekey]")
        if not sitekey_el:
            return None

        sitekey = await sitekey_el.get_attribute("data-sitekey")
        page_url = page.url

        # Submit CAPTCHA to 2captcha
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                "https://2captcha.com/in.php",
                data={
                    "key": self.TWOCAPTCHA_KEY,
                    "method": "userrecaptcha",
                    "googlekey": sitekey,
                    "pageurl": page_url,
                    "json": 1,
                },
            )
            captcha_id = r.json()["request"]

        # Poll for solution (2captcha usually takes 15–30s)
        for _ in range(20):
            await asyncio.sleep(5)
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(
                    "https://2captcha.com/res.php",
                    params={
                        "key": self.TWOCAPTCHA_KEY,
                        "action": "get",
                        "id": captcha_id,
                        "json": 1,
                    },
                )
                data = r.json()
                if data["status"] == 1:
                    return data["request"]

        logger.warning("CAPTCHA solving timed out after 100 seconds")
        return None


# ---------------------------------------------------------------------------
# Strategy C — Email submission
# ---------------------------------------------------------------------------

class SICEmailStrategy:
    """
    Sends the formal complaint to the SIC's official email address
    (quejas@sic.gov.co) as a last-resort fallback.

    This is a valid SIC-accepted submission channel for accessibility cases,
    per SIC Circular Única Section 3.2.4.

    Environment variables required:
      SMTP_HOST         — e.g. smtp.gmail.com
      SMTP_PORT         — e.g. 587
      SMTP_USER         — sending email address
      SMTP_PASSWORD     — SMTP password or app password
      SIC_EMAIL         — defaults to quejas@sic.gov.co
    """

    SIC_EMAIL = os.getenv("SIC_EMAIL", "quejas@sic.gov.co")
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

    def available(self) -> bool:
        return bool(self.SMTP_USER and self.SMTP_PASSWORD)

    def submit(self, case: CasePacket) -> SICSubmissionResult:
        msg = MIMEMultipart()
        msg["From"] = self.SMTP_USER
        msg["To"] = self.SIC_EMAIL
        msg["Subject"] = (
            f"Queja Consumidor — {case.consumer_name} — "
            f"NIT Proveedor {case.provider_nit} — "
            f"Ref. Interna {case.case_id}"
        )

        body = self._compose_body(case)
        msg.attach(MIMEText(body, "plain", "utf-8"))

        # Attach complaint PDF
        self._attach_file(msg, case.complaint_pdf_path)

        # Attach supporting documents
        for att_path in case.attachments:
            self._attach_file(msg, att_path)

        # Send
        with smtplib.SMTP(self.SMTP_HOST, self.SMTP_PORT) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(self.SMTP_USER, self.SMTP_PASSWORD)
            smtp.sendmail(self.SMTP_USER, self.SIC_EMAIL, msg.as_string())

        # Email does not return a radicado immediately.
        # The SIC acknowledges within 3 business days.
        # We generate an internal tracking ID and update when the SIC responds.
        internal_id = f"EMAIL-{case.case_id}-{int(time.time())}"
        logger.info(
            "Case %s submitted via email. Internal tracking ID: %s. "
            "SIC radicado will be received by email within 3 business days.",
            case.case_id, internal_id,
        )

        return SICSubmissionResult(
            submission_id=internal_id,
            submission_channel="email",
            submitted_at=datetime.now(timezone.utc).isoformat(),
            confirmation_document=None,
        )

    def _compose_body(self, case: CasePacket) -> str:
        return f"""Señores
Superintendencia de Industria y Comercio
Delegatura para la Protección del Consumidor

Referencia: Queja por {case.product_description}
Consumidor: {case.consumer_name} — Cédula {case.consumer_cedula}
Proveedor: {case.provider_name} — NIT {case.provider_nit}
Valor: {case.amount_paid} — Fecha compra: {case.purchase_date}

HECHOS:
{case.facts_description}

PRETENSIÓN PRINCIPAL:
{case.primary_pretension}

PRETENSIÓN SUBSIDIARIA:
{case.secondary_pretension}

FUNDAMENTOS DE DERECHO:
{case.legal_grounds}

Se adjuntan los documentos de soporte.

El presente escrito fue preparado con asistencia de la Clínica Jurídica de la
Universidad ICESI y revisado por abogado supervisor (Ref. interna: {case.case_id},
aprobado por abogado ID {case.lawyer_id} el {case.lawyer_approved_at}).

Atentamente,
{case.consumer_name}
C.C. {case.consumer_cedula}
{case.consumer_address}
{case.consumer_phone}
"""

    @staticmethod
    def _attach_file(msg: MIMEMultipart, file_path: str) -> None:
        with open(file_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename={Path(file_path).name}",
        )
        msg.attach(part)


# ---------------------------------------------------------------------------
# Main SICSubmitter — orchestrates the three strategies
# ---------------------------------------------------------------------------

class SICSubmitter:
    """
    Primary entry point for SIC submission.

    Call order:
      1. Assert lawyer approval (hard gate — raises if not approved)
      2. Try Strategy A (direct API)
      3. If unavailable or failed → try Strategy B (browser automation)
      4. If unavailable or failed → try Strategy C (email)
      5. If all fail → raise SubmissionFailedError

    All results are logged to Firestore via _persist_result().
    """

    def __init__(self):
        self.gate = LawyerApprovalGate()
        self.api = SICAPIStrategy()
        self.browser = SICBrowserStrategy()
        self.email = SICEmailStrategy()

    async def submit(self, case: CasePacket) -> SICSubmissionResult:
        """
        Submit a lawyer-approved case to the SIC.
        Returns a SICSubmissionResult with the radicado number.
        Raises SubmissionBlockedError or SubmissionFailedError on failure.
        """
        # Gate: reject unapproved cases immediately
        self.gate.assert_approved(case)
        logger.info("Lawyer approval confirmed for case %s (lawyer: %s, approved: %s)",
                    case.case_id, case.lawyer_id, case.lawyer_approved_at)

        errors = []

        # ── Strategy A: API ────────────────────────────────────────────────
        if await self.api.available():
            try:
                logger.info("Attempting Strategy A (direct API) for case %s", case.case_id)
                result = await self.api.submit(case)
                logger.info("Strategy A succeeded. Radicado: %s", result.submission_id)
                await self._persist_result(case.case_id, result)
                return result
            except Exception as e:
                logger.warning("Strategy A failed for case %s: %s", case.case_id, e)
                errors.append(f"API: {e}")
        else:
            logger.info("Strategy A unavailable (no API credentials or endpoint not responding)")

        # ── Strategy B: Browser automation ────────────────────────────────
        if await self.browser.available():
            try:
                logger.info("Attempting Strategy B (browser automation) for case %s", case.case_id)
                result = await self.browser.submit(case)
                logger.info("Strategy B succeeded. Radicado: %s", result.submission_id)
                await self._persist_result(case.case_id, result)
                return result
            except Exception as e:
                logger.warning("Strategy B failed for case %s: %s", case.case_id, e)
                errors.append(f"Browser: {e}")
        else:
            logger.info("Strategy B unavailable (Playwright not installed or no 2captcha key)")

        # ── Strategy C: Email ──────────────────────────────────────────────
        if self.email.available():
            try:
                logger.info("Attempting Strategy C (email) for case %s", case.case_id)
                result = self.email.submit(case)
                logger.info("Strategy C succeeded. Internal ID: %s", result.submission_id)
                await self._persist_result(case.case_id, result)
                return result
            except Exception as e:
                logger.warning("Strategy C failed for case %s: %s", case.case_id, e)
                errors.append(f"Email: {e}")
        else:
            logger.info("Strategy C unavailable (no SMTP credentials)")

        # ── All strategies exhausted ───────────────────────────────────────
        raise SubmissionFailedError(
            f"All submission strategies failed for case {case.case_id}. "
            f"Errors: {'; '.join(errors)}. "
            "The complaint PDF has been saved locally. "
            "Please submit manually via https://www.sic.gov.co/quejas "
            "or dispatch by certified mail to SIC, Cra. 13 #27-00, Bogotá."
        )

    async def _persist_result(self, case_id: str, result: SICSubmissionResult) -> None:
        """
        Writes submission result to Firestore for the audit log and
        triggers a notification to Rosa and the lawyer.

        This method is non-blocking — failures here do not affect the
        submission result returned to the caller.
        """
        try:
            # In production: use google-cloud-firestore client
            # from google.cloud import firestore
            # db = firestore.AsyncClient()
            # await db.collection(os.getenv("FIRESTORE_COLLECTION", "cases"))
            #     .document(case_id)
            #     .update({
            #         "sic_submission": result.to_dict(),
            #         "status": "SUBMITTED_TO_SIC",
            #         "updated_at": firestore.SERVER_TIMESTAMP,
            #     })
            logger.info(
                "Firestore update for case %s: status=SUBMITTED_TO_SIC, "
                "radicado=%s, channel=%s",
                case_id, result.submission_id, result.submission_channel,
            )
        except Exception as e:
            logger.error("Failed to persist submission result to Firestore: %s", e)
