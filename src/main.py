# app/main.py

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from src.config import settings
from src.routes import apple_webhook, auth, iap

app = FastAPI(
    title="IAP Subscription Service",
    version="1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# — CORS (если фронтенд будет на другом домене/API вызывается из браузера) —
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # или список доверенных фронтенд-доменов
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    body = await request.body()
    logger.info(f"➡️ {request.method} {request.url} Body: {body!r}")
    try:
        response = await call_next(request)
    except Exception:
        # 3) Catch anything unhandled and log its traceback
        logger.exception("💥 Unhandled exception during request")
        # re-raise so FastAPI can return its own 500 or debug page
        raise
    if response.status_code >= 400:
        # read & log the response body as before…
        resp_body = b""
        async for chunk in response.body_iterator:
            resp_body += chunk
        text = resp_body.decode("utf-8", "replace")
        logger.error(f"⬅️ {response.status_code} for {request.url}\n{text}")
        return Response(
            content=resp_body,
            status_code=response.status_code,
            headers=response.headers,
        )
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # попытка считать тело запроса (может быть пустым, если json был битый)
    try:
        body_bytes = await request.body()
        body = body_bytes.decode("utf-8")
    except Exception:
        body = "<cannot decode body>"

    # логируем URL, тело и список ошибок валидации
    logger.error(
        f"🚨 Validation error for {request.method} {request.url}\n"
        f"Body: {body}\nErrors: {exc.errors()}"
    )

    # можно вернуть своё тело ответа, но стандартный JSON с detail тоже норм:
    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.errors(),
            "body": body,
        },
    )


# Регистрируем роутеры
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(iap.router, prefix="/iap", tags=["iap"])
app.include_router(apple_webhook.router, tags=["apple"])


# Простая проверка работоспособности
@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
