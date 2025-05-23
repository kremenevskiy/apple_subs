# schemas/schemas.py
# В этом файле определены Pydantic-схемы для валидации входящих запросов и формирования ответов.
# Включает схемы для продуктов (подписок и пакетов кредитов), для проверки покупок (валидация IAP),
# а также схемы для действий генерации и создания моделей.

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class ProductInfo(BaseModel):
    """Схема продукта: описание подписки или пакета кредитов, доступного для покупки."""
    product_id: str                       # идентификатор продукта в Apple App Store
    product_type: str                    # тип продукта: 'subscription' или 'consumable'
    credits: int                         # количество кредитов, которое дает покупка (подписка может давать ежемесячно)
    title: str                           # название или описание продукта для отображения

    class Config:
        orm_mode = True

class PurchaseEvent(BaseModel):
    """Входящая схема для события покупки от клиента (валидация IAP)."""
    product_id: str                      # идентификатор продукта, который был приобретен
    transaction_id: str                  # уникальный идентификатор транзакции (от Apple) для предотвращения повторной обработки
    purchase_type: str                   # тип покупки: 'subscription' или 'consumable'
    transaction_receipt: Optional[str] = None  # необязательно: квитанция или JWT, предоставленная клиентом, для проверки

class PurchaseValidationResponse(BaseModel):
    """Ответ сервера на проверку и обработку покупки."""
    success: bool
    message: str

class GenerationRequest(BaseModel):
    """Входящая схема для запроса генерации контента."""
    user_id: int
    type: str = Field(..., regex="^(generation|model)$")  # 'generation' (1 кредит) или 'model' (50 кредитов)

class GenerationResponse(BaseModel):
    """Ответ на запрос генерации/создания модели."""
    success: bool
    message: str
    remaining_credits: Optional[int] = None
