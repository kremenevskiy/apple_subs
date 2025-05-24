# app/routes/auth.py (маршрут для авторизации через Apple)
from fastapi import APIRouter, HTTPException, Depends
from jose import jwk, jwt
from jose.utils import base64url_decode
from src.models import models
from src.schemas import schemas
from fastapi import Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.services import apple_signin, auth_service

auth_router = APIRouter()

@auth_router.post("/auth/apple", response_model=schemas.AuthResponse)
async def apple_login(payload: schemas.AppleSignInPayload):
    """
    Принимает identity token от клиента (после входа через Sign in with Apple),
    проверяет его подпись и данные, затем возвращает наш JWT для доступа.
    """
    token = payload.identity_token
    # Верифицируем токен Apple (подпись и содержание)
    apple_data = await apple_signin.verify_apple_token(token)
    if not apple_data:
        raise HTTPException(status_code=401, detail="Invalid Apple token")
    # apple_data содержит, например, {'sub': '001-...','email': 'user@privaterelay.appleid.com', ...}
    user = await models.User.get_by_apple_sub(apple_data['sub'])
    if not user:
        # Создаём нового пользователя
        user = models.User(
            apple_sub = apple_data['sub'],
            email = apple_data.get('email'),
            app_account_token = apple_signin.generate_app_account_token()
        )
        await user.save()  # (используя async ORM)
    # Генерируем наш JWT на основе идентификатора пользователя
    access_jwt = auth_service.create_access_token({"user_id": user.id})
    return {"access_token": access_jwt, "token_type": "Bearer"}


auth_scheme = HTTPBearer()  # схема Bearer токена

async def get_current_user(auth: HTTPAuthorizationCredentials = Security(auth_scheme)):
    token_str = auth.credentials
    payload = auth_service.verify_access_token(token_str)
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    user = await models.User.get(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# Использование:
@router.get("/protected/resource")
async def use_resource(current_user: models.User = Depends(get_current_user)):
    return {"message": f"Hello, {current_user.email}"}

