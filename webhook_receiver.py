from fastapi import FastAPI, Request
import uvicorn
import json

app = FastAPI()

@app.post("/apple/iap/webhook")
async def apple_iap_webhook(request: Request):
    jws_raw = await request.body()   # Apple sends signed JWS in raw body

    print("\n📦 Raw Apple JWS received:")
    print(jws_raw.decode())

    # Optional: decode and verify signature with Apple's SDK (see below)
    return {"status": "ok"}   # Apple expects 2xx response

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)