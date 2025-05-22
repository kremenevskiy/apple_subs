import glob
import json
import os

from appstoreserverlibrary.models import Environment
from appstoreserverlibrary.signed_data_verifier import SignedDataVerifier
from fastapi import APIRouter, Depends, Request

from db.session import get_session
from service.entitlements import grant_entitlements, revoke_subscription

BUNDLE_ID = os.getenv("APP_BUNDLE_ID")

# 📁 Read raw DER bytes from the .cer files
root_certs = []
for der in glob.glob("src/root_certs/*.cer"):
    with open(der, "rb") as f:
        root_certs.append(f.read())

verifier = SignedDataVerifier(
    root_certificates=root_certs,
    enable_online_checks=True,
    environment=Environment.Environment.SANDBOX,
    bundle_id=BUNDLE_ID,
)

webhook_router = APIRouter()


@webhook_router.post("/apple/iap/webhook")
async def iap_webhook(request: Request, db=Depends(get_session)):
    raw = await request.body()
    envelope = json.loads(raw)
    jws = envelope["signedPayload"]

    note = verifier.verify_and_decode_notification(jws)
    print("🔍 Note:")
    print(note)

    ntype = note.notificationType
    data = note.data or {}
    env = data.environment

    if signed := data.signedTransactionInfo:
        tx = verifier.verify_and_decode_signed_transaction(signed)
        tx["environment"] = env
        if ntype in ("INITIAL_BUY", "DID_RENEW"):
            await grant_entitlements(tx, db)
        else:
            await revoke_subscription(tx, db)

    return {"status": "ok"}
