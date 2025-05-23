# models/models.py
# Этот файл содержит определения ORM-моделей (таблиц) для пользователей, подписок, кредитов и транзакций.
# Используется SQLAlchemy (AsyncIO) для определения схемы базы данных PostgreSQL.
# Каждая модель отражает соответствующую таблицу в БД, с отношениями между пользователем, подпиской и кредитами.

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, BigInteger
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    """Модель пользователя: хранит информацию о пользователе и текущем балансе кредитов."""
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    # В реальном приложении можно добавить поля email, etc.
    credit_balance = Column(Integer, default=0)  # текущий баланс кредитов пользователя
    # Отношения: один пользователь имеет одну активную (или последнюю) подписку
    subscription = relationship("Subscription", back_populates="user", uselist=False)
    credit_transactions = relationship("CreditTransaction", back_populates="user")

class Subscription(Base):
    """Модель подписки: хранит текущее состояние подписки пользователя."""
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    apple_product_id = Column(String, nullable=False)        # идентификатор продукта подписки (из App Store)
    original_transaction_id = Column(String, unique=True)    # оригинальный ID транзакции подписки (для связки с Apple)
    is_active = Column(Boolean, default=True)                # флаг активной подписки
    expiration_date = Column(DateTime, nullable=True)        # дата окончания текущего оплаченного периода
    grace_until = Column(DateTime, nullable=True)            # дата окончания периода grace (30 дней после отмены)
    user = relationship("User", back_populates="subscription")

class CreditTransaction(Base):
    """Модель транзакции кредитов: история начислений и списаний кредитов пользователя."""
    __tablename__ = "credit_transactions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    change = Column(Integer, nullable=False)      # изменение баланса: положительное (начисление) или отрицательное (списание)
    reason = Column(String, nullable=False)       # причина изменения (например, 'purchase', 'renewal', 'generation', 'model_creation', 'refund')
    related_product_id = Column(String, nullable=True)  # ID продукта (подписки или пакета), если применимо
    related_transaction_id = Column(String, nullable=True)  # ID транзакции Apple, если применимо
    timestamp = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="credit_transactions")
