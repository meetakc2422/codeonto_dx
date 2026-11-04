"""Encrypt stored third-party tokens. The key lives in .env (GOOGLE_TOKEN_KEY), never in the database."""

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def _fernet() -> Fernet:
    if not settings.GOOGLE_TOKEN_KEY:
        raise ImproperlyConfigured("GOOGLE_TOKEN_KEY is not set in .env")
    return Fernet(settings.GOOGLE_TOKEN_KEY.encode())


def encrypt(plain: str) -> str:
    return _fernet().encrypt(plain.encode()).decode()


def decrypt(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken as e:
        raise ValueError("Stored token cannot be decrypted with the current GOOGLE_TOKEN_KEY") from e
