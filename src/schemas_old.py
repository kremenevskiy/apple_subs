from pydantic import BaseModel, Field


class ValidateRequest(BaseModel):
    transactionId: str = Field(..., alias="transactionId")
    signedTransactionInfo: str | None = None
    environment: str = "Sandbox"
    appAccountToken: str
