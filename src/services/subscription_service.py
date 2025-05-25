# app/services/subscription_service.py
import json
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import models

# Применить проверенную покупку к аккаунту пользователя (начисление credits, models или активация подписки)
async def apply_purchase(db: AsyncSession, user: models.User, product: models.Product, transaction_data: dict, event_type: str = "PURCHASE") -> models.User:
    # Обновляем данные пользователя в зависимости от типа продукта
    if product.type == "subscription":
        user.subscription_status = "active"
        expires_ms = transaction_data.get("expiresDate")
        if expires_ms:
            user.subscription_expires_at = datetime.utcfromtimestamp(expires_ms / 1000)
    elif product.type == "credits":
        user.credits += product.credits_count or 0
    elif product.type == "model":
        user.models += product.models_count or 0
    # Создаем запись о транзакции
    tx = models.Transaction(
        user_id=user.id,
        product_id=product.id,
        transaction_id=transaction_data.get("transactionId"),
        original_transaction_id=transaction_data.get("originalTransactionId"),
        type=event_type,
        quantity=transaction_data.get("quantity", 1),
        purchase_date=datetime.utcfromtimestamp(transaction_data.get("purchaseDate", 0) / 1000) if transaction_data.get("purchaseDate") else None,
        raw_data=json.dumps(transaction_data)
    )
    db.add(tx)
    await db.commit()
    # Обновляем объект пользователя и возвращаем его
    await db.refresh(user)
    return user

# Обработка серверного уведомления App Store и обновление статуса подписки пользователя
async def process_app_store_notification(db: AsyncSession, notification: dict):
    data = notification.get("data", {})
    transaction_info = data.get("signedTransactionInfo") or {}
    if not transaction_info:
        return None
    # Определяем, какого пользователя касается уведомление
    user = None
    app_account_token = transaction_info.get("appAccountToken")
    if app_account_token:
        result = await db.execute(select(models.User).where(models.User.app_account_token == app_account_token))
        user = result.scalars().first()
    if not user:
        # Альтернатива: поиск по original_transaction_id (для подписок)
        original_tx = transaction_info.get("originalTransactionId")
        if original_tx:
            result = await db.execute(select(models.Transaction).where(models.Transaction.original_transaction_id == original_tx))
            existing_tx = result.scalars().first()
            if existing_tx:
                user = await db.get(models.User, existing_tx.user_id)
    if not user:
        return None  # Пользователь не найден для этого уведомления
    # Находим продукт, связанный с транзакцией
    product_id_str = transaction_info.get("productId")
    result = await db.execute(select(models.Product).where(models.Product.product_id == product_id_str))
    product = result.scalars().first()
    if not product:
        return None
    # Определяем тип уведомления и обновляем пользователя
    event_type = notification.get("notificationType") or "UNKNOWN"
    if product.type == "subscription":
        if event_type in ["SUBSCRIBED", "RENEWED", "DID_RENEW", "RESUBSCRIBE"]:
            user.subscription_status = "active"
            expires_ms = transaction_info.get("expiresDate")
            if expires_ms:
                user.subscription_expires_at = datetime.utcfromtimestamp(expires_ms / 1000)
        elif event_type in ["EXPIRED", "CANCEL", "DID_FAIL_TO_RENEW"]:
            user.subscription_status = "inactive"
    elif product.type == "credits":
        if event_type == "REFUND":
            quantity = transaction_info.get("quantity", 1)
            refund_amount = (product.credits_count or 0) * quantity
            user.credits = user.credits - refund_amount if user.credits >= refund_amount else 0
    elif product.type == "model":
        if event_type == "REFUND":
            quantity = transaction_info.get("quantity", 1)
            refund_amount = (product.models_count or 0) * quantity
            user.models = user.models - refund_amount if user.models >= refund_amount else 0
    # Логируем это событие в таблицу Transaction, если еще не записано
    tx_id = transaction_info.get("transactionId")
    if tx_id:
        result = await db.execute(select(models.Transaction).where(models.Transaction.transaction_id == tx_id))
        existing = result.scalars().first()
    else:
        existing = None
    if not existing:
        tx = models.Transaction(
            user_id=user.id,
            product_id=product.id,
            transaction_id=tx_id,
            original_transaction_id=transaction_info.get("originalTransactionId"),
            type=event_type,
            quantity=transaction_info.get("quantity", 1),
            purchase_date=datetime.utcfromtimestamp(transaction_info.get("purchaseDate", 0) / 1000) if transaction_info.get("purchaseDate") else None,
            raw_data=json.dumps(notification)
        )
        db.add(tx)
    await db.commit()
    return user
