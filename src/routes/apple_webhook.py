# app/routes/apple_webhook.py
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from src.config import settings, get_db
from src.external import apple_verifier
from src.services import subscription_service

router = APIRouter(tags=["apple"])

@router.post("/apple/iap/webhook", status_code=200)
async def apple_iap_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    # Получаем JSON тело от Apple (содержит signedPayload)
    data = await request.json()
    signed_payload = data.get("signedPayload")
    if not signed_payload:
        raise HTTPException(status_code=400, detail="Invalid payload")
    # Проверяем подпись и декодируем уведомление
    try:
        notification = apple_verifier.verify_app_store_notification(signed_payload, settings.APPLE_ROOT_CERT_PATH)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid notification signature")
    # Обрабатываем уведомление: обновляем подписку/покупки пользователя
    await subscription_service.process_app_store_notification(db, notification)
    # Возвращаем 200 OK для подтверждения
    return {"status": "ok"}
