# app/routes/iap.py
from fastapi import APIRouter, Depends, HTTPException
from src.services import iap_service
from src.models import models

iap_router = APIRouter()

@iap_router.post("/iap/validate")
async def validate_purchase(data: dict, current_user: models.User = Depends(get_current_user)):
    """
    Принимает информацию о совершённой покупке от клиента и валидирует её через Apple.
    """
    transaction_id = data.get("transaction_id")
    product_id = data.get("product_id")
    if not transaction_id or not product_id:
        raise HTTPException(status_code=400, detail="Missing transaction data")
    # Вызов сервиса для проверки транзакции через App Store API
    try:
        result = await iap_service.verify_and_process_transaction(current_user, transaction_id, product_id)
    except iap_service.InvalidTransaction as e:
        raise HTTPException(status_code=400, detail=str(e))
    except iap_service.TransactionMismatch as e:
        raise HTTPException(status_code=403, detail=str(e))
    # если все ок, сервис возвращает информацию об обновлениях
    return {"status": "success", **result}
