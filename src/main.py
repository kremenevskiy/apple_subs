# main.py
# Точка входа FastAPI приложения. Создает приложение, конфигурирует подключение к БД, включает все маршруты и запускает.
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import iap, apple_webhook, usage
from models import models
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src import config

engine = create_async_engine(config.DatabaseConfig.url, future=True, echo=False)
# Создаем фабрику сессий для Dependency Injection
AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# Dependency для получения сессии
async def get_db_session():
    async with AsyncSessionLocal() as session:
        async with session.begin():
            yield session
            # Коммит/ролбэк произойдет автоматически по выходу

app = FastAPI(title="IAP Subscription & Credits API")

# Разрешим CORS для клиентского приложения (если требуется)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Подключаем роутеры
app.include_router(iap.iap_router)
app.include_router(usage.usage_router)
app.include_router(apple_webhook.apple_router)
