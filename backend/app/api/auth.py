"""Auth endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from app.auth import DEMO_USER, verify_password, create_access_token
from app.schemas import TokenRequest, TokenResponse

router = APIRouter()


@router.post("/token", response_model=TokenResponse)
async def login(body: TokenRequest) -> TokenResponse:
    if body.username != DEMO_USER["username"] or not verify_password(
        body.password, DEMO_USER["password_hash"]
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(body.username)
    return TokenResponse(access_token=token)
