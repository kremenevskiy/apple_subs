# app/services/user_service.py
import uuid
import jwt
import datetime
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.models import models
from src.config import settings, get_db
from fastapi import Header, HTTPException, Depends


# OAuth2 схема для извлечения JWT из заголовка Authorization
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/apple")

# Создание или получение пользователя по данным Apple (Apple Sign-In)
async def get_or_create_user_by_apple(db: AsyncSession, apple_sub: str, email: str = None) -> models.User:
    result = await db.execute(select(models.User).where(models.User.apple_sub == apple_sub))
    user = result.scalars().first()
    if user:
        # Обновляем email, если получен и ранее не сохранен
        if email and not user.email:
            user.email = email
        # Генерируем app_account_token, если отсутствует
        if not user.app_account_token:
            user.app_account_token = str(uuid.uuid4())
    else:
        user = models.User(
            apple_sub=apple_sub,
            email=email,
            app_account_token=str(uuid.uuid4()),
            credits=0,
            models=0,
            subscription_status="inactive",
            subscription_expires_at=None
        )
        db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

# Генерация JWT токена для пользователя
def create_access_token(user: models.User) -> str:
    payload = {
        "user_id": user.id,
        "email": user.email,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7)
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token


async def get_current_user(
    x_app_account_token: str = Header(..., alias="X-App-Account-Token"),
    db: AsyncSession = Depends(get_db),
) -> models.User:
    user = await db.scalar(
        select(models.User).where(models.User.app_account_token == x_app_account_token)
    )

    if not user:
        # если впервые — создаём
        user = models.User(app_account_token=x_app_account_token, credits=0, models=0, subscription_status="inactive", subscription_expires_at=None)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user
