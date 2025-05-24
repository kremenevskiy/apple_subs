from dataclasses import dataclass
from dotenv import load_dotenv
import os


load_dotenv('.env', override=True)

@dataclass(frozen=True)
class AppleConfig:
    is_sendbox: bool = os.environ["IAP_USE_SANDBOX"] == "1"
    private_key_path = os.environ["APP_PRIVATE_KEY_PATH"]  # путь к .p8 ключу для App Store API
    issuer_id: str = os.environ["APP_ISSUER_ID"]
    key_id: str = os.environ["APP_KEY_ID"]
    bundle_id: str = os.environ["APP_BUNDLE_ID"]
    public_key: str = os.getenv("APP_PUBLIC_KEY")
    apple_certs_dirpath: str = 'root_certs'


@dataclass(frozen=True)
class DatabaseConfig:
    url: str = os.environ["DATABASE_URL"]


@dataclass(frozen=True)
class JWTConfig:
    secret: str = os.environ["JWT_SECRET"]
    algorithm: str = os.environ["JWT_ALGORITHM"]