# app/routes/apple_webhook.py
from fastapi import APIRouter, Request
from src.services import appstore_notifications

apple_router = APIRouter()

@apple_router.post("/apple/iap/webhook", status_code=200)
async def apple_notifications_webhook(request: Request):
    """
    Webhook endpoint receiving App Store Server Notifications (V2).
    """
    body = await request.json()
    signed_payload = body.get("signedPayload")
    if not signed_payload:
        # Apple должно всегда присылать signedPayload
        return {"status": "error", "message": "No payload"}, 400
    try:
        # Декодируем и проверяем уведомление
        notification = appstore_notifications.decode_notification(signed_payload)
    except Exception as e:
        # Если подпись не верифицирована или другой сбой - логируем, отвечаем 400 (Apple повторит позже)
        print(f"Notification verify failed: {e}")
        return {"status": "error", "message": "Invalid signature"}, 400
    # Теперь у нас есть notification (объект или dict) с полями типа, сабтипа, данные
    await appstore_notifications.handle_notification(notification)
    # Возвращаем 200 OK чтобы Apple не повторял
    return {"status": "ok"}
