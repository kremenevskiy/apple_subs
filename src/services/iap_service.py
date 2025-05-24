# app/services/iap_service.py
from src import external# условно модуль для общения с App Store
from src.models import models
from src.db import db

class InvalidTransaction(Exception): pass
class TransactionMismatch(Exception): pass

async def verify_and_process_transaction(user: models.User, transaction_id: str, product_id: str):
    # Получаем данные транзакции от Apple
    data = await external.appstore_api.get_transaction_info(transaction_id)
    if not data:
        raise InvalidTransaction("Transaction not found or invalid")
    # Проверяем соответствие product_id
    if data["productId"] != product_id:
        # Product не совпадает – возможно мошенничество
        raise TransactionMismatch("Product mismatch")
    # Проверяем appAccountToken
    app_account = data.get("appAccountToken")
    if app_account and app_account != user.app_account_token:
        raise TransactionMismatch("User token mismatch")
    # Определяем тип продукта и обрабатываем
    if data["type"] == "Auto-Renewable Subscription":
        await process_subscription_purchase(user, data)
    elif data["type"] == "Consumable":
        await process_consumable_purchase(user, data)
    elif data["type"] == "Non-Consumable":
        await process_nonconsumable_purchase(user, data)
    else:
        # другие типы (например, Non-Renewing Subscription)
        await process_other_purchase(user, data)
    # Здесь process_* функции обновляют БД и возвращают, например, новые значения балансов или статусов.
    await db.session.commit()  # зафиксировать транзакцию БД
    return {"message": "Purchase processed"}
