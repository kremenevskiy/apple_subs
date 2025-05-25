# app/external/apple_verifier.py
import jwt
import time
import base64
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, ec, padding

# Проверка Apple Sign In identity token
def verify_apple_identity_token(identity_token: str, client_id: str) -> dict:
    # Получаем публичные ключи Apple (JWKS) и проверяем подпись токена и поля
    jwks_client = jwt.PyJWKClient("https://appleid.apple.com/auth/keys")
    signing_key = jwks_client.get_signing_key_from_jwt(identity_token)
    data = jwt.decode(identity_token, signing_key.key, algorithms=["RS256"], audience=client_id)
    # Дополнительно проверим issuer (издателя)
    if data.get("iss") != "https://appleid.apple.com":
        raise ValueError("Invalid issuer")
    return data

# Проверка уведомления App Store (подписанного payload из вебхука)
def verify_app_store_notification(signed_payload: str, apple_root_cert_path: str) -> dict:
    # Декодируем и проверяем внешний JWT payload (уведомление от App Store)
    outer_payload = _verify_signed_jws(signed_payload, apple_root_cert_path)
    # Если в уведомлении есть вложенные подписанные данные, декодируем их тоже
    data = outer_payload.get("data", {})
    if "signedTransactionInfo" in data:
        data["signedTransactionInfo"] = _verify_signed_jws(data["signedTransactionInfo"], apple_root_cert_path)
    if "signedRenewalInfo" in data:
        data["signedRenewalInfo"] = _verify_signed_jws(data["signedRenewalInfo"], apple_root_cert_path)
    outer_payload["data"] = data
    return outer_payload

# Внутренняя функция для проверки любого Apple-подписанного JWS (используется для транзакций и уведомлений)
def _verify_signed_jws(token: str, apple_root_cert_path: str) -> dict:
    # Извлекаем цепочку сертификатов из header
    header = jwt.get_unverified_header(token)
    x5c_list = header.get("x5c")
    if not x5c_list:
        raise ValueError("No x5c certificate chain in token header")
    # Загружаем корневой сертификат Apple
    with open(apple_root_cert_path, "rb") as f:
        root_cert_data = f.read()
        try:
            root_cert = x509.load_pem_x509_certificate(root_cert_data)
        except Exception:
            root_cert = x509.load_der_x509_certificate(root_cert_data)
    # Парсим сертификаты из x5c (base64 DER -> x509)
    certs = [x509.load_der_x509_certificate(base64.b64decode(cert)) for cert in x5c_list]
    # Проверяем цепочку сертификатов: certs[0] - лист, последний - промежуточный (или root)
    for i in range(len(certs) - 1):
        cert = certs[i]
        issuer_cert = certs[i + 1]
        # Проверяем, что issuer_cert подписал cert
        issuer_public_key = issuer_cert.public_key()
        issuer_public_key.verify(
            cert.signature,
            cert.tbs_certificate_bytes,
            padding.PKCS1v15() if isinstance(issuer_public_key, rsa.RSAPublicKey) else ec.ECDSA(cert.signature_hash_algorithm),
            cert.signature_hash_algorithm,
        )
    # Проверяем, что последний сертификат цепочки подписан корневым Apple
    last_cert = certs[-1]
    root_public_key = root_cert.public_key()
    # Если последний сертификат - не сам корневой, проверим его подпись корневым ключом
    if last_cert.fingerprint(hashes.SHA256()) != root_cert.fingerprint(hashes.SHA256()):
        root_public_key.verify(
            last_cert.signature,
            last_cert.tbs_certificate_bytes,
            padding.PKCS1v15() if isinstance(root_public_key, rsa.RSAPublicKey) else ec.ECDSA(last_cert.signature_hash_algorithm),
            last_cert.signature_hash_algorithm,
        )
    # Теперь проверяем подпись JWS с помощью открытого ключа листового сертификата
    leaf_cert = certs[0]
    public_key = leaf_cert.public_key()
    payload = jwt.decode(token, public_key, algorithms=[header.get("alg")], options={"verify_aud": False})
    return payload
