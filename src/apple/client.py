import os
import pathlib
import time

import httpx
import jwt
from dotenv import load_dotenv

load_dotenv(".env", override=True)

ISSUER_ID = os.environ["APPLE_ISSUER_ID"]
KEY_ID = os.environ["APPLE_KEY_ID"]
BUNDLE_ID = os.environ["APP_BUNDLE_ID"]
PRIVATE_KEY = pathlib.Path(os.environ["PRIVATE_KEY_PATH"]).read_text()


def _jwt() -> str:
    now = int(time.time())
    return jwt.encode(
        {
            "iss": ISSUER_ID,
            "iat": now,
            "exp": now + 1200,
            "aud": "appstoreconnect-v1",
            "bid": BUNDLE_ID,
        },
        PRIVATE_KEY,
        algorithm="ES256",
        headers={"kid": KEY_ID},
    )


async def verify_transaction(txn_id: str, env: str = "Sandbox") -> dict:
    base = (
        "https://api.storekit-sandbox.itunes.apple.com"
        if env == "Sandbox"
        else "https://api.storekit.itunes.apple.com"
    )
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(
            f"{base}/inApps/v1/verifyTransaction",
            headers={"Authorization": f"Bearer {_jwt()}"},
            json={"transactionId": txn_id},
        )
        r.raise_for_status()
        return r.json()
