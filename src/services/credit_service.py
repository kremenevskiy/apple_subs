# services/credit_service.py
# Функции для управления балансом кредитов: покупка пакетов кредитов, расход кредитов на генерацию/модель.
# Здесь используются транзакции и блокировки, чтобы избежать одновременного расходования одних и тех же кредитов конкурентными запросами.

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from models.models import User, CreditTransaction
from datetime import datetime
from services.subscription_service import cancel_subscription

async def add_credits(session: AsyncSession, user: User, amount: int, product_id: str, transaction_id: str):
    """Начисляет пользователю указанное количество кредитов (например, покупка пакета кредитов)."""
    user.credit_balance += amount
    # Записываем транзакцию в историю: покупка пакета (reason = purchase)
    session.add(CreditTransaction(
        user_id=user.id,
        change=amount,
        reason="purchase",
        related_product_id=product_id,
        related_transaction_id=transaction_id
    ))

async def use_credits(session: AsyncSession, user_id: int, cost: int, usage_type: str) -> bool:
    """Пытается списать 'cost' кредитов у пользователя для указанной операции (usage_type). Возвращает True при успехе."""
    # Начинаем транзакцию вручную для корректной блокировки строки пользователя
    # (AsyncSession используется внутри контекста в роутере, здесь предполагается, что session передан уже с begin()).
    result = await session.execute(select(User).where(User.id == user_id).with_for_update())  # блокируем запись пользователя до конца транзакции
    user = result.scalar_one_or_none()
    if user is None:
        return False  # пользователь не найден
    # Проверяем условия использования: активная подписка или grace period
    if user.subscription:
        sub = user.subscription
        if not sub.is_active:
            # Подписка неактивна
            if sub.grace_until and datetime.utcnow() < sub.grace_until:
                # В период grace кредиты не могут быть использованы
                return False
            else:
                # Grace period истек - можно окончательно занулить кредиты (опционально) и отказать
                user.credit_balance = 0
                # Здесь можно удалить или архивировать подписку, если нужно
                await cancel_subscription(session, sub, reason="expired")  # фиксируем финальное завершение подписки
                return False
    # Теперь проверяем достаточно ли кредитов
    if user.credit_balance < cost:
        return False
    # Все проверки пройдены - списываем кредиты
    user.credit_balance -= cost
    session.add(CreditTransaction(
        user_id=user.id,
        change=-cost,
        reason=usage_type,  # например "generation" или "model"
        related_product_id=None,
        related_transaction_id=None
    ))
    return True
