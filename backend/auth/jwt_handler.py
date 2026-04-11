# backend/auth/jwt_handler.py
import os
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

SECRET = os.getenv("JWT_SECRET", "change-me-in-production-justicia-icesi-2026")
ALGORITHM = "HS256"
EXPIRY_HOURS = 8

bearer_scheme = HTTPBearer()


class TokenData(BaseModel):
    lawyer_id: str
    email: str


def create_token(lawyer_id: str, email: str) -> str:
    payload = {
        "lawyer_id": lawyer_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=EXPIRY_HOURS),
    }
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)


def decode_token(token: str) -> TokenData:
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
        return TokenData(lawyer_id=payload["lawyer_id"], email=payload["email"])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def require_lawyer_token(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> TokenData:
    return decode_token(credentials.credentials)
