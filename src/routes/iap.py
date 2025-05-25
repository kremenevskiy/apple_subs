# app/routes/iap.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.config import get_db
from src.models import models
from src.schemas.iap import IAPValidationRequest, IAPValidationResponse
from src.services import subscription_service, user_service
from src.external import appstore_api

router = APIRouter()

@router.post("/validate", response_model=IAPValidationResponse)
async def validate_purchase(request: IAPValidationRequest, db: AsyncSession = Depends(get_db), user: models.User = Depends(user_service.get_current_user)):
    # Проверяем транзакцию через Apple
    try:
        transaction_data = await appstore_api.get_transaction_info(transaction_id=request.transaction_id, environment="sandbox")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Transaction validation failed: {str(e)}")
    # Находим продукт в нашей базе по productId
    product_id_str = transaction_data.get("productId")
    result = await db.execute(select(models.Product).where(models.Product.product_id == product_id_str))
    product = result.scalars().first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    # Применяем покупку к аккаунту пользователя
    updated_user = await subscription_service.apply_purchase(db, user, product, transaction_data, event_type="PURCHASE")
    # Формируем ответ в зависимости от типа продукта
    response = {"success": True}
    if product.type == "subscription":
        response.update({"subscription_status": updated_user.subscription_status, "subscription_expires_at": updated_user.subscription_expires_at})
    elif product.type == "credits":
        response.update({"credits": updated_user.credits})
    elif product.type == "model":
        response.update({"models": updated_user.models})
    return response
