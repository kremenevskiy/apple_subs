# services/subscription_service.py
# Функции бизнес-логики, связанные с подписками: активация новой подписки, продление, отмена/истечение.
# Этот модуль обеспечивает корректное обновление состояния подписки пользователя и начисление/блокировку кредитов.

from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from models.models import User, Subscription, CreditTransaction

async def activate_subscription(session: AsyncSession, user: User, product_id: str, original_tx_id: str, credits_on_start: int):
    """Активирует новую подписку для пользователя: создает или обновляет запись Subscription, начисляет начальные бонусные кредиты."""
    # Если у пользователя уже есть запись подписки, обновляем ее; иначе создаем новую
    if user.subscription:
        sub = user.subscription
        sub.apple_product_id = product_id
        sub.original_transaction_id = original_tx_id
        sub.is_active = True
        # Новый период подписки начинается сейчас, предположим период = 1 месяц (30 дней) для упрощения
        sub.expiration_date = datetime.utcnow() + timedelta(days=30)
        sub.grace_until = None  # обнуляем grace period, т.к. подписка активна
    else:
        sub = Subscription(
            user_id=user.id,
            apple_product_id=product_id,
            original_transaction_id=original_tx_id,
            is_active=True,
            expiration_date=datetime.utcnow() + timedelta(days=30)
        )
        session.add(sub)
    # Начисляем бонусные кредиты за первую покупку подписки
    user.credit_balance += credits_on_start
    session.add(CreditTransaction(
        user_id=user.id,
        change=credits_on_start,
        reason="subscription_start",
        related_product_id=product_id,
        related_transaction_id=original_tx_id
    ))

async def renew_subscription(session: AsyncSession, sub: Subscription, credits_on_renew: int):
    """Обрабатывает продление подписки: продлевает expiration_date, начисляет очередные кредиты и сохраняет активность."""
    # Продлеваем срок действия подписки (еще на 1 период, например 30 дней)
    sub.expiration_date = datetime.utcnow() + timedelta(days=30)
    sub.is_active = True
    sub.grace_until = None  # пока подписка активна, grace period не актуален
    # Начисляем кредиты за продление
    user = sub.user
    user.credit_balance += credits_on_renew
    session.add(CreditTransaction(
        user_id=user.id,
        change=credits_on_renew,
        reason="subscription_renewal",
        related_product_id=sub.apple_product_id,
        related_transaction_id=sub.original_transaction_id  # связка через original_tx_id (первичная сделка)
    ))

async def cancel_subscription(session: AsyncSession, sub: Subscription, reason: str = "canceled"):
    """Обрабатывает отмену или истечение подписки: помечает подписку неактивной, устанавливает grace period и при необходимости блокирует кредиты."""
    sub.is_active = False
    sub.grace_until = datetime.utcnow() + timedelta(days=30)  # 30-дневный период, в течение которого кредиты показываются, но не используются
    # Примечание: Кредиты, начисленные по подписке, остаются на балансе, но их использование будет ограничено проверкой grace period.
    # Можно добавить запись о событии отмены в историю (для аудита, без изменения баланса)
    session.add(CreditTransaction(
        user_id=sub.user_id,
        change=0,
        reason=f"subscription_{reason}",
        related_product_id=sub.apple_product_id,
        related_transaction_id=sub.original_transaction_id
    ))
