# app/models/models.py
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=True)
    apple_sub = Column(String, unique=True, index=True)            # Apple уникальный идентификатор пользователя (sub)
    app_account_token = Column(String, unique=True, index=True)    # Токен для связи транзакций App Store с пользователем
    credits = Column(Integer, default=0)
    models = Column(Integer, default=0)
    subscription_status = Column(String, default="inactive")
    subscription_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    transactions = relationship("Transaction", back_populates="user")


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    product_id = Column(String, unique=True, index=True)  # Идентификатор продукта в App Store (например, com.app.product)
    type = Column(String)      # "subscription", "credits", или "model"
    credits_count = Column(Integer, nullable=True)
    models_count = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    transactions = relationship("Transaction", back_populates="product")


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    transaction_id = Column(String, unique=True, index=True)          # Идентификатор транзакции Apple (transactionId)
    original_transaction_id = Column(String, nullable=True)           # Оригинальный идентификатор транзакции Apple для подписок
    type = Column(String)                                             # Например, "PURCHASE", "RENEWAL", "EXPIRED"
    quantity = Column(Integer, default=1)
    purchase_date = Column(DateTime, nullable=True)
    raw_data = Column(Text)                                           # Полные сырые данные (JSON или receipt)

    user = relationship("User", back_populates="transactions")
    product = relationship("Product", back_populates="transactions")
