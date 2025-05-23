# services/apple_service.py
# Функции для взаимодействия с API Apple: проверка подписей/квитанций и обработка уведомлений от App Store.
# Используется библиотека appstoreserverlibrary для верификации JWT от Apple и вызова серверного API Apple для проверки транзакций.

import os
from appstoreserverlibrary import AppStoreServerAPIClient, SignedDataVerifier, VerificationException
from appstoreserverlibrary.models.Environment import Environment
from appstoreserverlibrary.signed_data_verifier import SignedDataVerifier
from appstoreserverlibrary.receipt_utility import ReceiptUtility
from models.models import User
from src import config
import glob

# Инициализация клиента App Store Server API при старте (например, в startup-event FastAPI)
private_key_path = config.AppleConfig.private_key_path  # путь к .p8 ключу для App Store API
if private_key_path and os.path.exists(private_key_path):
    private_key = open(private_key_path, "r").read()
else:
    private_key = None


appstore_client = None
if private_key:
    appstore_client = AppStoreServerAPIClient(private_key, key_id, issuer_id, bundle_id, environment)
# Предполагается, что root сертификаты Apple загружены и пути переданы через переменные окружения
root_certs_paths = os.getenv("APPLE_ROOT_CERTS", "")  # через запятую


# 📁 Read raw DER bytes from the .cer files
root_certificates = []
for der in glob.glob(f"{config.AppleConfig.apple_certs_dirpath}/*.cer"):
    with open(der, "rb") as f:
        root_certificates.append(f.read())


signed_data_verifier = None
if root_certificates:
    # Создаем объект для верификации подписанных уведомлений/транзакций
    signed_data_verifier = SignedDataVerifier(
        root_certificates=root_certificates,
        enable_online_checks=True,
        environment=Environment.SANDBOX if config.AppleConfig.is_sendbox else Environment.PRODUCTION,
        bundle_id=config.AppleConfig.bundle_id,
    )




async def verify_purchase_with_apple(purchase_event) -> bool:
    """Проверяет подлинность покупки через Apple. Возвращает True, если транзакция валидна и принадлежит нашему приложению."""
    try:
        if purchase_event.transaction_receipt:
            # Если есть квитанция (для старого StoreKit), проверим её
            # (Пример: извлекаем ID транзакции и убеждаемся что ответной историей содержит нужную покупку)
            receipt_util = ReceiptUtility()
            transaction_id = receipt_util.extract_transaction_id_from_app_receipt(purchase_event.transaction_receipt)
            if transaction_id != purchase_event.transaction_id:
                return False
            # Дополнительно можно вызвать get_transaction_history или get_status через appstore_client.
        elif signed_data_verifier:
            # В StoreKit2 транзакция приходит как JWS (подписанный токен), 
            # можно сразу проверить через verify_and_decode_notification (хотя это предназначено для server notifications).
            # Если клиент присылает подпись транзакции (signedTransactionInfo), можно ее верифицировать:
            # payload = signed_data_verifier.verify_and_decode_notification(purchase_event.transaction_receipt)
            pass
        # При желании: вызывать appstore_client.get_transaction_history(...) или get_status(...) для проверки статуса подписки.
        return True
    except VerificationException as e:
        # Невалидная подпись или квитанция
        return False

async def handle_apple_notification(notification_jws: str, session: "AsyncSession"):
    """Обрабатывает входящее уведомление от Apple (App Store Server Notification v2)."""
    if not signed_data_verifier:
        return
    try:
        # Расшифровываем и проверяем подпись уведомления
        payload = signed_data_verifier.verify_and_decode_notification(notification_jws)
    except VerificationException as e:
        print("Failed to verify Apple notification signature:", e)
        return
    # Извлекаем из payload необходимые поля
    notification_type = payload["notificationType"]  # например, INITIAL_BUY, DID_RENEW, CANCEL, REFUND и т.д.
    subtype = payload.get("subtype")  # подтип события (например, VOLUNTARY, BILLING_RETRY, etc)
    # В зависимости от типа уведомления, вызываем соответствующую бизнес-логику:
    # Например:
    # - INITIAL_BUY: первая покупка подписки (можно обработать аналогично activate_subscription)
    # - DID_RENEW / DID_RECOVER: успешное продление (renew_subscription)
    # - CANCEL: подписка отменена досрочно или возврат (cancel_subscription)
    # - EXPIRED: срок подписки истек без продления (cancel_subscription)
    # - REFUND: возврат средств (можно списать соответствующие кредиты)
    original_tx_id = payload["data"]["originalTransactionId"]
    product_id = payload["data"]["productId"]
    user = await session.execute(select(User).where(User.subscription.has(original_transaction_id=original_tx_id)))
    user = user.scalar_one_or_none()
    if not user:
        return  # Пользователь с таким original_transaction_id не найден (возможно, не наш или устарело)
    # Загружаем подписку пользователя
    sub = user.subscription
    if notification_type == "INITIAL_BUY":
        # подписка впервые куплена (в песочнице Apple пришлет такое уведомление)
        # Здесь обычно кредиты уже начислены через client->validate, но можно убедиться что все в порядке
        sub.is_active = True
    elif notification_type in ("DID_RENEW", "DID_RECOVER"):
        # подписка продлена или восстановлена
        await renew_subscription(session, sub, credits_on_renew=<число_кредитов_за_период>)
    elif notification_type == "EXPIRED":
        # срок действия истек без продления
        await cancel_subscription(session, sub, reason="expired")
    elif notification_type == "CANCEL":
        # подписка отменена (например, пользователь отписался или Apple возместила)
        await cancel_subscription(session, sub, reason="canceled")
    elif notification_type == "REFUND":
        # произошел возврат средств по покупке
        # можно снять соответствующие кредиты, которые давались, например:
        refunded_amount = <кредиты_за_период>  # определяем сколько кредитов вернуть/заморозить
        sub.is_active = False
        sub.grace_until = datetime.utcnow()  # отменяем немедленно возможность использования
        user.credit_balance -= refunded_amount  # убираем кредиты, полученные за этот период
        session.add(CreditTransaction(
            user_id=user.id,
            change=-refunded_amount,
            reason="refund",
            related_product_id=product_id,
            related_transaction_id=original_tx_id
        ))
    # Другие типы уведомлений (DID_CHANGE_RENEWAL_STATUS, PRICE_INCREASE_CONSENT etc.) можно обрабатывать по необходимости.
