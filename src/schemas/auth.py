# app/schemas/auth.py
from pydantic import BaseModel

class AppleSignInRequest(BaseModel):
    identity_token: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
