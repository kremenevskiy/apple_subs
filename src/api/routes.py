import httpx
from fastapi import APIRouter, Depends, HTTPException

from apple.client import verify_transaction
from src.db.session import get_session
from schemas_old import ValidateRequest
from src.service.entitlements import grant_entitlements

router = APIRouter()


@router.post("/iap/validate")
async def validate(body: ValidateRequest, db=Depends(get_session)):
    try:
        tx = await verify_transaction(body.transactionId, body.environment)
    except httpx.HTTPStatusError as e:
        raise HTTPException(400, f"Apple verification failed: {e.response.text}")

    # patch in appAccountToken (Apple omits it in verifyTransaction response)
    tx["appAccountToken"] = body.appAccountToken
    await grant_entitlements(tx, db)
    return {"status": "ok"}
