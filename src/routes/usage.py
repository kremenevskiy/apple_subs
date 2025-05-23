# routes/usage.py
# FastAPI роуты для действий, расходующих кредиты (генерация и создание модели).
# Здесь проверяется право пользователя выполнить действие и списываются кредиты при успехе.

from fastapi import APIRouter, Depends, HTTPException
from src.schemas import schemas
from services.credit_service import use_credits
usage_router = APIRouter(prefix="/action")

@usage_router.post("/use", response_model=schemas.GenerationResponse)
async def use_credit_action(request: schemas.GenerationRequest, session: AsyncSession = Depends(get_db_session)):
    """Выполняет запрос генерации или создания модели, если у пользователя хватает кредитов и действующая подписка."""
    # В реальном приложении user_id берется из токена; здесь он передается явно для простоты
    user_id = request.user_id
    action_type = request.type  # "generation" или "model"
    cost = 1 if action_type == "generation" else 50
    # Начинаем транзакцию вручную для использования кредитов
    async with session.begin():  # откроем транзакцию
        success = await use_credits(session, user_id, cost, usage_type=action_type)
        if not success:
            # Если не удалось (нет подписки/баланса) – откатим транзакцию и вернем ошибку
            await session.rollback()
            raise HTTPException(status_code=400, detail="Not enough credits or subscription inactive")
        # Иначе, транзакция зафиксируется при выходе из блока with
    # Если дошли сюда, списание произошло
    # Можно здесь вызвать фактическое выполнение генерации/создания модели (например, внешнюю функцию), но это вне области данного сервиса.
    remaining = (await session.get(User, user_id)).credit_balance
    return GenerationResponse(success=True, message=f"{action_type.capitalize()} completed", remaining_credits=remaining)
