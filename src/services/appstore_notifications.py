# app/services/appstore_notifications.py
from src import external  # внешний модуль или Apple library for verification
from src.models import models
from src.db import db

def decode_notification(signed_payload: str) -> dict:
    """
    Верифицирует JWS и возвращает содержимое уведомления.
    Если верификация не удалась, бросает исключение.
    """
    # Здесь можно использовать либо apple.app_store_server_library, либо вручную:
    decoded = external.apple_verifier.verify_and_decode_notification(signed_payload)
    # `decoded` предположим словарь: {"notificationType": ..., "subtype": ..., "data": {...}}
    return decoded

async def handle_notification(notification: dict):
    notif_type = notification.get("notificationType")
    subtype = notification.get("subtype")
    data = notification.get("data", {})
    # Возможно, извлечём полезные части из data:
    # transactionInfo и renewalInfo, если нужны.
    # В простом случае нам достаточно originalTransactionId и status.
    if notif_type == "INITIAL_BUY":
        # Новая подписка
        await process_initial_buy(data)
    elif notif_type == "DID_RENEW":
        await process_renewal(data)
    elif notif_type == "DID_CHANGE_RENEWAL_STATUS":
        await process_renewal_status_change(data, subtype)
    elif notif_type == "EXPIRED":
        await process_expired(data)
    elif notif_type == "CANCEL":
        await process_cancel(data, subtype)
    elif notif_type == "REFUND":
        await process_refund(data)
    elif notif_type == "CONSUMPTION_REQUEST":  # пример доп. типов
        await process_consumption(data)
    else:
        # Неизвестный или не обрабатываемый тип (например, DID_RECOVER, PRICE_INCREASE_CONSENT etc.)
        print(f"Unhandled notification type: {notif_type}")
    await db.session.commit()
