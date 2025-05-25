# app/external/appstore_api.py
import time

import httpx
import jwt

from src.config import settings
from src.external import apple_verifier

PRODUCTION_BASE = "https://api.storekit.itunes.apple.com"
SANDBOX_BASE = "https://api.storekit-sandbox.itunes.apple.com"


# Генерация JWT для обращения к App Store Server API
def generate_appstore_jwt() -> str:
    now = int(time.time())
    payload = {
        "iss": settings.APPLE_API_ISSUER_ID,
        "iat": now,
        "exp": now + 3600,
        "aud": "appstoreconnect-v1",
        "bid": settings.APPLE_BUNDLE_ID,
    }
    # Подписываем токен приватным ключом (.p8 файл)
    with open(settings.APPLE_PRIVATE_KEY_PATH, "r") as f:
        private_key = f.read()
    token = jwt.encode(
        payload,
        private_key,
        algorithm="ES256",
        headers={"kid": settings.APPLE_API_KEY_ID},
    )
    return token


# Проверка транзакции через App Store API (получение и валидация данных транзакции)
async def get_transaction_info(
    transaction_id: str, environment: str = "production"
) -> dict:
    base = SANDBOX_BASE if environment.lower() == "sandbox" else PRODUCTION_BASE
    print(f"get transaction info: {transaction_id}")

    jwt_token = generate_appstore_jwt()
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json",
    }
    print(f"jwt_token: {jwt_token}")
    async with httpx.AsyncClient() as client:
        # url = f"{base}/inApps/v1/verifyTransaction"
        url = f"{base}/inApps/v1/transactions/{transaction_id}"
        print(f"sending request to url {url}")
        print("before request")
        response = await client.get(url, headers=headers)
        print(f"status code: {response.status_code}")

        if response.status_code != 200:
            try:
                error_data = response.json()
                raise Exception(f"App Store API error: {error_data}")
            except:
                raise Exception(f"App Store API error: {response.status_code}")

        payload = response.json()
        print(f"success: {payload}")
        # Ответ содержит подписанную информацию о транзакции (JWS)
        transaction_jws = payload.get("signedTransactionInfo") or (
            payload if isinstance(payload, str) else None
        )
        if not transaction_jws:
            raise Exception("Invalid transaction data")
        # Проверяем и декодируем подписанную транзакцию
        transaction_data = apple_verifier._verify_signed_jws(
            transaction_jws, settings.APPLE_ROOT_CERT_PATH
        )
        return transaction_data
