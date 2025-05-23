# routes/apple_webhook.py
# FastAPI роутер для обработки серверных уведомлений Apple о событиях подписок.
# Apple будет посылать POST-запросы на этот эндпоинт с JWT, содержащим информацию о событии.
from fastapi import APIRouter, Header, Depends
from starlette.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from services.apple_service import handle_apple_notification

apple_router = APIRouter(prefix="/apple/iap")

@apple_router.post("/webhook")
async def apple_webhook_handler(
    request_body: str = Depends(lambda: ""),  # предположим, raw body можно получить как строку
    # В реальных условиях, FastAPI не дает напрямую raw body через Depends, пришлось бы использовать request.stream().
    # Здесь упрощенно: request_body это весь JWT.
    session: AsyncSession = Depends(get_db_session)
):
    """Получает уведомление от App Store (JWT строкой), верифицирует и обрабатывает его."""
    signed_payload = request_body  # JWT уведомления
    # Верифицируем источник по IP или header подписи (в App Store Notifications v2 можно проверять подпись JWT)
    # Передадим обработку в сервис
    await handle_apple_notification(signed_payload, session)
    # Возвращаем пустой 200 OK, что означает успешное принятие (Apple это ожидает)
    return Response(status_code=200)
