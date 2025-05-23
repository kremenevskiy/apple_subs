# routes/iap.py
# FastAPI роутер для работы с покупками внутри приложения (IAP):
# - получение списка доступных продуктов (подписки и пакеты кредитов)
# - прием события покупки от клиента и проверка/обработка этой покупки

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.schemas import schemas
from services import subscription_service, credit_service, apple_service

iap_router = APIRouter(prefix="/iap")

# В реальном проекте продукты и их параметры могут храниться в БД или конфиге.
AVAILABLE_PRODUCTS = [
    {"product_id": "com.myapp.subscription.monthly", "product_type": "subscription", "credits": 100, "title": "Monthly Subscription (100 credits/month)"},
    {"product_id": "com.myapp.credits.pack1", "product_type": "consumable", "credits": 50, "title": "Credit Pack (50 credits)"},
    {"product_id": "com.myapp.credits.pack2", "product_type": "consumable", "credits": 120, "title": "Credit Pack (120 credits)"},
]

@iap_router.get("/products", response_model=List[schemas.ProductInfo])
async def list_products():
    """Возвращает список доступных для покупки продуктов (подписки и кредитные пакеты)."""
    return AVAILABLE_PRODUCTS

@iap_router.post("/validate", response_model=schemas.PurchaseValidationResponse)
async def validate_purchase(event: schemas.PurchaseEvent, session: AsyncSession = Depends(get_db_session)):
    """Принимает информацию о покупке от клиента, проверяет ее через Apple и обновляет данные пользователя (подписка/кредиты)."""
    # Найдем пользователя (в реальном приложении идентификатор пользователя определяется по токену авторизации; здесь упрощенно может передаваться в event)
    # Предположим, что PurchaseEvent.product_id достаточно, чтобы определить тип, а user_id определяется из контекста (например, session пользователя).
    user = ...  # получить текущего авторизованного пользователя (опущено, зависит от auth системы)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found or not authorized")
    # Проверка: не обработана ли эта транзакция ранее (по ее уникальному ID)
    existing = await session.execute(select(CreditTransaction).where(CreditTransaction.related_transaction_id == event.transaction_id))
    if existing.scalar_one_or_none():
        # Такая транзакция уже зафиксирована в истории - дублирующая отправка
        return PurchaseValidationResponse(success=True, message="Purchase already processed")
    # Верифицируем покупку через Apple
    valid = await apple_service.verify_purchase_with_apple(event)
    if not valid:
        raise HTTPException(status_code=400, detail="Invalid purchase receipt")
    # Обработка в зависимости от типа продукта
    if event.purchase_type == "subscription":
        # Активируем подписку пользователю
        await subscription_service.activate_subscription(session, user, event.product_id, event.transaction_id, credits_on_start=AVAILABLE_PRODUCTS[0]["credits"])
    elif event.purchase_type == "consumable":
        # Начисляем кредиты пакета
        # Найдем описание продукта по product_id чтобы узнать сколько кредитов добавить
        product_data = next((p for p in AVAILABLE_PRODUCTS if p["product_id"] == event.product_id), None)
        if not product_data:
            raise HTTPException(status_code=400, detail="Unknown product")
        credits_amount = product_data["credits"]
        await credit_service.add_credits(session, user, credits_amount, event.product_id, event.transaction_id)
    else:
        raise HTTPException(status_code=400, detail="Unsupported purchase_type")
    # По завершении асинхронной транзакции (commit) изменения будут зафиксированы
    return PurchaseValidationResponse(success=True, message="Purchase processed successfully")
