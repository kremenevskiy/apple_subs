# app/services/auth_service.py
import jwt
from fastapi import HTTPException
from src import config 
from datetime import datetime, timedelta

def create_access_token(data: dict, expires_sec: int = 24*3600) -> str:
    # Создаем новый JWT с заданными данными и временем жизни
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(seconds=expires_sec)
    payload["iat"] = datetime.utcnow()
    # Подписываем нашим секретом
    token = jwt.encode(payload, config.JWTConfig.secret, algorithm=config.JWTConfig.algorithm)
    return token

def verify_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, config.JWTConfig.secret, algorithms=[config.JWTConfig.algorithm])
        return payload  # если нужен объект пользователя, можно здесь же загрузить из БД
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Token invalid")
