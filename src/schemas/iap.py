# app/schemas/iap.py
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


class IAPValidationRequest(BaseModel):
    transaction_id: str
    original_transaction_id: Optional[str] = None
    product_id: Optional[str] = None
    purchase_date: datetime
    expiration_date: Optional[datetime] = None
    environment: str
    appAccountToken: str

    @field_validator("transaction_id", mode="before")
    @classmethod
    def coerce_transaction_id_to_str(cls, v):
        if isinstance(v, (int, float, bytes)):
            return str(v)
        return v

    @field_validator("original_transaction_id", mode="before")
    @classmethod
    def coerce_original_transaction_id_to_str(cls, v):
        if isinstance(v, (int, float, bytes)):
            return str(v)
        return v


class IAPValidationResponse(BaseModel):
    success: bool
    credits: Optional[int] = None
    models: Optional[int] = None
    subscription_status: Optional[str] = None
    subscription_expires_at: Optional[datetime] = None
