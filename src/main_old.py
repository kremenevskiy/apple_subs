import uvicorn
from fastapi import FastAPI

from src.api.routes import router as iap_router
from src.apple.webhook import webhook_router  # separate router for Apple hooks

app = FastAPI()
app.include_router(iap_router, prefix="/api")
app.include_router(webhook_router)  # absolute path already includes /apple

# Run with:  uvicorn src.main:app --host 0.0.0.0 --port 8000


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
