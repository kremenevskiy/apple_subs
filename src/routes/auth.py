# app/routes/auth.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.config import settings, get_db
from src.schemas.auth import AppleSignInRequest, TokenResponse
from src.external import apple_verifier
from src.services import user_service

router = APIRouter()

@router.post("/apple", response_model=TokenResponse)
async def apple_sign_in(payload: AppleSignInRequest, db: AsyncSession = Depends(get_db)):
    # Проверяем identity token от Apple Sign In
    try:
        claims = apple_verifier.verify_apple_identity_token(payload.identity_token, settings.APPLE_CLIENT_ID)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Apple identity token")
    apple_sub = claims.get("sub")
    email = claims.get("email")
    if not apple_sub:
        raise HTTPException(status_code=400, detail="Apple token missing subject")
    # Ищем или создаем пользователя в базе данных
    user = await user_service.get_or_create_user_by_apple(db, apple_sub, email)
    # Генерируем JWT для клиента
    access_token = user_service.create_access_token(user)
    return {"access_token": access_token, "token_type": "bearer"}
