# app/config.py
from pydantic_settings import BaseSettings
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    APPLE_BUNDLE_ID: str  # Bundle ID или Service ID для Apple Sign In
    APPLE_API_KEY_ID: str  # Key ID для App Store Connect API
    APPLE_API_ISSUER_ID: str  # Issuer ID (GUID) для App Store Connect API
    APPLE_PRIVATE_KEY_PATH: str
    APPLE_ROOT_CERT_PATH: str  # Путь к Apple Root CA сертификату для проверки вебхуков

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# Создаем движок БД и фабрику сессий (асинхронных)
engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# Зависимость для получения сессии БД
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
