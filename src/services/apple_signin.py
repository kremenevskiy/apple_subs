# app/services/apple_signin.py
import httpx, jwt
from jwt import PyJWKClient


APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"
APPLE_AUDIENCE = "com.myapp.ios"  # Bundle ID приложения (или Service ID для веб-приложения)
APPLE_ISS = "https://appleid.apple.com"

# Можно использовать PyJWT с PyJWKClient для удобства
jwks_client = PyJWKClient(APPLE_JWKS_URL)

async def verify_apple_token(identity_token: str) -> dict:
    """
    Проверяет подпись и валидность identity token от Apple.
    Возвращает payload токена (dict) при успехе или None при ошибке.
    """
    try:
        # Извлекаем открытый ключ по kid из токена
        signing_key = jwks_client.get_signing_key_from_jwt(identity_token)
        # Декодируем и проверяем токен (библиотека сама проверит подпись с полученным ключом)
        payload = jwt.decode(identity_token, signing_key.key, algorithms=["RS256"], 
                              audience=APPLE_AUDIENCE, issuer=APPLE_ISS)
        return payload
    except Exception as e:
        # Логируем ошибку для отладки
        print(f"Apple token verification failed: {e}")
        return None

import uuid
def generate_app_account_token() -> str:
    # Генерируем новый UUID для связывания транзакций Apple с этим пользователем
    return str(uuid.uuid4())
