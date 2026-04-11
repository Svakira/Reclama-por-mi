# backend/api/auth_routes.py
import hashlib
import os

from fastapi import APIRouter, HTTPException

from backend.auth.jwt_handler import create_token
from backend.models.case_models import LoginRequest, LoginResponse

router = APIRouter()

# Demo credentials — in production, read from Firestore users/ collection
DEMO_LAWYER = {
    "email": os.getenv("LAWYER_EMAIL", "abogado@icesi.edu.co"),
    "password_hash": os.getenv(
        "LAWYER_PASSWORD_HASH",
        hashlib.sha256(b"icesi2026").hexdigest(),
    ),
    "lawyer_id": "lawyer_001",
    "name": "Juan Martínez",
}


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest):
    pw_hash = hashlib.sha256(body.password.encode()).hexdigest()
    if body.email != DEMO_LAWYER["email"] or pw_hash != DEMO_LAWYER["password_hash"]:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    token = create_token(
        lawyer_id=DEMO_LAWYER["lawyer_id"],
        email=DEMO_LAWYER["email"],
    )
    return LoginResponse(
        token=token,
        lawyer_id=DEMO_LAWYER["lawyer_id"],
        name=DEMO_LAWYER["name"],
    )
