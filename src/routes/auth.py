# app/routes/auth.py (маршрут для авторизации через Apple)
from fastapi import APIRouter, HTTPException, Depends


from src.models import models

from src.services import apple_signin, auth_service

auth_router = APIRouter()

@auth_router.post("/auth/apple", response_model=AuthResponse)
async def apple_login(payload: AppleSignInPayload):
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




