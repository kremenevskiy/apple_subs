import datetime as dt
import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class SubStatus(str, enum.Enum):
    active = "active"
    in_grace = "in_grace"
    expired = "expired"
    refunded = "refunded"


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)  # your auth uid
    created_at = Column(DateTime, default=dt.datetime.utcnow)
    credits = Column(Integer, default=0)
    subs = relationship("Subscription", back_populates="user")


class Subscription(Base):
    __tablename__ = "subscriptions"
    original_txn_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"))
    product_id = Column(String)
    status = Column(Enum(SubStatus))
    expires_at = Column(DateTime)
    last_env = Column(String)
    user = relationship("User", back_populates="subs")


class TxLog(Base):
    __tablename__ = "transaction_log"
    transaction_id = Column(String, primary_key=True)
    received_at = Column(DateTime, default=dt.datetime.utcnow)
    raw = Column(String)
